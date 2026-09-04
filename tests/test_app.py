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
