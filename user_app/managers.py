from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(email__iexact=username.strip())

    def create_user(self, email, password=None, **extra_fields):
        if not email or not email.strip():
            raise ValueError("Укажите электронную почту.")
        for field in ("name", "surname"):
            if not extra_fields.get(field, "").strip():
                raise ValueError("Укажите имя и фамилию.")
        user = self.model(email=self.normalize_email(email.strip()).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Суперпользователь должен иметь права администратора.")
        return self.create_user(email, password, **extra_fields)
