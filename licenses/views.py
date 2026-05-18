from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from devices.models import Device
from ebooks.models import Ebook
from .models import EbookLicense
from .serializers import LicenseIssueSerializer, LicenseRevokeSerializer, LicenseVerifySerializer


class LicenseVerifyView(APIView):
    def post(self, request):
        serializer = LicenseVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exists = EbookLicense.objects.filter(
            user=request.user,
            ebook_id=serializer.validated_data["ebook_id"],
            device_id=serializer.validated_data["device_id"],
            revoked=False,
        ).exists()
        if not exists:
            return Response({"valid": False}, status=status.HTTP_403_FORBIDDEN)
        return Response({"valid": True})


class LicenseIssueView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = LicenseIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ebook = Ebook.objects.filter(id=serializer.validated_data["ebook_id"]).first()
        device = Device.objects.filter(id=serializer.validated_data["device_id"], revoked=False).first()
        if not ebook or not device:
            return Response({"detail": "Invalid ebook or device"}, status=status.HTTP_400_BAD_REQUEST)

        license_obj, created = EbookLicense.objects.get_or_create(
            user=device.user,
            ebook=ebook,
            defaults={"device": device, "revoked": False},
        )
        if not created and license_obj.device_id != device.id:
            return Response({"detail": "License already bound to another device"}, status=status.HTTP_409_CONFLICT)
        if not created and license_obj.revoked:
            license_obj.device = device
            license_obj.revoked = False
            license_obj.save(update_fields=["device", "revoked"])
        return Response({"status": "issued", "license_id": license_obj.id})


class LicenseRevokeView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = LicenseRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = EbookLicense.objects.filter(
            ebook_id=serializer.validated_data["ebook_id"],
            device_id=serializer.validated_data["device_id"],
        ).update(revoked=True)
        if not updated:
            return Response({"detail": "License not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "revoked"})
