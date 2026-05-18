from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import LoginView, LogoutView
from devices.views import DeviceViewSet
from ebooks.views import EbookViewSet
from licenses.views import LicenseIssueView, LicenseRevokeView, LicenseVerifyView

router = DefaultRouter()
router.register("device", DeviceViewSet, basename="device")
router.register("book", EbookViewSet, basename="book")

book_list = EbookViewSet.as_view({"get": "list"})
book_detail = EbookViewSet.as_view({"get": "retrieve"})
book_download = EbookViewSet.as_view({"post": "download"})
device_register = DeviceViewSet.as_view({"post": "create"})
device_revoke = DeviceViewSet.as_view({"post": "revoke"})

urlpatterns = [
    path("portal/", include("portal.urls")),
    path("api/auth/login", LoginView.as_view(), name="login"),
    path("api/auth/logout", LogoutView.as_view(), name="logout"),
    path("api/auth/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/device/register", device_register, name="device-register"),
    path("api/device/revoke", device_revoke, name="device-revoke"),
    path("api/books", book_list, name="book-list-srs"),
    path("api/book/<int:pk>", book_detail, name="book-detail-srs"),
    path("api/book/download", book_download, name="book-download-srs"),
    path("api/license/verify", LicenseVerifyView.as_view(), name="license-verify"),
    path("api/license/issue", LicenseIssueView.as_view(), name="license-issue"),
    path("api/license/revoke", LicenseRevokeView.as_view(), name="license-revoke"),
    path("api/", include(router.urls)),
]
