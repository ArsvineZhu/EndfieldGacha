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
from datetime import datetime


# 用户数据存储文件夹路径
USER_DATA_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "users")

# 确保用户数据文件夹存在
os.makedirs(USER_DATA_FOLDER, exist_ok=True)


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


def get_user_file_path(user_id):
    """获取用户数据文件路径"""
    return os.path.join(USER_DATA_FOLDER, f"{user_id}.json")


def load_user(user_id):
    """加载指定用户的数据"""
    user_file = get_user_file_path(user_id)
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_user(user_id, user_data):
    """保存用户数据"""
    user_file = get_user_file_path(user_id)
    with open(user_file, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)


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
            "history": [],
        },
        "weapon_gacha": {
            "total": 0,
            "no_6star": 0,
            "no_up": 0,
            "guarantee_used": False,
            "history": [],
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
            "history": [],
        },
        "weapon_gacha": {
            "total": 0,
            "no_6star": 0,
            "no_up": 0,
            "guarantee_used": False,
            "history": [],
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
