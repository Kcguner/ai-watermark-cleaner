"""Local Flask server: upload -> cleaners -> download. No business logic here."""
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
        try:
            return render_template("index.html", sources=list_sources())
        except Exception:
            return jsonify(sources=list_sources())

    @app.get("/api/health")
    def health():
        return jsonify(ok=True)

    @app.post("/api/clean")
    def clean():
        f = request.files.get("file")
        source = request.form.get("source", "generic")
        if not f or not f.filename:
            return jsonify(error="no file"), 400
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED:
            return jsonify(error=f"unsupported type: {ext}"), 400
        try:
            sig = get_signature(source)
        except KeyError:
            sig = get_signature("generic")
        raw = f.read()
        stem = Path(secure_filename(f.filename)).stem or "cleaned"

        if ext in (".png", ".jpg", ".jpeg"):
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            out_img = strip_metadata_pil(clean_image(img, sig))
            buf = io.BytesIO()
            fmt = "PNG" if ext == ".png" else "JPEG"
            out_img.save(buf, format=fmt, quality=95)
            buf.seek(0)
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            return send_file(buf, mimetype=mime, as_attachment=True,
                             download_name=f"{stem}_cleaned{ext}")

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
                         download_name=f"{stem}_cleaned{ext}")
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
