from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import User
from .validators import normalize_phone


class EmailValidationMixin:
    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        users = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise ValidationError("Пользователь с такой электронной почтой уже зарегистрирован.")
        return email


class RegistrationForm(EmailValidationMixin, forms.ModelForm):
    password = forms.CharField(
        label="Пароль", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )

    class Meta:
        model = User
        fields = ("name", "surname", "email", "password")
        widgets = {"email": forms.EmailInput(attrs={"autocomplete": "email"})}

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get("password")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error("password", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={"autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Пароль", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        data = super().clean()
        if data.get("email") and data.get("password"):
            self.user = authenticate(self.request, email=data["email"].lower(), password=data["password"])
            if self.user is None:
                raise ValidationError("Неверный email или пароль.")
        return data


class ProfileForm(EmailValidationMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "surname", "email", "avatar", "about", "phone", "github_url")
        widgets = {
            "avatar": forms.FileInput(attrs={"accept": "image/*"}),
            "about": forms.Textarea(attrs={"rows": 4}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "+79991234567"}),
        }

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if phone and User.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Пользователь с таким телефоном уже зарегистрирован.")
        return phone

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and avatar.size > 5 * 1024 * 1024:
            raise ValidationError("Размер аватара не должен превышать 5 МБ.")
        return avatar


class AdminUserCreationForm(EmailValidationMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "name", "surname")


class AdminUserChangeForm(EmailValidationMixin, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
