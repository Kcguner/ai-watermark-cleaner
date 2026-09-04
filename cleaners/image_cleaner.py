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
