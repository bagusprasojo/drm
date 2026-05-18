from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="portal-dashboard"),
    path("login", views.login_page, name="portal-login"),
    path("logout", views.logout_page, name="portal-logout"),
    path("device/register", views.register_device, name="portal-device-register"),
    path("upload", views.upload_ebook, name="portal-upload"),
    path("license/issue", views.issue_license, name="portal-license-issue"),
    path("license/<int:license_id>/revoke", views.revoke_license, name="portal-license-revoke"),
    path("device/<int:device_id>/revoke", views.revoke_device, name="portal-device-revoke"),
]
