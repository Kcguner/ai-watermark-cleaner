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
