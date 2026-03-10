# -*- coding: utf-8 -*-
"""
资源管理模块

提供资源相关的操作，包括：
- 充值
- 兑换
"""

from datetime import datetime


# 充值挡位配置
RECHARGE_TIERS = {
    6: {"base": 2, "extra": 1, "total": 3},  # 2+1
    30: {"base": 12, "extra": 3, "total": 15},  # 12+3
    98: {"base": 42, "extra": 8, "total": 50},  # 42+8
    198: {"base": 85, "extra": 17, "total": 102},  # 85+17
    328: {"base": 141, "extra": 30, "total": 171},  # 141+30
    648: {"base": 280, "extra": 70, "total": 350},  # 280+70
}


def process_recharge(user_info, amount):
    """
    处理充值操作

    Args:
        user_info: 用户数据字典
        amount: 充值金额

    Returns:
        tuple: (success: bool, message: str, origeometry_amount: int, is_first: bool)
    """
    if amount <= 0:
        return False, "无效的充值金额", 0, False

    if amount not in RECHARGE_TIERS:
        return (
            False,
            "无效的充值金额，只支持 6、30、98、198、328、648 元",
            0,
            False,
        )

    # 检查是否是首充
    is_first_recharge = (
        user_info["resources"].get("first_recharge", {}).get(str(amount), False)
    )

    # 计算源石数量
    if is_first_recharge:
        if amount == 6:
            # 6 元档特殊，给 6 个源石
            origeometry_amount = 6
        else:
            # 其他档位双倍：基本数量 × 2
            base = RECHARGE_TIERS[amount]["base"]
            origeometry_amount = base * 2

        # 标记首充已使用
        user_info["resources"]["first_recharge"][str(amount)] = False
    else:
        # 非首充，正常数量：基本数量 + 额外赠送数量
        origeometry_amount = RECHARGE_TIERS[amount]["total"]

    # 增加源石
    user_info["resources"]["origeometry"] = (
        user_info["resources"].get("origeometry", 0) + origeometry_amount
    )

    # 更新累计充值金额
    user_info["resources"]["total_recharge"] = (
        user_info["resources"].get("total_recharge", 0) + amount
    )

    # 更新时间戳
    user_info["last_visit"] = datetime.now().isoformat()

    # 构建返回消息
    if is_first_recharge:
        message = (
            f"成功充值 {amount} 元，获得 {origeometry_amount} 个衍质源石（首充双倍）"
        )
    else:
        message = f"成功充值 {amount} 元，获得 {origeometry_amount} 个衍质源石"

    return True, message, origeometry_amount, is_first_recharge


def process_exchange(user_info, from_resource, to_resource, amount):
    """
    处理资源兑换操作

    Args:
        user_info: 用户数据字典
        from_resource: 源资源类型
        to_resource: 目标资源类型
        amount: 兑换数量

    Returns:
        tuple: (success: bool, message: str)
    """
    if not from_resource or not to_resource:
        return False, "无效的兑换参数"

    if from_resource == "origeometry":
        if to_resource == "oroberyl":
            # 1 衍质源石 → 75 嵌晶玉
            if user_info["resources"].get("origeometry", 0) >= amount:
                user_info["resources"]["origeometry"] -= amount
                user_info["resources"]["oroberyl"] = (
                    user_info["resources"].get("oroberyl", 0) + amount * 75
                )
                # 更新时间戳
                user_info["last_visit"] = datetime.now().isoformat()
                return True, f"成功兑换 {amount} 衍质源石为 {amount * 75} 嵌晶玉"
            else:
                return False, "衍质源石不足"
        elif to_resource == "arsenal_tickets":
            # 1 衍质源石 → 25 武库配额
            if user_info["resources"].get("origeometry", 0) >= amount:
                user_info["resources"]["origeometry"] -= amount
                user_info["resources"]["arsenal_tickets"] = (
                    user_info["resources"].get("arsenal_tickets", 0) + amount * 25
                )
                # 更新时间戳
                user_info["last_visit"] = datetime.now().isoformat()
                return True, f"成功兑换 {amount} 衍质源石为 {amount * 25} 武库配额"
            else:
                return False, "衍质源石不足"
        else:
            return False, "无效的兑换目标"
    else:
        return False, "仅支持从衍质源石兑换其他资源"


def consume_char_gacha_resources(user_info, count):
    """
    消耗角色卡池抽卡资源

    Args:
        user_info: 用户数据字典
        count: 抽卡次数 (1 或 10)

    Returns:
        tuple: (success: bool, error_message: str or None, consumed_resources: dict)
    """

    consumed_resources = {
        "chartered_permits": 0,
        "oroberyl": 0,
        "arsenal_tickets": 0,
        "origeometry": 0,
        "urgent_recruitment": 0,
    }

    if count == 1:
        # 单抽：1 张特许寻访凭证或 500 个嵌晶玉
        if user_info["resources"]["chartered_permits"] >= 1:
            user_info["resources"]["chartered_permits"] -= 1
            consumed_resources["chartered_permits"] = 1
            return True, None, consumed_resources
        elif user_info["resources"]["oroberyl"] >= 500:
            user_info["resources"]["oroberyl"] -= 500
            consumed_resources["oroberyl"] = 500
            return True, None, consumed_resources
        else:
            return False, "资源不足，无法进行单抽", consumed_resources
    elif count == 10:
        # 十连：优先使用凭证，不足部分用嵌晶玉补充
        available_permits = user_info["resources"].get("chartered_permits", 0)
        available_oroberyl = user_info["resources"].get("oroberyl", 0)

        # 需要的凭证和玉
        required_permits = 10
        required_oroberyl = 0

        # 计算需要消耗的凭证和玉
        if available_permits >= required_permits:
            # 凭证足够
            user_info["resources"]["chartered_permits"] -= required_permits
            consumed_resources["chartered_permits"] = required_permits
        else:
            # 凭证不足，用玉补充
            used_permits = available_permits
            user_info["resources"]["chartered_permits"] = 0
            consumed_resources["chartered_permits"] = used_permits

            remaining_permits = required_permits - used_permits
            required_oroberyl = remaining_permits * 500

            if available_oroberyl >= required_oroberyl:
                user_info["resources"]["oroberyl"] -= required_oroberyl
                consumed_resources["oroberyl"] = required_oroberyl
            else:
                return False, "资源不足，无法进行十连抽", consumed_resources
        return True, None, consumed_resources
    else:
        return False, "无效的抽卡次数", consumed_resources


def consume_weapon_gacha_resources(user_info):
    """
    消耗武器卡池申领资源

    Args:
        user_info: 用户数据字典

    Returns:
        tuple: (success: bool, error_message: str or None, consumed_resources: dict)
    """

    consumed_resources = {
        "chartered_permits": 0,
        "oroberyl": 0,
        "arsenal_tickets": 0,
        "origeometry": 0,
        "urgent_recruitment": 0,
    }

    # 武库申领消耗：1980 个武库配额
    if user_info["resources"]["arsenal_tickets"] >= 1980:
        user_info["resources"]["arsenal_tickets"] -= 1980
        consumed_resources["arsenal_tickets"] = 1980
        return True, None, consumed_resources
    else:
        return False, "武库配额不足，无法进行申领", consumed_resources


def update_last_visit(user_info):
    """更新最后访问时间"""
    user_info["last_visit"] = datetime.now().isoformat()
