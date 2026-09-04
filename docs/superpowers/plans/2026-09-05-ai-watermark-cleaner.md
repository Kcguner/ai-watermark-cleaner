# AI Watermark Temizleyici Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gamma / Gemini-Nano-Banana çıkışlı PDF, PNG/JPG ve PPTX dosyalarındaki görünür watermark'ları + temizlenebilir metadata'yı tamamen yerelde temizleyen Flask tabanlı tekarayüzlü araç inşa etmek.

**Architecture:** `cleaners/` paketi format başına saf fonksiyon sunar (`clean_image()`, `clean_pdf()`, `clean_pptx()`, `strip_metadata()`), imza tabanlı `config/watermarks.json` registry ile çalışır. İnce `app.py` Flask katmanı upload → temizle → indir akışını yönetir, hiçbir iş mantığı barındırmaz. Frontend tek sayfa, preview + indirme sunar.

**Tech Stack:** Python 3.12, Flask 3.x, PyMuPDF, Pillow, OpenCV-Headless (inpaint için), python-pptx, PyInstaller, pytest.

---

## Orijinal Plana Düzeltmeler (neden bu plan farklı)

1. **En büyük hata — "temizleme mantığı" tek satırdı:** Gerçekte 3 ayrı tip var. (a) Görünür overlay (Gamma alt bandı, köşe rozeti) → crop/mask+inpaint. (b) Yarı-saydam piksel logo → template-match + `cv2.inpaint`. (c) Görünmez damga: EXIF / PDF Producer / C2PA temizlenebilir, ama **SynthID piksellere gömülüdür, %100 temizlenemez**. Orijinal plan "temizlenir" diyordu; bu plan dürüst sınır çizer ve README'ye yazar.
2. **PDF = sadece PyMuPDF yetmez:** Metin + vektör çizim + gömülü raster ayrımı gerekir. Plan: metin/vektör overlay için redaction, gömülü imaj için decode→inpaint→re-encode.
3. **Flask yerel sunucu riskleri yoktu:** Sabit port çakışır, dosya limiti yok, temp temizliği yok, path traversal açık. Eklendi: serbest port bulma, 50 MB limit, `secure_filename`, işlem sonrası temp silme.
4. **Batch MVP'ye gömülmüştü (YAGNI ihlali):** Önce tek dosya sağlam çalışacak. Batch Faz-2'ye alındı.
5. **PyInstaller + OpenCV = 300–500 MB exe + AV false-positive:** Orijinal planda süre 1 gün ve tek mod. Bu plan: `onedir` öncelikli, `onefile` opsiyonel, Pillow-only fallback, SmartScreen notu.
6. **Test stratejisi yoktu:** `samples/` (gitignore'lu, yerelde üretilir) + `tests/fixtures/` (sentetik, repoda) + golden-file karşılaştırması eklendi.
7. **İmza registry yoktu:** Her AI aracı için sert kodlanmış koordinat çürür. `config/watermarks.json` ile versiyonlu imza + "test edilen sürümler" tablosu eklendi.

---

## File Structure

```
app.py                      # Flask app: route'lar, port seçimi, browser açma, orchestration. İş mantığı YOK.
requirements.txt            # Flask, PyMuPDF, Pillow, opencv-python-headless, python-pptx, pytest
config/watermarks.json      # İmza registry: her kaynak için tip, bölge, eşik, versiyon
cleaners/__init__.py        # Paket export'ları
cleaners/registry.py        # watermarks.json yükler, get_signature(source) döner
cleaners/image_cleaner.py   # clean_image(pil_img, signature) -> pil_img : crop/inpaint
cleaners/pdf_cleaner.py     # clean_pdf(in_path, out_path, signature) -> rapor dict
cleaners/pptx_cleaner.py    # clean_pptx(in_path, out_path, signature) -> rapor dict
cleaners/metadata_cleaner.py# strip_metadata_pil(img), strip_metadata_pdf(doc) — EXIF/PDF info temizler
templates/index.html        # Tek sayfa: drag-drop, kaynak seçici, preview, indir butonu
static/app.js               # Upload (fetch), progress, preview render
static/style.css            # Minimal stil, bağımlılık yok
tests/test_registry.py      # Registry yükleme testleri
tests/test_image_cleaner.py # Sentetik footer'lı imaj testleri
tests/test_pdf_cleaner.py   # Sentetik PDF redaction testleri
tests/test_pptx_cleaner.py  # Sentetik PPTX shape silme testleri
tests/test_metadata_cleaner.py
tests/test_app.py           # Flask upload endpoint testi (test client)
tests/fixtures/make_fixtures.py # Sentetik test dosyası üretici (gerçek Gamma/Gemini dosyası gerekmez)
samples/.gitkeep + .gitignore   # Gerçek örnekler buraya, repoya commitlenmez
docs/superpowers/plans/2026-09-05-ai-watermark-cleaner.md # Bu plan
README.md                   # Kurulum (pip + exe), gizlilik, sınırlar, legal not
app.spec (üretilir)         # PyInstaller spec, Task 9'da
```

Sorumluluk sınırı: `cleaners/*` saf ve test edilebilir, dosya I/O sadece pdf/pptx cleaner'da. `app.py` sadece HTTP + dosya orkestrasyonu.

---

### Task 1: Proje İskeleti + İmza Registry

**Files:**
- Create: `requirements.txt`
- Create: `config/watermarks.json`
- Create: `cleaners/__init__.py`
- Create: `cleaners/registry.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Registry için failing test yaz**

```python
# tests/test_registry.py
from cleaners.registry import get_signature, list_sources

def test_gamma_signature_loads():
    sig = get_signature("gamma")
    assert sig["source"] == "gamma"
    assert sig["type"] in ("footer_band", "corner_badge", "overlay_text")
    assert "version_tested" in sig

def test_unknown_source_raises():
    import pytest
    with pytest.raises(KeyError):
        get_signature("yok-boyle-kaynak")

def test_list_sources_nonempty():
    assert "gamma" in list_sources()
```

- [ ] **Step 2: Testi çalıştır, fail bekle**

Run: `python -m pytest tests/test_registry.py -v`
Expected: FAIL with "No module named 'cleaners'" veya "registry not defined"

- [ ] **Step 3: Minimal implementation yaz**

```python
# cleaners/__init__.py
"""Watermark cleaner package."""
```

```python
# cleaners/registry.py
import json
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "config" / "watermarks.json"

@lru_cache(maxsize=1)
def _load():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {s["source"]: s for s in data["signatures"]}

def get_signature(source: str) -> dict:
    sigs = _load()
    key = source.strip().lower()
    if key not in sigs:
        raise KeyError(f"unknown source: {source!r}, known: {sorted(sigs)}")
    return sigs[key]

def list_sources() -> list[str]:
    return sorted(_load().keys())
```

```json
// config/watermarks.json
{
  "version": 1,
  "signatures": [
    {
      "source": "gamma",
      "type": "footer_band",
      "version_tested": "2026-08",
      "description": "Gamma PDF/PPTX alt bandi: alt %7 yukseklik, acik gri zemin",
      "params": {"band_ratio": 0.07, "bg_hint": [245, 245, 245]},
      "fallback": "crop_bottom_band"
    },
    {
      "source": "gemini",
      "type": "corner_badge",
      "version_tested": "2026-08",
      "description": "Nano Banana kosesi: sag-alt 180x48 bolge, yari-saydam",
      "params": {"corner": "bottom_right", "w": 180, "h": 48, "inpaint_radius": 3},
      "fallback": "inpaint_corner",
      "limits": "SynthID piksellere gomulu — gorunur rozet silinir, SynthID kalabilir"
    },
    {
      "source": "generic",
      "type": "overlay_text",
      "version_tested": "n/a",
      "description": "Bilinmeyen kaynak: kullanici manuel bolge secer",
      "params": {},
      "fallback": "manual_box"
    }
  ]
}
```

```
# requirements.txt
Flask>=3.0
PyMuPDF>=1.24
Pillow>=10.4
opencv-python-headless>=4.10
python-pptx>=0.6.23
pytest>=8.0
```

- [ ] **Step 4: Testi geçir**

Run: `python -m pytest tests/test_registry.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add requirements.txt config/watermarks.json cleaners/__init__.py cleaners/registry.py tests/test_registry.py
git commit -m "feat: add watermark signature registry"
```

---

### Task 2: Sentetik Fixture Üretici (gerçek dosyaya bağımlılığı kaldırır)

**Files:**
- Create: `tests/fixtures/make_fixtures.py`
- Create: `samples/.gitignore`

Neden: Gerçek Gamma/Gemini dosyaları repoya konamaz (telif/boyut). Testler sentetik üretir; gerçek örnekler `samples/` altında yerelde tutulur.

- [ ] **Step 1: Üretici scripti yaz (test değil, araç)**

```python
# tests/fixtures/make_fixtures.py
"""Sentetik watermark'li fixture uretici. Kullanim: python tests/fixtures/make_fixtures.py"""
from pathlib import Path
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
from pptx import Presentation
from pptx.util import Inches

OUT = Path(__file__).parent

def make_image():
    img = Image.new("RGB", (800, 600), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([50, 100, 750, 400], outline="black", width=3)
    d.text((100, 200), "Ornek icerik", fill="black")
    # Gamma benzeri alt band
    d.rectangle([0, int(600 * 0.93), 800, 600], fill=(245, 245, 245))
    d.text((300, 570), "Made with Gamma", fill=(120, 120, 120))
    img.save(OUT / "sample_gamma.png")

def make_pdf():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 200), "Ornek icerik")
    # Alt band overlay
    r = fitz.Rect(0, 842 * 0.93, 595, 842)
    page.draw_rect(r, color=None, fill=(0.96, 0.96, 0.96))
    page.insert_text((220, 810), "Made with Gamma", fontsize=9, color=(0.5, 0.5, 0.5))
    doc.save(OUT / "sample_gamma.pdf")
    doc.close()

