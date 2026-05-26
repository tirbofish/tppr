# tppr-backend

This is the backend, which stores the database and the past paper questions. 

on launch, you can take a look at the API documentation (powered by swagger) at [localhost:5000/api/docs/](http://localhost:5000/api/docs/)

## running

this requires **uv** to be installed.

```bash
uv run src/main.py
```

### api only

sicne you can launch the frontend as its own server, it would only be right to serve the backend by itself. for that, we have a specific flag:
```bash
uv run src/main.py --api-only
```

## PDF OCR configuration

PDF uploads are stored in SeaweedFS, then the backend creates a time-limited signed share URL and sends that URL to Mistral OCR using `document_url`.

Required for OCR:

- `MISTRAL_API_KEY`: your Mistral API key.
- `BACKEND_PUBLIC_URL`: the public base URL Mistral can reach, for example `https://your-domain.example`. If omitted, the backend falls back to the incoming request host, which usually will not work for local-only URLs like `localhost`.

Optional:

- `PDF_SHARE_LINK_SECRET`: signing secret for PDF share links. Falls back to `JWT_SECRET_KEY`, then `SECRET_KEY`.
- `PDF_SHARE_LINK_TTL_SECONDS`: signed link lifetime in seconds. Defaults to `3600`.
- `MISTRAL_OCR_MODEL`: defaults to `mistral-ocr-latest`.
- `MISTRAL_OCR_TABLE_FORMAT`: defaults to `html`.
- `MISTRAL_OCR_INCLUDE_IMAGE_BASE64`: defaults to `1`.
