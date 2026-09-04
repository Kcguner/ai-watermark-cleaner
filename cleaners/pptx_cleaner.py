"""PPTX cleaner: removes watermark-like shapes."""
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
            # Only remove if in the bottom area (protects main content headings)
            try:
                top_ratio = shape.top / 9144000  # EMU -> inches approx, assumes 10" slide
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
    # Clear core properties
    prs.core_properties.author = ""
    prs.core_properties.last_modified_by = ""
    prs.save(out_path)
    return {"slides": len(prs.slides), "removed": removed}
