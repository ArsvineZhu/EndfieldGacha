# -*- coding: utf-8 -*-
"""
Flask 应用工厂模块

提供 Flask 应用创建和配置功能
"""

import os
import re
from mimetypes import guess_type
from pathlib import Path

from flask import Flask, abort, request, send_file

# 获取项目根目录（server 包的上级目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HASHED_STATIC_PATTERN = re.compile(r"^(css|js)/[0-9a-f]{6}\.(css|js)(\.map)?$")


def create_app(dev_mode=False):
    """创建并配置 Flask 应用"""
    template_folder = os.path.join(PROJECT_ROOT, "web", "templates")
    source_static_folder = os.path.join(PROJECT_ROOT, "web", "static")
    dist_static_folder = os.path.join(PROJECT_ROOT, "dist", "static")
    static_folder = (
        source_static_folder
        if dev_mode
        else (dist_static_folder if os.path.exists(dist_static_folder) else source_static_folder)
    )
    
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.secret_key = os.environ.get(
        "ENDFIELD_SECRET_KEY",
        "endfield_gacha_secret_key_Arsvine_20260228",
    )
    app.config["DEV_MODE"] = dev_mode

    @app.before_request
    def _block_source_static_access():
        if app.config.get("DEV_MODE", False):
            return None
        if not request.path.startswith("/static/"):
            return None

        rel_path = request.path[len("/static/") :]
        if rel_path.startswith(("css/", "js/", "pages/")) and not HASHED_STATIC_PATTERN.match(rel_path):
            abort(404)
        return None

    @app.before_request
    def _serve_precompressed_static():
        if app.config.get("DEV_MODE", False):
            return None
        if request.method not in {"GET", "HEAD"}:
            return None
        if not request.path.startswith("/static/"):
            return None

        rel_path = request.path[len("/static/") :]
        if not rel_path:
            return None

        static_root = Path(app.static_folder or "")
        target = static_root / rel_path
        accept_encoding = request.headers.get("Accept-Encoding", "").lower()
        candidates = []
        if "br" in accept_encoding:
            candidates.append(("br", target.with_name(f"{target.name}.br")))
        if "gzip" in accept_encoding:
            candidates.append(("gzip", target.with_name(f"{target.name}.gz")))

        for encoding, candidate in candidates:
            if not candidate.is_file():
                continue
            mimetype = guess_type(rel_path)[0] or "application/octet-stream"
            response = send_file(candidate, mimetype=mimetype, conditional=True)
            response.headers["Content-Encoding"] = encoding
            response.headers["Vary"] = "Accept-Encoding"
            return response

        return None

    # 注册路由
    from .routes import create_routes

    create_routes(app)

    return app


def compress_static_files():
    """压缩静态文件"""
    try:
        from build.compress import main as compress_main

        print("正在压缩静态文件...")
        compress_main()
        print("静态文件压缩完成，启动服务")
    except Exception as e:
        print(f"压缩静态文件时出错：{e}")
