from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont


def create_avatar(name):
    image = Image.new("RGB", (256, 256), "#dce5ee")
    font_path = settings.BASE_DIR / "static/fonts/Neue_Haas_Grotesk_Display_Pro_75_Bold.otf"
    font = ImageFont.truetype(str(font_path), 140)
    draw = ImageDraw.Draw(image)
    draw.text((128, 128), name.strip()[:1].upper() or "?", font=font,
              fill="#334155", anchor="mm")
    output = BytesIO()
    image.save(output, format="PNG")
    return ContentFile(output.getvalue(), name=f"{uuid4().hex}.png")
