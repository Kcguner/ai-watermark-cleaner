"""Image watermark cleaning: footer crop + corner inpaint (with blind-crop guards)."""
from __future__ import annotations
import cv2
import numpy as np
from PIL import Image


def _band_looks_like_watermark(img: Image.Image, ratio: float) -> bool:
    """Check whether the bottom band looks like a light footer band.

    Conditions (all must hold):
    (a) band mean brightness > 200 (light gray/white),
    (b) low variance inside band (grayscale std < 25 -> uniform),
    (c) band is distinct from the page content above it, so a fully
        uniform white page is NOT treated as a watermark (no data loss).

    Returns True if the band looks like a watermark footer.
    """
    w, h = img.size
    band_h = max(1, int(h * ratio))
    if band_h >= h:
        return False
    gray = np.asarray(img.convert("L"))
    band = gray[h - band_h:h, 0:w]
    if band.size == 0:
        return False
    band_mean = float(band.mean())
    band_std = float(band.std())
    if not (band_mean > 200 and band_std < 25):
        return False
    # Distinctness check: compare with the strip directly above the band.
    above = gray[max(0, h - 2 * band_h):h - band_h, 0:w]
    if above.size == 0:
        return True
    above_mean = float(above.mean())
    above_std = float(above.std())
    # Uniform page (e.g. clean white image): neighbor is equally light and
    # uniform with nearly the same mean -> not a distinct footer band.
    if above_mean > 200 and above_std < 25 and abs(band_mean - above_mean) < 3.0:
        return False
    return True


def _corner_looks_like_badge(img: Image.Image, corner: str, w: int, h: int) -> bool:
    """Check whether a corner region looks like a light badge.

    Returns True when the corner mean brightness >= 200. Dark photo content
    (mean < 200) means we skip inpainting to avoid damaging real content.
    Dimensions are clamped to the image size to handle tiny images.
    """
    W, H = img.size
    w = max(1, min(w, W))
    h = max(1, min(h, H))
    gray = np.asarray(img.convert("L"))
    Hh, Ww = gray.shape[:2]
    if corner == "bottom_right":
        region = gray[Hh - h:Hh, Ww - w:Ww]
    elif corner == "bottom_left":
        region = gray[Hh - h:Hh, 0:w]
    elif corner == "top_right":
        region = gray[0:h, Ww - w:Ww]
    else:
        region = gray[0:h, 0:w]
    if region.size == 0:
        return False
    return float(region.mean()) >= 200.0


def clean_image(img: Image.Image, signature: dict) -> Image.Image:
    stype = signature.get("type")
    params = signature.get("params", {})
    if stype == "footer_band":
        ratio = float(params.get("band_ratio", 0.07))
        if not _band_looks_like_watermark(img, ratio):
            return img
        w, h = img.size
        cut = int(h * (1 - ratio))
        return img.crop((0, 0, w, cut))
    if stype == "corner_badge":
        w_box = int(params.get("w", 180))
        h_box = int(params.get("h", 48))
        radius = int(params.get("inpaint_radius", 3))
        corner = params.get("corner", "bottom_right")
        W, H = img.size
        # Clamp badge size to image size to avoid empty slices on tiny images.
        w_box = max(1, min(w_box, W))
        h_box = max(1, min(h_box, H))
        if not _corner_looks_like_badge(img, corner, w_box, h_box):
            return img
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
    # generic / overlay_text: return unchanged unless a manual box is given
    # (the UI sends a manual box for user-selected regions).
    box = signature.get("manual_box")
    if box:
        x0, y0, x1, y1 = box
        arr = np.array(img.convert("RGB"))
        mask = np.zeros(arr.shape[:2], dtype=np.uint8)
        mask[y0:y1, x0:x1] = 255
        return Image.fromarray(cv2.inpaint(arr, mask, 3, cv2.INPAINT_TELEA))
    return img
