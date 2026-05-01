# tppr-backend

This is the backend, which stores the database and the past paper questions. 

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