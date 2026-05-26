# -*- coding: utf-8 -*-
"""Info API: 主页、用户数据、清空数据、历史、卡池信息。"""

import json
from datetime import datetime

from flask import jsonify, render_template, request, session

from gacha_core import GlobalConfigLoader

from ..user import get_or_create_current_user, reset_user_data, save_user

DEFAULT_CONFIG = GlobalConfigLoader("configs/config_6")


def register_routes(app):
    # ------------------------------------------------------------------ 主页
    @app.route("/")
    def index():
        user_id, user_data = get_or_create_current_user(request)
        user_data["last_visit"] = datetime.now().isoformat()
        save_user(user_id, user_data)
        session["user_id"] = user_id
        return render_template("index.html")

    # ------------------------------------------------------------------ 用户数据
    @app.route("/api/user_data", methods=["GET"])
    def get_user_data():
        _, user_info = get_or_create_current_user(request)
        return jsonify(user_info)

    # ------------------------------------------------------------------ 清空数据
    @app.route("/api/clear_data", methods=["POST"])
    def clear_data():
        user_id, user_info = get_or_create_current_user(request)
        new_data = reset_user_data(user_id, user_info.get("created_at"))
        save_user(user_id, new_data)
        return jsonify({"message": "数据已清空"})

    # ------------------------------------------------------------------ 历史记录
    @app.route("/api/history", methods=["GET"])
    def get_history():
        _, user_info = get_or_create_current_user(request)
        pool_type = request.args.get("pool_type", "char")
        if pool_type not in ("char", "weapon"):
            return jsonify({"error": "Invalid pool type"}), 400
        operations = user_info[f"{pool_type}_gacha"].get("operations", [])
        return jsonify({"operations": operations})

    # ------------------------------------------------------------------ 卡池信息
    @app.route("/api/pool_info", methods=["GET"])
    def get_pool_info():
        pool_type = request.args.get("pool_type", "char")
        try:
            pool_data = DEFAULT_CONFIG.get_pool_data(pool_type)
            pool_info = DEFAULT_CONFIG.get_pool_info(pool_type)
        except FileNotFoundError as e:
            return jsonify({"error": f"配置文件不存在: {str(e)}"}), 404
        except (KeyError, json.JSONDecodeError) as e:
            return jsonify({"error": f"配置文件格式错误: {str(e)}"}), 500
        except ValueError as e:
            return jsonify({"error": f"配置校验失败: {str(e)}"}), 500

        boosted_items = []
        for star in pool_data:
            for item in pool_data[star]:
                if item.get("up_prob", 0) > 0:
                    boosted_items.append({
                        "name": item["name"],
                        "star": int(star),
                        "type": item.get("type", ""),
                    })

        pool_name = pool_info.get("name", "特许寻访" if pool_type == "char" else "武库申领")
        response = {"pool_name": pool_name, "boosted_items": boosted_items}

        if pool_type == "weapon":
            response["available_banners"] = [
                {
                    "id": b["id"],
                    "pool_name": b.get("pool_name", ""),
                    "open_time": b.get("open_time", ""),
                    "close_time": b.get("close_time", ""),
                    "boosted_items": [
                        {"name": i["name"], "star": 6, "type": i.get("type", "")}
                        for i in b.get("featured", {}).get("current_up", [])
                    ],
                }
                for b in DEFAULT_CONFIG.get_weapon_banners()
            ]
            response["default_banner_id"] = DEFAULT_CONFIG.get_active_weapon_banner_id()

        return jsonify(response)
