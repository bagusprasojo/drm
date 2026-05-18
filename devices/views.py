from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Device
from .serializers import DeviceRevokeSerializer, DeviceSerializer


class DeviceViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = DeviceSerializer

    def get_queryset(self):
        return Device.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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
