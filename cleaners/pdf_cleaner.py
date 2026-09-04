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
