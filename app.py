"""Local Flask server: upload -> cleaners -> download. No business logic here."""
from __future__ import annotations
import io
import socket
import sys
import tempfile
import threading
import webbrowser
import zipfile
from pathlib import Path
from flask import Flask, request, send_file, jsonify, render_template
from jinja2 import TemplateNotFound
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
from cleaners.registry import get_signature, list_sources
from cleaners.image_cleaner import clean_image
from cleaners.pdf_cleaner import clean_pdf
from cleaners.pptx_cleaner import clean_pptx
from cleaners.metadata_cleaner import strip_metadata_pil

ALLOWED = {".png", ".jpg", ".jpeg", ".pdf", ".pptx"}
MAX_MB = 50


def _base_path() -> Path:
    """Return the base directory for bundled resources.

    When frozen (e.g. PyInstaller), resources live under sys._MEIPASS;
    otherwise they live next to this file.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def create_app() -> Flask:
    base = _base_path()
    app = Flask(
        __name__,
        template_folder=str(base / "templates"),
        static_folder=str(base / "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

    @app.get("/")
    def index():
        try:
            return render_template("index.html", sources=list_sources())
        except TemplateNotFound:
            return jsonify(sources=list_sources())

    @app.get("/api/health")
    def health():
        return jsonify(ok=True)

    @app.errorhandler(413)
    def too_large(e):
        return jsonify(error=f"file too large (max {MAX_MB} MB)"), 413

    @app.errorhandler(500)
    def internal(e):
        if app.debug:
            raise e
        return jsonify(error="internal error"), 500

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
        stem = Path(secure_filename(f.filename)).stem or "cleaned"

        if ext in (".png", ".jpg", ".jpeg"):
            raw = f.read()
            try:
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                out_img = strip_metadata_pil(clean_image(img, sig))
                buf = io.BytesIO()
                fmt = "PNG" if ext == ".png" else "JPEG"
                out_img.save(buf, format=fmt, quality=95)
                buf.seek(0)
            except (UnidentifiedImageError, OSError, ValueError) as e:
                return jsonify(error=f"invalid or corrupt image: {e}"), 400
            except Exception as e:
                return jsonify(error=f"invalid or corrupt image: {e}"), 400
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            return send_file(buf, mimetype=mime, as_attachment=True,
                             download_name=f"{stem}_cleaned{ext}")

        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / f"in{ext}"
            outp = Path(td) / f"out{ext}"
            try:
                f.save(str(inp))
                if ext == ".pdf":
                    clean_pdf(str(inp), str(outp), sig)
                    mime = "application/pdf"
                else:
                    clean_pptx(str(inp), str(outp), sig)
                    mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                data = outp.read_bytes()
            except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as e:
                return jsonify(error=f"invalid or corrupt file: {e}"), 400
            except Exception as e:
                # Map known bad-file errors from fitz/pptx to 400;
                # anything else is truly unexpected -> 500.
                mod = type(e).__module__.lower()
                name = type(e).__name__.lower()
                if ("fitz" in mod or "pymupdf" in mod or "pptx" in mod
                        or "zip" in name or "package" in name
                        or "filedata" in name or "emptyfile" in name
                        or "invalid" in name):
                    return jsonify(error=f"invalid or corrupt file: {e}"), 400
                return jsonify(error="internal error"), 500
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
    threading.Timer(1.0, webbrowser.open, args=(f"http://127.0.0.1:{port}",)).start()
    app.run(host="127.0.0.1", port=port, debug=False)
