# -*- coding: utf-8 -*-
"""
Flask 应用工厂模块

提供 Flask 应用创建和配置功能
"""

import os
from flask import Flask


# 获取项目根目录（server 包的上级目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    """创建并配置 Flask 应用"""
    template_folder = os.path.join(PROJECT_ROOT, "app", "templates")
    static_folder = os.path.join(PROJECT_ROOT, "app", "static")
    
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.secret_key = "endfield_gacha_secret_key_Arsvine_20260228"

    # 注册路由
    from .routes import create_routes

    create_routes(app)

    return app


def compress_static_files():
    """压缩静态文件"""
    try:
        from app.utils.compress import main as compress_main

        print("正在压缩静态文件...")
        compress_main()
        print("静态文件压缩完成，启动服务")
    except Exception as e:
        print(f"压缩静态文件时出错：{e}")
