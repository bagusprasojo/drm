from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from devices.models import Device
from downloads.models import DownloadLog
from ebooks.models import Ebook
from ebooks.tasks import process_ebook_task
from licenses.models import EbookLicense

from .forms import DeviceRegisterForm, EbookUploadForm, LicenseForm


def _is_admin(user):
    return user.is_authenticated and user.is_staff


def login_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("portal-dashboard")
    if request.method == "POST":
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user and user.is_active and not getattr(user, "is_banned", False):
            login(request, user)
            return redirect("portal-dashboard")
        messages.error(request, "Login gagal")
    return render(request, "portal/login.html")


@login_required
@require_POST
def logout_page(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("portal-login")


@login_required
@require_GET
def dashboard(request: HttpRequest) -> HttpResponse:
    ebooks = Ebook.objects.order_by("-created_at")[:20]
    devices = Device.objects.order_by("-created_at")[:20]
    licenses = EbookLicense.objects.select_related("ebook", "device", "user").order_by("-issued_at")[:20]
    downloads = DownloadLog.objects.select_related("ebook", "device", "user").order_by("-downloaded_at")[:20]
    return render(
        request,
        "portal/dashboard.html",
        {
            "ebooks": ebooks,
            "devices": devices,
            "licenses": licenses,
            "downloads": downloads,
            "upload_form": EbookUploadForm(),
            "license_form": LicenseForm(),
            "device_form": DeviceRegisterForm(),
        },
    )


@login_required
@user_passes_test(_is_admin)
@require_POST
def upload_ebook(request: HttpRequest) -> HttpResponse:
    form = EbookUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Form upload tidak valid")
        return redirect("portal-dashboard")

    upload = form.cleaned_data["file"]
    suffix = Path(upload.name).suffix.lower()
    if suffix != ".pdf":
        messages.error(request, "Hanya .pdf yang didukung")
        return redirect("portal-dashboard")
    if upload.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        messages.error(request, "Ukuran file melebihi batas")
        return redirect("portal-dashboard")

    settings.SOURCE_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    source_path = settings.SOURCE_STORAGE_ROOT / upload.name
    with source_path.open("wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)

    ebook = Ebook.objects.create(
        title=form.cleaned_data["title"],
        author=form.cleaned_data.get("author", ""),
        source_path=str(source_path),
        uploaded_by=request.user,
    )
    process_ebook_task.delay(ebook.id)
    messages.success(request, "Upload berhasil, processing dimulai")
    return redirect("portal-dashboard")


@login_required
@user_passes_test(_is_admin)
@require_POST
def register_device(request: HttpRequest) -> HttpResponse:
    form = DeviceRegisterForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Form device tidak valid")
        return redirect("portal-dashboard")

    user = form.cleaned_data["user"]
    device_hash = form.cleaned_data["device_hash"]
    exists = Device.objects.filter(user=user, device_hash=device_hash).exists()
    if exists:
        messages.error(request, "Device hash sudah terdaftar untuk user tersebut")
        return redirect("portal-dashboard")

    Device.objects.create(
        user=user,
        device_hash=device_hash,
        device_name=form.cleaned_data["device_name"],
        os_version=form.cleaned_data["os_version"],
        app_version=form.cleaned_data["app_version"],
        revoked=False,
    )
    messages.success(request, "Device berhasil didaftarkan")
    return redirect("portal-dashboard")


@login_required
@user_passes_test(_is_admin)
@require_POST
def issue_license(request: HttpRequest) -> HttpResponse:
    form = LicenseForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Form license tidak valid")
        return redirect("portal-dashboard")

    ebook = form.cleaned_data["ebook"]
    device = form.cleaned_data["device"]
    license_obj, created = EbookLicense.objects.get_or_create(
        user=device.user,
        ebook=ebook,
        defaults={"device": device, "revoked": False},
    )
    if not created and license_obj.device_id != device.id:
        messages.error(request, "License ebook ini sudah terikat ke device lain")
        return redirect("portal-dashboard")
    if license_obj.revoked:
        license_obj.revoked = False
        license_obj.device = device
        license_obj.save(update_fields=["revoked", "device"])
    messages.success(request, "License berhasil di-issue")
    return redirect("portal-dashboard")


@login_required
@user_passes_test(_is_admin)
@require_POST
def revoke_license(request: HttpRequest, license_id: int) -> HttpResponse:
    license_obj = get_object_or_404(EbookLicense, id=license_id)
    license_obj.revoked = True
    license_obj.save(update_fields=["revoked"])
    messages.success(request, "License berhasil di-revoke")
    return redirect("portal-dashboard")


@login_required
@user_passes_test(_is_admin)
@require_POST
def revoke_device(request: HttpRequest, device_id: int) -> HttpResponse:
    device = get_object_or_404(Device, id=device_id)
    device.revoked = True
    device.save(update_fields=["revoked"])
    messages.success(request, "Device berhasil di-revoke")
    return redirect("portal-dashboard")
