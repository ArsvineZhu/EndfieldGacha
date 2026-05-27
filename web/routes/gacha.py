# -*- coding: utf-8 -*-
"""Gacha API: 抽卡、加急招募、累计奖励。"""

from datetime import datetime

from flask import jsonify, request

from gacha_core import CharGacha, GlobalConfigLoader, WeaponGacha

from .. import user as user_store
from ..resource import (
    consume_char_gacha_resources,
    consume_weapon_gacha_resources,
)

DEFAULT_CONFIG = GlobalConfigLoader("configs/config_6")


def _build_result_record(result, draw_number):
    return {
        "name": result.name,
        "star": result.star,
        "quota": result.quota,
        "is_up_g": result.is_up_g,
        "is_6_g": result.is_6_g,
        "is_5_g": result.is_5_g,
        "draw_number": draw_number,
    }


def _snapshot_resources(user_info):
    return {
        "chartered_permits": user_info["resources"].get("chartered_permits", 0),
        "oroberyl": user_info["resources"].get("oroberyl", 0),
        "arsenal_tickets": user_info["resources"].get("arsenal_tickets", 0),
        "origeometry": user_info["resources"].get("origeometry", 0),
        "urgent_recruitment": user_info["resources"].get("urgent_recruitment", 0),
    }


def _compute_delta(before, after):
    return {k: before[k] - after[k] for k in before}


def _update_char_collection(user_info, result):
    if result.name not in user_info["collection"]["chars"]:
        user_info["collection"]["chars"][result.name] = {"star": result.star, "count": 0}
    user_info["collection"]["chars"][result.name]["count"] += 1


def _update_weapon_collection(user_info, result):
    if result.name not in user_info["collection"]["weapons"]:
        weapon_type = ""
        try:
            pool_data = DEFAULT_CONFIG.get_pool_data("weapon")
            for star in pool_data:
                for item in pool_data[star]:
                    if item["name"] == result.name:
                        weapon_type = item.get("type", "")
                        break
                if weapon_type:
                    break
        except Exception:
            pass
        user_info["collection"]["weapons"][result.name] = {
            "star": result.star, "type": weapon_type, "count": 0,
        }
    user_info["collection"]["weapons"][result.name]["count"] += 1


