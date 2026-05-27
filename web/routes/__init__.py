# -*- coding: utf-8 -*-
"""API 路由包。"""

from ..user import (  # noqa: F401 — re-export for test monkeypatch
    get_or_create_current_user as get_or_create_current_user,
)
from ..user import save_user as save_user
from . import eval, gacha, info, resources


def create_routes(app):
    gacha.register_routes(app)
    resources.register_routes(app)
    info.register_routes(app)
    eval.register_routes(app)

    @app.context_processor
    def inject_static_url():
        def get_static_url(filename):
            if app.config.get("DEV_MODE", False):
                return filename
            try:
                from build.compress import load_manifest
                manifest = load_manifest()
                entry = manifest.get(filename, filename)
                if isinstance(entry, dict):
                    return entry["path"]
                return entry
            except Exception:
                return filename
        return dict(get_static_url=get_static_url)

    return app