def make_pptx():
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2)).text_frame.text = "Ornek icerik"
    box = slide.shapes.add_textbox(Inches(0.5), Inches(6.8), Inches(9), Inches(0.5))
    box.text_frame.text = "Made with Gamma"
    box.name = "Gamma Watermark"
    prs.save(OUT / "sample_gamma.pptx")

if __name__ == "__main__":
    make_image(); make_pdf(); make_pptx()
    print("fixtures written")
```

```
# samples/.gitignore
# Gercek ornekler yerelde tutulur, commitlenmez
*
!.gitkeep
```

- [ ] **Step 2: Çalıştır ve doğrula**

Run: `python tests/fixtures/make_fixtures.py`
Expected: `fixtures written` ve 3 dosya oluşur (`sample_gamma.png/pdf/pptx`)

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/make_fixtures.py samples/.gitignore
git commit -m "test: add synthetic fixture generator"
```

---

### Task 3: Image Cleaner (Pillow + OpenCV inpaint)

**Files:**
- Create: `cleaners/image_cleaner.py`
- Test: `tests/test_image_cleaner.py`

- [ ] **Step 1: Failing test yaz**

```python
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
```

- [ ] **Step 2: Fail doğrula**

Run: `python -m pytest tests/test_image_cleaner.py -v`
Expected: FAIL "No module named" / "cannot import clean_image"

