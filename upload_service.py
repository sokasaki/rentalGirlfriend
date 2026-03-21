import os
from random import random

from werkzeug.utils import secure_filename
from PIL import Image


def allowed_file(filename, allowed_extensions):
    return (
            '.' in filename and
            filename.rsplit('.', 1)[1].lower() in allowed_extensions
    )


def save_image(
        file,
        upload_folder,
        allowed_extensions,
        resize_to=(800, 800),
        thumb_size=(150, 150)
):
    if not file or file.filename == '':
        return 'no file'

    if not allowed_file(file.filename, allowed_extensions):
        return 'invalid file'

    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)

    original_path = os.path.join(upload_folder, filename)
    resized_path = os.path.join(upload_folder, f"resized_{name}{ext}")
    thumb_path = os.path.join(upload_folder, f"thumb_{name}{ext}")

    file.save(original_path)
    image = Image.open(original_path).convert('RGBA')

    # Resize original to the requested resize_to dimensions
    # This ensures the 'original' filename is actually a properly sized image.
    max_original = resize_to
    original_processed = image.copy()
    original_processed.thumbnail(max_original, Image.Resampling.LANCZOS)
    original_processed = original_processed.convert('RGB')
    original_processed.save(original_path, quality=95, optimize=True)

    # Resized version
    resized = image.copy()
    resized.thumbnail(resize_to)
    resized = resized.convert('RGB')
    resized.save(resized_path)

    # Thumbnail version
    thumb = image.copy()
    thumb.thumbnail(thumb_size)
    thumb = thumb.convert('RGB')
    thumb.save(thumb_path)

    return {
        "original": filename,
        "resized": f"resized_{name}{ext}",
        "thumbnail": f"thumb_{name}{ext}"
    }
