from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Device
from .serializers import DeviceRevokeSerializer, DeviceSerializer


class DeviceViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = DeviceSerializer

    def get_queryset(self):
        return Device.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device, created = Device.objects.update_or_create(
            user=request.user,
            device_hash=data["device_hash"],
            defaults={
                "device_name": data.get("device_name", ""),
                "os_version": data.get("os_version", ""),
                "app_version": data.get("app_version", ""),
                "public_key_pem": data.get("public_key_pem", ""),
                "revoked": False,
            },
        )
        out = self.get_serializer(device)
        return Response(out.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="revoke")
    def revoke(self, request):
        serializer = DeviceRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = Device.objects.filter(
            id=serializer.validated_data["device_id"], user=request.user
        ).update(revoked=True)
        if not updated:
            return Response({"detail": "Device not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "revoked"})
