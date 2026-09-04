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
