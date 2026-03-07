# -*- coding: utf-8 -*-
"""
Server 包

提供 Web 服务器功能

主要模块：
- app: Flask 应用工厂
- user: 用户管理
- resource: 资源操作
- routes: API 路由
"""

from .app import create_app, compress_static_files
from .user import (
    get_or_create_current_user,
    load_user,
    save_user,
    create_new_user,
)
from .resource import (
    process_recharge,
    process_exchange,
)

__all__ = [
    "create_app",
    "compress_static_files",
    "get_or_create_current_user",
    "load_user",
    "save_user",
    "create_new_user",
    "process_recharge",
    "process_exchange",
]
