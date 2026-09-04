# tests/test_metadata_cleaner.py
from PIL import Image
from cleaners.metadata_cleaner import strip_metadata_pil

def test_exif_stripped():
    img = Image.new("RGB", (50, 50), "red")
    exif = img.getexif()
    exif[271] = "Gemini"  # Make tag
    img.info["exif"] = exif.tobytes()
    out = strip_metadata_pil(img)
    assert out.getexif() is None or len(out.getexif()) == 0