def register_routes(app):
    # ------------------------------------------------------------------ 抽卡
    @app.route("/api/gacha", methods=["POST"])
    def gacha():
        data = request.json
        pool_type = data.get("pool_type")
        count = data.get("count", 1)

        if pool_type not in ("char", "weapon"):
            return jsonify({"error": "Invalid pool type"}), 400
        if count < 1 or count > 10:
            return jsonify({"error": "Invalid count"}), 400

        user_id, user_info = user_store.get_or_create_current_user(request)

        if pool_type == "char":
            ok, msg, _ = consume_char_gacha_resources(user_info, count)
            if not ok:
                return jsonify({"error": msg}), 400
        else:
            ok, msg, _ = consume_weapon_gacha_resources(user_info)
            if not ok:
                return jsonify({"error": msg}), 400

        results = []
        res_before = _snapshot_resources(user_info)

        if pool_type == "char":
            gacha = CharGacha(DEFAULT_CONFIG)
            gacha.counters.total = user_info["char_gacha"]["total"]
            gacha.counters.no_6star = user_info["char_gacha"]["no_6star"]
            gacha.counters.no_5star_plus = user_info["char_gacha"]["no_5star_plus"]
            gacha.counters.no_up = user_info["char_gacha"]["no_up"]
            gacha.counters.guarantee_used = user_info["char_gacha"]["guarantee_used"]

            for _ in range(count):
                r = gacha.attempt()
                results.append(_build_result_record(r, gacha.counters.total))
                _update_char_collection(user_info, r)
                user_info["resources"]["arsenal_tickets"] = (
                    user_info["resources"].get("arsenal_tickets", 0) + r.quota
                )

            user_info["char_gacha"]["total"] = gacha.counters.total
            user_info["char_gacha"]["no_6star"] = gacha.counters.no_6star
            user_info["char_gacha"]["no_5star_plus"] = gacha.counters.no_5star_plus
            user_info["char_gacha"]["no_up"] = gacha.counters.no_up
            user_info["char_gacha"]["guarantee_used"] = gacha.counters.guarantee_used

            op_type = "GET_ONE" if count == 1 else "GET_TEN"

            if gacha.counters.total >= 30 and not user_info["resources"]["urgent_used"]:
                user_info["resources"]["urgent_recruitment"] += 1
                user_info["resources"]["urgent_used"] = True

        else:
            gacha = WeaponGacha(DEFAULT_CONFIG)
            gacha.counters.total = user_info["weapon_gacha"]["total"]
            gacha.counters.no_6star = user_info["weapon_gacha"]["no_6star"]
            gacha.counters.no_up = user_info["weapon_gacha"]["no_up"]
            gacha.counters.guarantee_used = user_info["weapon_gacha"]["guarantee_used"]

            for _ in range(count):
                for r in gacha.attempt():
                    results.append(_build_result_record(r, gacha.counters.total))
                    _update_weapon_collection(user_info, r)

            user_info["weapon_gacha"]["total"] = gacha.counters.total
            user_info["weapon_gacha"]["no_6star"] = gacha.counters.no_6star
            user_info["weapon_gacha"]["no_up"] = gacha.counters.no_up
            user_info["weapon_gacha"]["guarantee_used"] = gacha.counters.guarantee_used

            op_type = "ISSUE"

        res_after = _snapshot_resources(user_info)
        consumed = _compute_delta(res_before, res_after)
        operation = {
            "type": op_type,
            "time": datetime.now().isoformat(),
            "consumed_resources": consumed,
            "results": results,
        }

        history_key = f"{pool_type}_gacha"
        user_info[history_key]["operations"].append(operation)
        user_info["last_visit"] = datetime.now().isoformat()
        user_store.save_user(user_id, user_info)

        return jsonify({"results": results})

    # ------------------------------------------------------------------ 加急招募
    @app.route("/api/urgent_recruitment", methods=["POST"])
    def urgent_recruitment():
        user_id, user_info = user_store.get_or_create_current_user(request)

        if user_info["resources"]["urgent_recruitment"] < 1:
            return jsonify({"error": "加急招募次数不足"}), 400

        res_before = _snapshot_resources(user_info)
        user_info["resources"]["urgent_recruitment"] -= 1

        gacha = CharGacha(DEFAULT_CONFIG)
        results = []
        for _ in range(10):
            r = gacha.attempt()
            results.append(_build_result_record(r, gacha.counters.total))
            _update_char_collection(user_info, r)
            user_info["resources"]["arsenal_tickets"] = (
                user_info["resources"].get("arsenal_tickets", 0) + r.quota
            )

        res_after = _snapshot_resources(user_info)
        consumed = _compute_delta(res_before, res_after)
        operation = {
            "type": "URGENT",
            "time": datetime.now().isoformat(),
            "consumed_resources": consumed,
            "results": results,
        }
        user_info["char_gacha"]["operations"].append(operation)
        user_info["last_visit"] = datetime.now().isoformat()
        user_store.save_user(user_id, user_info)

        return jsonify({"results": results})

    # ------------------------------------------------------------------ 累计奖励
    @app.route("/api/rewards", methods=["GET"])
    def get_rewards():
        user_id, user_info = user_store.get_or_create_current_user(request)
        pool_type = request.args.get("pool_type", "char")

        if pool_type == "char":
            gacha = CharGacha(DEFAULT_CONFIG)
            gacha.counters.total = user_info["char_gacha"]["total"]
            reward_tuples = gacha.get_accumulated_reward()
            for reward_name, count in reward_tuples:
                if "信物" in reward_name:
                    char_name = reward_name.replace("的信物", "")
                    if char_name in user_info["collection"]["chars"]:
                        user_info["collection"]["chars"][char_name]["count"] += count
                    else:
                        user_info["collection"]["chars"][char_name] = {"star": 6, "count": count}
        else:
            gacha = WeaponGacha(DEFAULT_CONFIG)
            gacha.counters.total = user_info["weapon_gacha"]["total"]
            reward_tuples = gacha.get_accumulated_reward()

        rewards = [f"{name} × {c}" for name, c in reward_tuples]
        user_info["last_visit"] = datetime.now().isoformat()
        user_store.save_user(user_id, user_info)

        return jsonify({"rewards": rewards})