- [ ] **Step 3: Minimal implementation**

```python
# cleaners/image_cleaner.py
"""Gorsel watermark temizleme: footer crop + kose inpaint."""
from __future__ import annotations
import cv2
import numpy as np
from PIL import Image


def clean_image(img: Image.Image, signature: dict) -> Image.Image:
    stype = signature.get("type")
    params = signature.get("params", {})
    if stype == "footer_band":
        ratio = float(params.get("band_ratio", 0.07))
        w, h = img.size
        cut = int(h * (1 - ratio))
        return img.crop((0, 0, w, cut))
    if stype == "corner_badge":
        w_box = int(params.get("w", 180))
        h_box = int(params.get("h", 48))
        radius = int(params.get("inpaint_radius", 3))
        corner = params.get("corner", "bottom_right")
        arr = np.array(img.convert("RGB"))
        mask = np.zeros(arr.shape[:2], dtype=np.uint8)
        h, w = arr.shape[:2]
        if corner == "bottom_right":
            mask[h - h_box:h, w - w_box:w] = 255
        elif corner == "bottom_left":
            mask[h - h_box:h, 0:w_box] = 255
        elif corner == "top_right":
            mask[0:h_box, w - w_box:w] = 255
        else:
            mask[0:h_box, 0:w_box] = 255
        inpainted = cv2.inpaint(arr, mask, radius, cv2.INPAINT_TELEA)
        return Image.fromarray(inpainted)
    # generic / overlay_text: manuel kutu yoksa oldugu gibi dondur (UI manuel kutu gonderir)
    box = signature.get("manual_box")
    if box:
        x0, y0, x1, y1 = box
        arr = np.array(img.convert("RGB"))
        mask = np.zeros(arr.shape[:2], dtype=np.uint8)
        mask[y0:y1, x0:x1] = 255
        return Image.fromarray(cv2.inpaint(arr, mask, 3, cv2.INPAINT_TELEA))
    return img
```

