from django import forms

from accounts.models import User
from devices.models import Device
from ebooks.models import Ebook


class EbookUploadForm(forms.Form):
    title = forms.CharField(max_length=255)
    author = forms.CharField(max_length=255, required=False)
    file = forms.FileField()


class LicenseForm(forms.Form):
    ebook = forms.ModelChoiceField(queryset=Ebook.objects.none())
    device = forms.ModelChoiceField(queryset=Device.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ebook"].queryset = Ebook.objects.order_by("-created_at")
        self.fields["device"].queryset = Device.objects.filter(revoked=False).order_by("-created_at")


class DeviceRegisterForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none())
    device_hash = forms.CharField(max_length=255)
    device_name = forms.CharField(max_length=255)
    os_version = forms.CharField(max_length=255)
    app_version = forms.CharField(max_length=64)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.order_by("email")
