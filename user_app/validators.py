import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError


def normalize_phone(value):
    if not value:
        return ""
    if not re.fullmatch(r"(?:8|\+7)[0-9]{10}", value):
        raise ValidationError("Введите телефон в формате 8XXXXXXXXXX или +7XXXXXXXXXX.")
    return "+7" + value[-10:]


def validate_phone(value):
    normalize_phone(value)


def validate_github_url(value):
    try:
        url = urlsplit(value)
        valid = (
            url.scheme in ("http", "https")
            and url.hostname in ("github.com", "www.github.com")
            and not url.username
            and not url.password
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValidationError("Укажите ссылку на github.com.")