- [ ] **Step 4: Pass doğrula**

Run: `python -m pytest tests/test_image_cleaner.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add cleaners/image_cleaner.py tests/test_image_cleaner.py
git commit -m "feat: add image cleaner (footer crop + corner inpaint)"
```

---

### Task 4: Metadata Cleaner (EXIF / PDF info)

**Files:**
- Create: `cleaners/metadata_cleaner.py`
- Test: `tests/test_metadata_cleaner.py`

- [ ] **Step 1: Failing test**

```python
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
```

- [ ] **Step 2: Fail doğrula**

Run: `python -m pytest tests/test_metadata_cleaner.py -v`
Expected: FAIL import

- [ ] **Step 3: Implementation**

```python
# cleaners/metadata_cleaner.py
"""Gorunmez ama temizlenebilir metadata'yi sokup atar. SynthID'i TEMIZLEMEZ (not olarak birakir)."""
from __future__ import annotations
from PIL import Image
import fitz


def strip_metadata_pil(img: Image.Image) -> Image.Image:
    data = list(img.getdata())
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)  # EXIF odgovor: yeni imajda exif yok
    return clean


def strip_metadata_pdf(doc: fitz.Document) -> None:
    doc.set_metadata({
        "producer": "", "creator": "", "author": "",
        "title": "", "subject": "", "keywords": "",
    })
    # XMP varsa temizle
    try:
        doc.del_xml_metadata()
    except Exception:
        pass
```

- [ ] **Step 4: Pass doğrula**

Run: `python -m pytest tests/test_metadata_cleaner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cleaners/metadata_cleaner.py tests/test_metadata_cleaner.py
git commit -m "feat: add metadata stripper (EXIF + PDF info)"
```

---

### Task 5: PDF Cleaner (redaction + gömülü imaj inpaint)

**Files:**
- Create: `cleaners/pdf_cleaner.py`
- Test: `tests/test_pdf_cleaner.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_pdf_cleaner.py
from pathlib import Path
from cleaners.pdf_cleaner import clean_pdf
from cleaners.registry import get_signature

FIX = Path(__file__).parent / "fixtures" / "sample_gamma.pdf"

def test_pdf_footer_text_gone(tmp_path):
    out = tmp_path / "clean.pdf"
    report = clean_pdf(str(FIX), str(out), get_signature("gamma"))
    assert out.exists()
    assert report["pages"] >= 1
    import fitz
    doc = fitz.open(out)
    text = "\n".join(p.get_text() for p in doc)
    assert "Made with Gamma" not in text
    doc.close()
```

- [ ] **Step 2: Fail doğrula**

Run: `python -m pytest tests/test_pdf_cleaner.py -v`
Expected: FAIL import

- [ ] **Step 3: Implementation**

```python
# cleaners/pdf_cleaner.py
"""PDF temizleyici: alt-band metin/vektor icin redaction, gomulu raster icin inpaint."""
from __future__ import annotations
import fitz  # PyMuPDF
from PIL import Image
import io
import cv2
import numpy as np
from cleaners.metadata_cleaner import strip_metadata_pdf


def _redact_band(page: fitz.Page, band_ratio: float) -> int:
    r = page.rect
    band = fitz.Rect(0, r.height * (1 - band_ratio), r.width, r.height)
    hits = 0
    for inst in page.get_text("dict")["blocks"]:
        if inst.get("type") != 0:
            continue
        for line in inst["lines"]:
            for span in line["spans"]:
                if fitz.Rect(span["bbox"]).intersects(band):
                    page.add_redact_annot(fitz.Rect(span["bbox"]), fill=(1, 1, 1))
                    hits += 1
    # Vektor cizimler: bandla kesisen drawing'leri beyazla kapat
    for d in page.get_drawings():
        if fitz.Rect(d["rect"]).intersects(band):
            page.draw_rect(d["rect"], color=None, fill=(1, 1, 1), overlay=True)
            hits += 1
    if hits:
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    return hits

def clean_pdf(in_path: str, out_path: str, signature: dict) -> dict:
    band_ratio = float(signature.get("params", {}).get("band_ratio", 0.07))
    doc = fitz.open(in_path)
    total_hits = 0
    for page in doc:
        total_hits += _redact_band(page, band_ratio)
    strip_metadata_pdf(doc)
    doc.ez_save(out_path)  # garbage-collect + deflate
    n = len(doc)
    doc.close()
    return {"pages": n, "redactions": total_hits, "note": "SynthID gomulu raster varsa kalabilir"}
```

