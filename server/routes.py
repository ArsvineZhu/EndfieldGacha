# -*- coding: utf-8 -*-
"""
API 路由模块

提供所有 API 端点的路由处理函数
"""

from flask import render_template, request, jsonify, session
from datetime import datetime

from core import CharGacha, WeaponGacha, GlobalConfigLoader
from .user import (
    get_or_create_current_user,
    save_user,
    reset_user_data,
)
from .resource import (
    process_recharge,
    process_exchange,
    consume_char_gacha_resources,
    consume_weapon_gacha_resources,
    update_last_visit,
)


# 全局配置实例
DEFAULT_CONFIG = GlobalConfigLoader("configs/config_1")


def create_routes(app):
    """创建所有路由"""

    # 主页
    @app.route("/")
    def index():
        # 自动获取或创建用户数据
        user_id, user_data = get_or_create_current_user(request)
        # 更新最后访问时间
        user_data["last_visit"] = datetime.now().isoformat()
        save_user(user_id, user_data)

        # 将用户ID存储在session中（可选，用于后续请求识别）
        session["user_id"] = user_id

        return render_template("index.html")

    # 抽卡 API
    @app.route("/api/gacha", methods=["POST"])
    def gacha():
        data = request.json
        pool_type = data.get("pool_type")
        count = data.get("count", 1)

        if pool_type not in ["char", "weapon"]:
            return jsonify({"error": "Invalid pool type"}), 400

        if count < 1 or count > 10:
            return jsonify({"error": "Invalid count"}), 400

        # 获取当前用户
        user_id, user_info = get_or_create_current_user(request)

        # 检查并消耗资源
        if pool_type == "char":
            success, error_msg = consume_char_gacha_resources(user_info, count)
            if not success:
                return jsonify({"error": error_msg}), 400
        else:  # weapon
            success, error_msg = consume_weapon_gacha_resources(user_info)
            if not success:
                return jsonify({"error": error_msg}), 400

        if pool_type == "char":
            # 初始化角色卡池实例
            char_gacha = CharGacha(DEFAULT_CONFIG)
            # 恢复计数器状态
            char_gacha.counters.total = user_info["char_gacha"]["total"]
            char_gacha.counters.no_6star = user_info["char_gacha"]["no_6star"]
            char_gacha.counters.no_5star_plus = user_info["char_gacha"]["no_5star_plus"]
            char_gacha.counters.no_up = user_info["char_gacha"]["no_up"]
            char_gacha.counters.guarantee_used = user_info["char_gacha"][
                "guarantee_used"
            ]

            results = []
            for _ in range(count):
                result = char_gacha.attempt()
                results.append(
                    {
                        "name": result.name,
                        "star": result.star,
                        "quota": result.quota,
                        "is_up_g": result.is_up_g,
                        "is_6_g": result.is_6_g,
                        "is_5_g": result.is_5_g,
                    }
                )

                # 更新收藏
                if result.name not in user_info["collection"]["chars"]:
                    user_info["collection"]["chars"][result.name] = {
                        "star": result.star,
                        "count": 0,
                    }
                user_info["collection"]["chars"][result.name]["count"] += 1

                # 发放武库配额奖励
                user_info["resources"]["arsenal_tickets"] = (
                    user_info["resources"].get("arsenal_tickets", 0) + result.quota
                )

            # 保存计数器状态
            user_info["char_gacha"]["total"] = char_gacha.counters.total
            user_info["char_gacha"]["no_6star"] = char_gacha.counters.no_6star
            user_info["char_gacha"]["no_5star_plus"] = char_gacha.counters.no_5star_plus
            user_info["char_gacha"]["no_up"] = char_gacha.counters.no_up
            user_info["char_gacha"][
                "guarantee_used"
            ] = char_gacha.counters.guarantee_used

            # 记录历史
            user_info["char_gacha"]["history"].extend(results)

            # 检查累计奖励：加急招募
            if (
                char_gacha.counters.total >= 30
                and not user_info["resources"]["urgent_used"]
            ):
                user_info["resources"]["urgent_recruitment"] += 1
                user_info["resources"]["urgent_used"] = True

        else:  # weapon
            # 初始化武器卡池实例
            weapon_gacha = WeaponGacha(DEFAULT_CONFIG)
            # 恢复计数器状态
            weapon_gacha.counters.total = user_info["weapon_gacha"]["total"]
            weapon_gacha.counters.no_6star = user_info["weapon_gacha"]["no_6star"]
            weapon_gacha.counters.no_up = user_info["weapon_gacha"]["no_up"]
            weapon_gacha.counters.guarantee_used = user_info["weapon_gacha"][
                "guarantee_used"
            ]

            results = []
            for _ in range(count):
                apply_results = weapon_gacha.attempt()
                for result in apply_results:
                    results.append(
                        {
                            "name": result.name,
                            "star": result.star,
                            "quota": result.quota,
                            "is_up_g": result.is_up_g,
                            "is_6_g": result.is_6_g,
                            "is_5_g": result.is_5_g,
                        }
                    )

                    # 更新收藏
                    if result.name not in user_info["collection"]["weapons"]:
                        user_info["collection"]["weapons"][result.name] = {
                            "star": result.star,
                            "count": 0,
                        }
                    user_info["collection"]["weapons"][result.name]["count"] += 1

            # 保存计数器状态
            user_info["weapon_gacha"]["total"] = weapon_gacha.counters.total
            user_info["weapon_gacha"]["no_6star"] = weapon_gacha.counters.no_6star
            user_info["weapon_gacha"]["no_up"] = weapon_gacha.counters.no_up
            user_info["weapon_gacha"][
                "guarantee_used"
            ] = weapon_gacha.counters.guarantee_used

            # 记录历史
            user_info["weapon_gacha"]["history"].extend(results)

        # 更新最后访问时间
        user_info["last_visit"] = datetime.now().isoformat()

        # 保存用户数据
        save_user(user_id, user_info)

        return jsonify({"results": results})

    # 加急招募 API
    @app.route("/api/urgent_recruitment", methods=["POST"])
    def urgent_recruitment():
        # 获取当前用户
        user_id, user_info = get_or_create_current_user(request)

        # 检查是否有加急招募次数
        if user_info["resources"]["urgent_recruitment"] < 1:
            return jsonify({"error": "加急招募次数不足"}), 400

        # 消耗 1 个加急招募次数
        user_info["resources"]["urgent_recruitment"] -= 1

        # 创建新的 CharGacha 实例（不计入先前卡池的保底计数）
        urgent_gacha = CharGacha(DEFAULT_CONFIG)

        # 执行 10 连抽
        results = []
        for _ in range(10):
            result = urgent_gacha.attempt(disable_guarantee=True)
            results.append(
                {
                    "name": result.name,
                    "star": result.star,
                    "quota": result.quota,
                    "is_up_g": result.is_up_g,
                    "is_6_g": result.is_6_g,
                    "is_5_g": result.is_5_g,
                }
            )

            # 更新收藏
            if result.name not in user_info["collection"]["chars"]:
                user_info["collection"]["chars"][result.name] = {
                    "star": result.star,
                    "count": 0,
                }
            user_info["collection"]["chars"][result.name]["count"] += 1

            # 发放武库配额奖励
            user_info["resources"]["arsenal_tickets"] = (
                user_info["resources"].get("arsenal_tickets", 0) + result.quota
            )

        # 记录历史
        user_info["char_gacha"]["history"].extend(results)

        # 更新最后访问时间
        user_info["last_visit"] = datetime.now().isoformat()

        # 保存用户数据
        save_user(user_id, user_info)

        return jsonify({"results": results})

    # 获取累计奖励 API
    @app.route("/api/rewards", methods=["GET"])
    def get_rewards():
        # 获取当前用户
        user_id, user_info = get_or_create_current_user(request)

        # 获取卡池类型参数，默认为角色卡池
        pool_type = request.args.get("pool_type", "char")

        if pool_type == "char":
            # 使用 core.py 中的 get_accumulated_reward 方法获取角色池奖励
            char_gacha = CharGacha(DEFAULT_CONFIG)
            char_gacha.counters.total = user_info["char_gacha"]["total"]
            reward_tuples = char_gacha.get_accumulated_reward()

            # 转换为前端需要的格式
            rewards = []
            for reward_name, count in reward_tuples:
                rewards.append(f"{reward_name} × {count}")

                # 检查是否是信物奖励，如果是，更新对应干员的收藏数量
                if "信物" in reward_name:
                    # 提取干员名称（假设信物格式为"干员名称的信物"）
                    char_name = reward_name.replace("的信物", "")
                    # 更新干员收藏数量
                    if char_name in user_info["collection"]["chars"]:
                        user_info["collection"]["chars"][char_name]["count"] += count
                    else:
                        # 如果干员不存在，创建新记录（假设为 6 星干员）
                        user_info["collection"]["chars"][char_name] = {
                            "star": 6,
                            "count": count,
                        }
        else:  # weapon
            # 使用 core.py 中的 get_accumulated_reward 方法获取武器池奖励
            weapon_gacha = WeaponGacha(DEFAULT_CONFIG)
            weapon_gacha.counters.total = user_info["weapon_gacha"]["total"]
            reward_tuples = weapon_gacha.get_accumulated_reward()

            # 转换为前端需要的格式
            rewards = []
            for reward_name, count in reward_tuples:
                rewards.append(f"{reward_name} × {count}")

        # 更新最后访问时间
        user_info["last_visit"] = datetime.now().isoformat()

        # 保存用户数据
        save_user(user_id, user_info)

        return jsonify({"rewards": rewards})

    # 获取用户数据 API
    @app.route("/api/user_data", methods=["GET"])
    def get_user_data():
        user_id, user_info = get_or_create_current_user(request)
        return jsonify(user_info)

    # 清空数据 API
    @app.route("/api/clear_data", methods=["POST"])
    def clear_data():
        # 获取当前用户
        user_id, user_info = get_or_create_current_user(request)

        # 重置用户数据（保留用户 ID 和创建时间）
        new_user_data = reset_user_data(user_id, user_info.get("created_at"))

        # 保存用户数据
        save_user(user_id, new_user_data)

        return jsonify({"message": "数据已清空"})

    # 充值 API
    @app.route("/api/recharge", methods=["POST"])
    def recharge():
        data = request.json
        amount = data.get("amount", 0)

        # 获取当前用户
        user_id, user_info = get_or_create_current_user(request)

        # 处理充值
        success, message, origeometry_amount, is_first = process_recharge(
            user_info, amount
        )

        if not success:
            return jsonify({"error": message}), 400

        # 保存用户数据
        save_user(user_id, user_info)

        return jsonify(
            {
                "message": message,
                "is_first_recharge": is_first,
                "origeometry_amount": origeometry_amount,
            }
        )

    # 兑换 API
    @app.route("/api/exchange", methods=["POST"])
    def exchange():
        data = request.json
        from_resource = data.get("from")
        to_resource = data.get("to")
        amount = data.get("amount", 1)

        # 获取当前用户
        user_id, user_info = get_or_create_current_user(request)

        # 处理兑换
        success, message = process_exchange(
            user_info, from_resource, to_resource, amount
        )

        if not success:
            return jsonify({"error": message}), 400

        # 保存用户数据
        save_user(user_id, user_info)

        return jsonify({"message": message})

    # 获取历史记录 API
    @app.route("/api/history", methods=["GET"])
    def get_history():
        # 获取当前用户
        user_id, user_info = get_or_create_current_user(request)

        # 获取卡池类型参数
        pool_type = request.args.get("pool_type", "char")

        if pool_type not in ["char", "weapon"]:
            return jsonify({"error": "Invalid pool type"}), 400

        # 获取对应的历史记录
        if pool_type == "char":
            history = user_info["char_gacha"].get("history", [])
        else:
            history = user_info["weapon_gacha"].get("history", [])

        return jsonify({"history": history})

    # 获取卡池信息 API
    @app.route("/api/pool_info", methods=["GET"])
    def get_pool_info():
        import json

        # 获取卡池类型参数，默认为角色卡池
        pool_type = request.args.get("pool_type", "char")

        try:
            pool_data = DEFAULT_CONFIG.get_pool_data(pool_type)
            # GlobalConfigLoader的constants属性就是gacha_rules.json的内容
            gacha_rules = DEFAULT_CONFIG.constants
        except FileNotFoundError as e:
            return jsonify({"error": f"配置文件不存在: {str(e)}"}), 404
        except (KeyError, json.JSONDecodeError) as e:
            return jsonify({"error": f"配置文件格式错误: {str(e)}"}), 500

        # 提取概率提升的物品（up_prob > 0 的物品）
        boosted_items = []
        for star in pool_data:
            for item in pool_data[star]:
                if item.get("up_prob", 0) > 0:
                    boosted_items.append(
                        {
                            "name": item["name"],
                            "star": int(star),
                            "type": item.get("type", ""),
                        }
                    )

        # 从gacha_rules配置中读取卡池名称
        pool_info = gacha_rules.get("pool_info", {})
        if pool_type == "char":
            pool_name = pool_info.get("char_pool_name", "特许寻访")
        else:
            pool_name = pool_info.get("weapon_pool_name", "武库申领")

        return jsonify({"pool_name": pool_name, "boosted_items": boosted_items})

    # 添加静态资源映射函数
    @app.context_processor
    def inject_static_url():
        def get_static_url(filename):
            """根据原始文件名获取哈希化后的URL，开发模式直接返回原始文件名"""
            if app.config.get("DEV_MODE", False):
                # 开发模式直接返回原始文件名
                return filename
            try:
                from app.utils.compress import load_manifest

                manifest = load_manifest()
                return manifest.get(filename, filename)
            except:
                # 如果无法加载manifest，返回原始文件名
                return filename

        return dict(get_static_url=get_static_url)

    return app
