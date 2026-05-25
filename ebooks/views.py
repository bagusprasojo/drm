from pathlib import Path
import io
import json
import zipfile

from django.conf import settings
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from devices.models import Device
from downloads.models import DownloadLog
from licenses.models import EbookLicense
from drm.crypto_utils import (
    decrypt_key_from_storage,
    load_master_key_from_env,
    rsa_sign,
    wrap_content_key_for_device,
    wrap_content_key_for_public_key,
)
from .models import Ebook
from .serializers import DownloadRequestSerializer, EbookSerializer, EbookUploadSerializer
from .tasks import process_ebook_task


def _http_range_response(request, file_path: Path):
    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range")
    if not range_header:
        response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=file_path.name)
        response["Accept-Ranges"] = "bytes"
        return response

    unit, _, range_spec = range_header.partition("=")
    if unit != "bytes" or "-" not in range_spec:
        return HttpResponse(status=416)

    start_s, end_s = range_spec.split("-", 1)
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else file_size - 1
    end = min(end, file_size - 1)
    if start > end:
        return HttpResponse(status=416)

    chunk_size = end - start + 1

    def stream_file():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                data = f.read(min(65536, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = StreamingHttpResponse(stream_file(), status=206, content_type="application/octet-stream")
    response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    response["Accept-Ranges"] = "bytes"
    response["Content-Length"] = str(chunk_size)
    response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
    return response


def _licensed_package_response(ebook: Ebook, license_obj: EbookLicense, device: Device) -> HttpResponse:
    master_key = load_master_key_from_env(settings.DRM_MASTER_KEY_B64)
    content_key = decrypt_key_from_storage(master_key, ebook.encrypted_content_key_b64)
    if device.public_key_pem:
        key_wrap_alg = "RSA-OAEP-SHA256-device-public-key"
        wrapped_content_key = wrap_content_key_for_public_key(content_key, device.public_key_pem)
    else:
        key_wrap_alg = "AES-256-GCM-SHA256(device_hash)"
        wrapped_content_key = wrap_content_key_for_device(content_key, device.device_hash)

    license_payload = {
        "version": 1,
        "ebook_id": ebook.id,
        "user_id": license_obj.user_id,
        "device_id": device.id,
        "device_hash": device.device_hash,
        "issued_at": license_obj.issued_at.isoformat(),
        "generated_at": timezone.now().isoformat(),
        "key_wrap_alg": key_wrap_alg,
        "wrapped_content_key": wrapped_content_key,
    }
    license_bin = json.dumps(license_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    license_sig = rsa_sign(settings.DRM_RSA_PRIVATE_KEY_PEM, license_bin)

    package_file = Path(ebook.package_path)
    out = io.BytesIO()
    with zipfile.ZipFile(package_file, "r") as src, zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for entry in src.infolist():
            if entry.filename in {"license.json", "license.sig"}:
                continue
            dst.writestr(entry, src.read(entry.filename))
        dst.writestr("license.json", license_bin)
        dst.writestr("license.sig", license_sig)

    response = HttpResponse(out.getvalue(), content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{package_file.name}"'
    response["Cache-Control"] = "no-store"
    return response


class EbookViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = EbookSerializer

    def get_queryset(self):
        if self.action in {"upload"}:
            return Ebook.objects.all().order_by("-created_at")
        return (
            Ebook.objects.filter(
                licenses__user=self.request.user,
                licenses__revoked=False,
                status=Ebook.ProcessingStatus.READY,
            )
            .distinct()
            .order_by("-created_at")
        )

    @action(detail=False, methods=["post"], url_path="upload", parser_classes=[MultiPartParser])
    def upload(self, request):
        serializer = EbookUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded = serializer.validated_data["file"]
        suffix = Path(uploaded.name).suffix.lower()
        if suffix != ".pdf":
            return Response({"detail": "Only .pdf is supported"}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            return Response({"detail": "File too large"}, status=status.HTTP_400_BAD_REQUEST)

        settings.SOURCE_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        source_path = settings.SOURCE_STORAGE_ROOT / uploaded.name
        with source_path.open("wb") as dest:
            for chunk in uploaded.chunks():
                dest.write(chunk)

        ebook = Ebook.objects.create(
            title=serializer.validated_data["title"],
            author=serializer.validated_data.get("author", ""),
            source_path=str(source_path),
            uploaded_by=request.user,
        )
        process_ebook_task.delay(ebook.id)
        return Response(EbookSerializer(ebook).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="download")
    def download(self, request):
        serializer = DownloadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ebook = Ebook.objects.filter(id=serializer.validated_data["ebook_id"], status=Ebook.ProcessingStatus.READY).first()
        if not ebook:
            return Response({"detail": "Ebook not available"}, status=status.HTTP_404_NOT_FOUND)

        device = Device.objects.filter(
            id=serializer.validated_data["device_id"], user=request.user, revoked=False
        ).first()
        if not device:
            return Response({"detail": "Invalid device"}, status=status.HTTP_400_BAD_REQUEST)

        license_obj = EbookLicense.objects.filter(
            user=request.user, ebook=ebook, device=device, revoked=False
        ).first()
        if not license_obj:
            return Response({"detail": "License invalid or device mismatch"}, status=status.HTTP_403_FORBIDDEN)

        DownloadLog.objects.create(
            user=request.user,
            ebook=ebook,
            device=device,
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )

        package_file = Path(ebook.package_path)
        if not package_file.exists():
            return Response({"detail": "Package missing"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if ebook.package_format_version >= 2:
            return _licensed_package_response(ebook, license_obj, device)
        return _http_range_response(request, package_file)