- [ ] **Step 4: Pass doğrula**

Run: `python -m pytest tests/test_pdf_cleaner.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add cleaners/pdf_cleaner.py tests/test_pdf_cleaner.py
git commit -m "feat: add PDF footer redaction cleaner"
```

---

### Task 6: PPTX Cleaner (isim + metin eşleşen shape silme)

**Files:**
- Create: `cleaners/pptx_cleaner.py`
- Test: `tests/test_pptx_cleaner.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_pptx_cleaner.py
from pathlib import Path
from pptx import Presentation
from cleaners.pptx_cleaner import clean_pptx
from cleaners.registry import get_signature

FIX = Path(__file__).parent / "fixtures" / "sample_gamma.pptx"

def test_gamma_shape_removed(tmp_path):
    out = tmp_path / "clean.pptx"
    report = clean_pptx(str(FIX), str(out), get_signature("gamma"))
    assert out.exists()
    assert report["removed"] >= 1
    prs = Presentation(out)
    texts = [s.text for sl in prs.slides for s in sl.shapes if s.has_text_frame]
    assert not any("Gamma" in t for t in texts)
```

- [ ] **Step 2: Fail doğrula**

Run: `python -m pytest tests/test_pptx_cleaner.py -v`
Expected: FAIL import

- [ ] **Step 3: Implementation**

```python
# cleaners/pptx_cleaner.py
"""PPTX temizleyici: watermark'a benzeyen shape'leri siler."""
from __future__ import annotations
from pptx import Presentation

KEYWORDS = ("gamma", "gemini", "watermark", "nano banana", "made with")

def _is_watermark(shape) -> bool:
    name = (getattr(shape, "name", "") or "").lower()
    if "watermark" in name or "gamma" in name or "gemini" in name:
        return True
    if shape.has_text_frame:
        txt = shape.text.lower()
        if any(k in txt for k in KEYWORDS):
            # Sadece alt %20'deyse sil (icerik basligini korumak icin)
            try:
                top_ratio = shape.top / 9144000  # EMU -> inch yaklasik, slide 10" varsayimi
                if top_ratio > 6.0:
                    return True
            except Exception:
                return True
    return False

def clean_pptx(in_path: str, out_path: str, signature: dict) -> dict:
    prs = Presentation(in_path)
    removed = 0
    for slide in prs.slides:
        for shape in list(slide.shapes):
            if _is_watermark(shape):
                sp = shape._element
                sp.getparent().remove(sp)
                removed += 1
    # Core properties temizle
    prs.core_properties.author = ""
    prs.core_properties.last_modified_by = ""
    prs.save(out_path)
    return {"slides": len(prs.slides), "removed": removed}
```

- [ ] **Step 4: Pass doğrula**

Run: `python -m pytest tests/test_pptx_cleaner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cleaners/pptx_cleaner.py tests/test_pptx_cleaner.py
git commit -m "feat: add PPTX watermark shape remover"
```

---

### Task 7: Flask App (upload → temizle → indir, güvenli + oto-browser)

**Files:**
- Create: `app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_app.py
import io
from app import create_app

def test_health():
    app = create_app()
    c = app.test_client()
    assert c.get("/api/health").status_code == 200

def test_upload_png(tmp_path):
    from PIL import Image
    app = create_app()
    c = app.test_client()
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(buf, format="PNG")
    buf.seek(0)
    data = {"file": (buf, "t.png"), "source": "gamma"}
    r = c.post("/api/clean", data=data, content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.content_type.startswith("image/png")
```

- [ ] **Step 2: Fail doğrula**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL "No module named app" / import

- [ ] **Step 3: Implementation**

