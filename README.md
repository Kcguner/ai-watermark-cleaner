# AI Watermark Cleaner

Remove visible AI watermarks from your own exports — PNG, JPG, PDF and PPTX — entirely on your device.

## Quick start

**Option A — Python (pip):**

```bat
pip install -r requirements.txt
python app.py
```

Your browser opens automatically at `http://127.0.0.1:<port>`. Upload a file, pick the source (gamma / gemini / generic), click **Clean file**, and the cleaned file downloads with a `_cleaned` suffix.

**Option B — Windows executable (no Python needed):**

1. Download `watermark-cleaner` from the Releases page.
2. Double-click `watermark-cleaner.exe`.
3. Your browser opens automatically; use the app the same way as above.

Supported inputs: `.png`, `.jpg`, `.jpeg`, `.pdf`, `.pptx` (max 50 MB per file).

## Privacy

Localhost only. The Flask server binds to `127.0.0.1` on a free port, opens your local browser, and processes files in memory or in a temporary directory. No upload, no cloud, no telemetry — files never leave your device.

## Capabilities and limits

| Watermark | Status | How it is handled |
|---|---|---|
| Gamma footer band (PDF / PPTX / image) | ✅ Removed | Bottom ~7% band redacted (PDF text/vector) or cropped (images); PPTX footer shapes matching keywords removed |
| Corner badge, e.g. Nano Banana bottom-right 180×48 (images) | ✅ Removed | Region inpainted with OpenCV Telea |
| EXIF metadata (images) / Info + XMP (PDF) / core properties (PPTX) | ✅ Stripped | Image re-created without EXIF; PDF producer/creator/author/title/subject/keywords cleared and XMP deleted; PPTX author/last-modified-by cleared |
| SynthID / C2PA pixel-embedded invisible marks | ⚠️ Partial | The visible badge is removed, but pixel-embedded invisible signals (Google SynthID, C2PA content credentials) survive cropping/inpainting and redaction. This tool does not detect or erase steganographic or cryptographic provenance marks. Do not rely on it to anonymize AI origin. |

## Tested versions

- Gamma: 2026-08 (footer band signature in `config/watermarks.json`)
- Nano Banana (Gemini image model): 2026-08 (corner badge signature in `config/watermarks.json`)

AI vendors change their watermark placement without notice. If a new export leaves residue, update the matching entry in `config/watermarks.json` (`band_ratio`, `w`/`h`/`corner` for badges) and re-run the test suite. No code change is needed for geometry tweaks — signatures are loaded at runtime by `cleaners/registry.py`.

## Windows SmartScreen note

The unsigned `.exe` may trigger Windows SmartScreen ("Windows protected your PC"). This is expected for new unsigned binaries. Click **More info → Run anyway** to start it. If you prefer not to do that, use Option A (run from source with Python) instead.

## Legal

Use this tool only on content you own or are authorized to modify. Removing watermarks, credits, or provenance from third-party content you do not own may violate the generator's terms of service or applicable law (including invisible-provenance rules such as the EU AI Act transparency duties for AI-generated content). You are responsible for complying with the terms of Gamma, Google/Gemini, and any other provider whose files you process.

## Languages

Default language is English. Switch to Türkçe, Deutsch, Français, or Español at any time with the **Language** dropdown in the UI header. Translations ship in `static/i18n.js` and apply instantly without reloading.

## Project structure

```text
ai-watermark-cleaner/
├── app.py                    # Flask server: upload -> cleaners -> download (binds 127.0.0.1)
├── requirements.txt          # Flask, PyMuPDF, Pillow, opencv-python-headless, python-pptx, pytest
├── LICENSE                   # MIT
├── config/
│   └── watermarks.json       # Watermark signatures (geometry + tested versions)
├── cleaners/
│   ├── __init__.py
│   ├── registry.py           # Loads signatures from config/watermarks.json
│   ├── image_cleaner.py      # Footer crop + corner inpaint (OpenCV)
│   ├── pdf_cleaner.py        # Footer redaction + metadata strip (PyMuPDF)
│   ├── pptx_cleaner.py       # Footer shape removal (python-pptx)
│   └── metadata_cleaner.py   # EXIF / PDF Info+XMP strip
├── templates/
│   └── index.html            # Upload UI with language + source selectors
├── static/
│   ├── app.js                # Upload/download client logic
│   ├── i18n.js               # EN/TR/DE/FR/ES strings
│   └── style.css             # UI styling
├── tests/
│   ├── test_app.py
│   ├── test_image_cleaner.py
│   ├── test_metadata_cleaner.py
│   ├── test_pdf_cleaner.py
│   ├── test_pptx_cleaner.py
│   ├── test_registry.py
│   └── fixtures/
│       └── make_fixtures.py  # Generates synthetic Gamma-like fixtures
└── samples/
    └── .gitkeep              # Drop your own test files here (gitignored)
```

## Dev

```bat
pip install -r requirements.txt
python -m pytest -q
```

The suite has 10 tests covering the registry, image footer crop, corner inpaint, PDF redaction, PPTX shape removal, metadata stripping, and the Flask `/api/health` + `/api/clean` endpoints. All 10 must pass before a release. Signatures live in `config/watermarks.json`, so geometry updates do not require code changes — edit the JSON, add or regenerate fixtures via `tests/fixtures/make_fixtures.py` if needed, and re-run pytest.

## License

MIT — see [LICENSE](LICENSE).
