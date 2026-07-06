from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User, VerificationDocument


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[c for c in User.Role.choices if c[0] != User.Role.ADMIN],
        label=_("نوع الحساب"),
    )
    email = forms.EmailField(required=True, label=_("البريد الإلكتروني"))
    phone_number = forms.CharField(required=False, label=_("رقم الهاتف"))

    class Meta:
        model = User
        fields = ["username", "email", "phone_number", "role", "password1", "password2"]
        labels = {
            "username": _("اسم المستخدم"),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data.get("phone_number", "")
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user


class VerificationDocumentForm(forms.ModelForm):
    class Meta:
        model = VerificationDocument
        fields = ["document_type", "file"]
        labels = {
            "document_type": _("نوع المستند"),
            "file": _("الملف"),
        }
        widgets = {
            "document_type": forms.TextInput(
                attrs={"placeholder": _("مثال: السجل التجاري، بطاقة الهوية، رخصة السمسرة")}
            ),
        }
