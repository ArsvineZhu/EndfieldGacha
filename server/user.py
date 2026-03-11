# -*- coding: utf-8 -*-
"""
用户管理模块

提供用户相关的功能，包括：
- 用户ID生成
- 用户数据加载/保存
- 用户创建
"""

import json
import os
import hashlib
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any


# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "userdata.db")


# 初始化数据库连接
def init_db():
    """初始化数据库，创建用户表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建用户表，使用SQLite JSON类型存储嵌套数据
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        last_visit TEXT NOT NULL,
        char_gacha TEXT NOT NULL,
        weapon_gacha TEXT NOT NULL,
        collection TEXT NOT NULL,
        resources TEXT NOT NULL
    )
    """
    )

    conn.commit()
    conn.close()


# 初始化数据库
init_db()


def get_user_ip(request):
    """获取用户的真实 IP 地址"""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip
    return request.remote_addr


def generate_user_id(ip_address, user_agent=None):
    """基于 IP 地址和 User-Agent 生成用户唯一标识"""
    identifier = f"{ip_address}:{user_agent or ''}"
    return hashlib.md5(identifier.encode("utf-8")).hexdigest()


def load_user(user_id: str) -> Optional[Dict[str, Any]]:
    """加载指定用户的数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT created_at, last_visit, char_gacha, weapon_gacha, collection, resources
    FROM users WHERE user_id = ?
    """,
        (user_id,),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        created_at, last_visit, char_gacha, weapon_gacha, collection, resources = result
        return {
            "user_id": user_id,
            "created_at": created_at,
            "last_visit": last_visit,
            "char_gacha": json.loads(char_gacha),
            "weapon_gacha": json.loads(weapon_gacha),
            "collection": json.loads(collection),
            "resources": json.loads(resources),
        }
    return None


def save_user(user_id: str, user_data: Dict[str, Any]) -> None:
    """保存用户数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 先尝试更新，如果不存在则插入
    cursor.execute(
        """
    UPDATE users SET
        last_visit = ?,
        char_gacha = ?,
        weapon_gacha = ?,
        collection = ?,
        resources = ?
    WHERE user_id = ?
    """,
        (
            user_data["last_visit"],
            json.dumps(user_data["char_gacha"], ensure_ascii=False),
            json.dumps(user_data["weapon_gacha"], ensure_ascii=False),
            json.dumps(user_data["collection"], ensure_ascii=False),
            json.dumps(user_data["resources"], ensure_ascii=False),
            user_id,
        ),
    )

    if cursor.rowcount == 0:
        # 用户不存在，插入新记录
        cursor.execute(
            """
        INSERT INTO users (
            user_id, created_at, last_visit, char_gacha, weapon_gacha, collection, resources
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                user_data["created_at"],
                user_data["last_visit"],
                json.dumps(user_data["char_gacha"], ensure_ascii=False),
                json.dumps(user_data["weapon_gacha"], ensure_ascii=False),
                json.dumps(user_data["collection"], ensure_ascii=False),
                json.dumps(user_data["resources"], ensure_ascii=False),
            ),
        )

    conn.commit()
    conn.close()


def create_new_user(user_id):
    """创建新的用户数据"""
    return {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "last_visit": datetime.now().isoformat(),
        "char_gacha": {
            "total": 0,
            "no_6star": 0,
            "no_5star_plus": 0,
            "no_up": 0,
            "guarantee_used": False,
            "operations": [],  # 操作记录
        },
        "weapon_gacha": {
            "total": 0,
            "no_6star": 0,
            "no_up": 0,
            "guarantee_used": False,
            "operations": [],  # 操作记录
        },
        "collection": {"chars": {}, "weapons": {}},
        "resources": {
            "urgent_recruitment": 0,
            "urgent_used": False,
            "chartered_permits": 10,
            "oroberyl": 50000,
            "arsenal_tickets": 8000,
            "origeometry": 100,
            "total_recharge": 0,
            "first_recharge": {
                "6": True,
                "30": True,
                "98": True,
                "198": True,
                "328": True,
                "648": True,
            },
        },
    }


def get_or_create_current_user(request):
    """获取或创建当前用户"""
    user_id = generate_user_id(get_user_ip(request), request.headers.get("User-Agent"))
    user_data = load_user(user_id)

    if user_data is None:
        user_data = create_new_user(user_id)
        save_user(user_id, user_data)

    return user_id, user_data


def reset_user_data(user_id, original_created_at=None):
    """重置用户数据（保留用户 ID 和创建时间）"""
    if original_created_at is None:
        original_created_at = datetime.now().isoformat()

    return {
        "user_id": user_id,
        "created_at": original_created_at,
        "last_visit": datetime.now().isoformat(),
        "char_gacha": {
            "total": 0,
            "no_6star": 0,
            "no_5star_plus": 0,
            "no_up": 0,
            "guarantee_used": False,
            "operations": [],  # 操作记录
        },
        "weapon_gacha": {
            "total": 0,
            "no_6star": 0,
            "no_up": 0,
            "guarantee_used": False,
            "operations": [],  # 操作记录
        },
        "collection": {"chars": {}, "weapons": {}},
        "resources": {
            "urgent_recruitment": 0,
            "urgent_used": False,
            "chartered_permits": 10,
            "oroberyl": 50000,
            "arsenal_tickets": 8000,
            "origeometry": 100,
            "total_recharge": 0,
            "first_recharge": {
                "6": True,
                "30": True,
                "98": True,
                "198": True,
                "328": True,
                "648": True,
            },
        },
    }