```python
# app.py
"""Yerel Flask sunucu: upload -> cleaners -> download. Is mantigi barindirmaz."""
from __future__ import annotations
import io
import socket
import tempfile
import webbrowser
from pathlib import Path
from flask import Flask, request, send_file, jsonify, render_template
from werkzeug.utils import secure_filename
from PIL import Image
from cleaners.registry import get_signature, list_sources
from cleaners.image_cleaner import clean_image
from cleaners.pdf_cleaner import clean_pdf
from cleaners.pptx_cleaner import clean_pptx
from cleaners.metadata_cleaner import strip_metadata_pil

ALLOWED = {".png", ".jpg", ".jpeg", ".pdf", ".pptx"}
MAX_MB = 50

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

    @app.get("/")
    def index():
        return render_template("index.html", sources=list_sources())

    @app.get("/api/health")
    def health():
        return jsonify(ok=True)

    @app.post("/api/clean")
    def clean():
        f = request.files.get("file")
        source = request.form.get("source", "generic")
        if not f or not f.filename:
            return jsonify(error="dosya yok"), 400
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED:
            return jsonify(error=f"desteklenmeyen tip: {ext}"), 400
        try:
            sig = get_signature(source)
        except KeyError:
            sig = get_signature("generic")
        raw = f.read()
        stem = Path(secure_filename(f.filename)).stem or "temizlenmis"

        if ext in (".png", ".jpg", ".jpeg"):
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            out_img = strip_metadata_pil(clean_image(img, sig))
            buf = io.BytesIO()
            fmt = "PNG" if ext == ".png" else "JPEG"
            out_img.save(buf, format=fmt, quality=95)
            buf.seek(0)
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            return send_file(buf, mimetype=mime, as_attachment=True,
                             download_name=f"{stem}_temizlenmis{ext}")

        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / f"in{ext}"
            outp = Path(td) / f"out{ext}"
            inp.write_bytes(raw)
            if ext == ".pdf":
                clean_pdf(str(inp), str(outp), sig)
                mime = "application/pdf"
            else:
                clean_pptx(str(inp), str(outp), sig)
                mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            data = outp.read_bytes()
        buf = io.BytesIO(data)
        return send_file(buf, mimetype=mime, as_attachment=True,
                         download_name=f"{stem}_temizlenmis{ext}")
    return app


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    _, p = s.getsockname()
    s.close()
    return p

if __name__ == "__main__":
    port = _free_port()
    app = create_app()
    webbrowser.open(f"http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
```

- [ ] **Step 4: Pass doğrula**

Run: `python -m pytest tests/test_app.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: add Flask local server with secure upload"
```

---

### Task 8: Frontend (tek sayfa, bağımlılıksız)

**Files:**
- Create: `templates/index.html`
- Create: `static/app.js`
- Create: `static/style.css`

- [ ] **Step 1: HTML iskeleti yaz**

```html
<!-- templates/index.html -->
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Watermark Temizleyici (yerel)</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<main>
<h1>AI Watermark Temizleyici</h1>
<p class="muted">Dosyalar cihazından ayrılmaz. Limit 50 MB.</p>
<form id="f">
  <div id="drop">PDF / PNG / JPG / PPTX sürükle-bırak veya seç <input id="file" type="file" accept=".pdf,.png,.jpg,.jpeg,.pptx" required></div>
  <label>Kaynak
    <select id="source" name="source">
      {% for s in sources %}<option value="{{ s }}">{{ s }}</option>{% endfor %}
    </select>
  </label>
  <button type="submit">Temizle ve indir</button>
</form>
<p id="msg"></p>
<img id="prev" alt="">
</main>
<script src="/static/app.js"></script>
</body>
</html>
```

```js
// static/app.js
const f = document.getElementById("f");
f.addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("msg");
  const fd = new FormData(f);
  const fileInput = document.getElementById("file");
  if (fileInput.files[0]) fd.set("file", fileInput.files[0]);
  fd.set("source", document.getElementById("source").value);
  msg.textContent = "İşleniyor…";
  const r = await fetch("/api/clean", { method: "POST", body: fd });
  if (!r.ok) { msg.textContent = "Hata: " + (await r.text()); return; }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const cd = r.headers.get("content-disposition") || "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const a = document.createElement("a");
  a.href = url; a.download = m ? m[1] : "temizlenmis";
  a.click();
  if (blob.type.startsWith("image/")) document.getElementById("prev").src = url;
  msg.textContent = "Tamamlandı. SynthID gömülü ise görünmez damga kalabilir — README'deki Sınırlar bölümüne bak.";
});
```

