# Web App Module Knowledge Base

**Generated:** 2026-05-26
**Module:** Flask web application assets

## Overview

`app/` holds the Jinja template and the source static assets that are compressed before deployment.

## Structure

```text
app/
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── utils/
    └── compress.py
```

## Where to look

| Task | Location | Notes |
|---|---|---|
| Edit the main page | `templates/index.html` | Jinja2 template |
| Change source styles | `static/css/` | Re-run compression afterwards |
| Change source scripts | `static/js/` | Re-run compression afterwards |
| Compress assets | `utils/compress.py` | Used by `server/app.py` and `server.py` |
| Inspect Flask app logic | `../server/` | Actual server implementation lives in the `server/` package |

## Conventions

- Modify source assets, then regenerate compressed output
- Keep template logic simple
- The web app currently uses the server package in the repository root, not an `app.py` module inside `app/`

