"""Strip removable metadata. Does NOT clean SynthID (left as a note)."""
from __future__ import annotations
from PIL import Image
import fitz


def strip_metadata_pil(img: Image.Image) -> Image.Image:
    """Return a copy of img with EXIF/info metadata removed.

    Rebuilds pixel data via tobytes/frombytes (no getdata/putdata), which
    drops EXIF and the info dict. Palette (P mode) and transparency are
    explicitly preserved so RGBA/P round-trips keep their mode and visuals.
    """
    mode = img.mode
    size = img.size
    palette = None
    if mode == "P":
        try:
            palette = img.getpalette()
        except Exception:
            palette = None
    transparency = None
    try:
        transparency = img.info.get("transparency")
    except Exception:
        transparency = None
    raw = img.tobytes()
    clean = Image.frombytes(mode, size, raw)
    if mode == "P" and palette is not None:
        try:
            clean.putpalette(palette)
        except Exception:
            pass
    if transparency is not None:
        try:
            clean.info["transparency"] = transparency
        except Exception:
            pass
    # Drop any EXIF that may have been carried over (frombytes starts clean,
    # but be explicit for Pillow versions that attach an empty exif object).
    if hasattr(clean, "getexif"):
        try:
            ex = clean.getexif()
            if len(ex) > 0:
                ex.clear()
        except Exception:
            pass
    if clean.mode != mode:
        try:
            clean = clean.convert(mode)
        except Exception:
            pass
    return clean


def strip_metadata_pdf(doc: fitz.Document) -> None:
    doc.set_metadata({
        "producer": "", "creator": "", "author": "",
        "title": "", "subject": "", "keywords": "",
    })
    # Clear XMP metadata if present.
    try:
        doc.del_xml_metadata()
    except Exception:
        pass