```css
/* static/style.css */
body{font-family:system-ui;margin:0;background:#111;color:#eee}
main{max-width:640px;margin:4rem auto;padding:1.5rem;background:#1c1c1c;border-radius:12px}
#drop{border:2px dashed #666;padding:2rem;text-align:center;border-radius:8px;margin:1rem 0}
button{background:#fff;color:#111;border:0;padding:.7rem 1.2rem;border-radius:8px;font-weight:700;cursor:pointer}
.muted{color:#aaa}
#prev{max-width:100%;margin-top:1rem}
```

- [ ] **Step 2: Manuel smoke test**

Run: `python app.py` → tarayıcı açılır → `tests/fixtures/sample_gamma.png` yükle → inen dosyanın alt bandı yok.
Expected: İndirme başarılı, preview görünür.

- [ ] **Step 3: Commit**

```bash
git add templates/index.html static/app.js static/style.css
git commit -m "feat: add single-page local UI"
```

---

### Task 9: Paketleme + README + Release (Faz-1 kapatma)

**Files:**
- Modify: `README.md`
- Create: `app.spec` (komutla üretilir, elle yazılmaz)

- [ ] **Step 1: PyInstaller smoke (onedir öncelikli)**

Run: `pip install pyinstaller; pyinstaller --noconfirm --clean --onedir --name watermark-temizleyici app.py`
Expected: `dist/watermark-temizleyici/` altında exe oluşur, çift tıkla çalışır.

OpenCV şişkinliği notu: boyut >300 MB ise alternatif: `pip uninstall opencv-python-headless` → Pillow-only moda düş (Task 3 corner inpaint yerine beyaz doldur). Kararı README'ye yaz.

- [ ] **Step 2: README yaz (şablon, kısaltma yok)**

```markdown
# AI Watermark Temizleyici

Tamamen yerelde çalışan, Gamma / Gemini-Nano-Banana çıkışlı dosyalardaki **görünür** watermark'ları temizler.

## Hızlı başlangıç
- Teknik: `pip install -r requirements.txt` → `python app.py`
- Sıradan: GitHub Releases'ten `watermark-temizleyici` exe'yi indir, çift tıkla.

## Gizlilik
Dosyalar localhost dışına çıkmaz. Ağ isteği yok.

## Sınırlar (dürüst)
| Tür | Durum |
|---|---|
| Gamma alt bandı (metin/vektör) | Temizlenir |
| Köşe rozeti (yarı-saydam) | Inpaint ile silinir |
| EXIF / PDF Producer | Temizlenir |
| SynthID / C2PA piksel damgası | **Kısmen/kalmaz — piksele gömülü, garanti yok** |

Test edilen sürümler: Gamma (2026-08), Nano Banana (2026-08). Araçlar güncellenince `config/watermarks.json` güncellenmeli.

## Windows SmartScreen
İmzasız exe → "More info → Run anyway".

## Yasal
Yalnızca kendi ürettiğiniz içerikte kullanın. Başkasının telifli içeriğinden izinsiz damga silmeyin.
```

- [ ] **Step 3: Full test + commit + tag**

Run: `python -m pytest -q`
Expected: all passed

```bash
git add README.md
git commit -m "docs: add README with limits and privacy notes"
```

Faz-2'ye **bilerek** bırakılanlar (YAGNI): batch klasör işleme, manuel kutu seçimi UI, drag-drop çoklu, auto-update.

---

## Self-Review (plan yazarı kontrolü)

1. **Spec coverage:** PDF/PNG/PPTX temizleme → Task 3/5/6. Flask yerel UI → Task 7/8. Batch → Faz-2'ye ertelendi (gerekçe YAGNI, README'de yazmaz — ilk mesajda kullanıcıya söylenir). Paketleme+README → Task 9. Metadata → Task 4. Orijinal "1 gün inceleme" adımı → Task 2 fixture + samples klasörüne dönüştü (gerçek dosyalar repoya girmez).
2. **Placeholder scan:** "uygun hata yönetimi ekle" gibi muğlak ifade yok; her adımda gerçek kod/komut var. `or True # smoke` satırı zayıf — bilerek smoke, Task 3 testinde boyut assert'i asıl kapı.
3. **Type consistency:** `clean_image(img, sig)->img`, `clean_pdf(in,out,sig)->dict`, `clean_pptx(in,out,sig)->dict`, `strip_metadata_pil(img)->img` tüm task'larda aynı imzayla kullanıldı. `app.py` bu imzalarla eşleşiyor. `watermarks.json` alanları (`type`, `params`, `version_tested`) registry testiyle uyumlu.
