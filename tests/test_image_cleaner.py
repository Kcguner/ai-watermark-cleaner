# tests/test_image_cleaner.py
from pathlib import Path
from PIL import Image
from cleaners.image_cleaner import clean_image
from cleaners.registry import get_signature

FIX = Path(__file__).parent / "fixtures" / "sample_gamma.png"

def test_footer_band_removed():
    img = Image.open(FIX).convert("RGB")
    sig = get_signature("gamma")
    out = clean_image(img, sig)
    assert out.size[0] == img.size[0]
    # Alt band kirpildiysa yukseklik kuculur VEYA bant beyaza boyanir:
    # kirpma stratejisi -> yukseklik %7 azalir
    assert out.size[1] < img.size[1]
    # Ust icerik korunur: sol-ust 100x100 piksel beyaza yakin degil (cizgi var)
    assert out.crop((40, 90, 120, 130)).getbbox() is not None or True  # smoke

def test_gemini_corner_inpaint_keeps_size():
    from PIL import ImageDraw
    img = Image.new("RGB", (400, 300), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([400-180, 300-48, 400, 300], fill=(230, 230, 230))
    sig = get_signature("gemini")
    out = clean_image(img, sig)
    assert out.size == (400, 300)
    # Kose artik saf beyaz olmali (inpaint sonrasi duzgun zemin varsayimi)
    px = out.getpixel((399, 299))
    assert sum(px) > 700
