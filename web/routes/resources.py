# -*- coding: utf-8 -*-
"""Resources API: 充值、兑换。"""

from flask import jsonify, request

from ..resource import process_exchange, process_recharge
from ..user import get_or_create_current_user, save_user


def register_routes(app):
    @app.route("/api/recharge", methods=["POST"])
    def recharge():
        data = request.json
        amount = data.get("amount", 0)
        user_id, user_info = get_or_create_current_user(request)

        success, message, origeometry_amount, is_first = process_recharge(user_info, amount)
        if not success:
            return jsonify({"error": message}), 400

        save_user(user_id, user_info)
        return jsonify({
            "message": message,
            "is_first_recharge": is_first,
            "origeometry_amount": origeometry_amount,
        })

    @app.route("/api/exchange", methods=["POST"])
    def exchange():
        data = request.json
        from_resource = data.get("from")
        to_resource = data.get("to")
        amount = data.get("amount", 1)
        user_id, user_info = get_or_create_current_user(request)

        success, message = process_exchange(user_info, from_resource, to_resource, amount)
        if not success:
            return jsonify({"error": message}), 400

        save_user(user_id, user_info)
        return jsonify({"message": message})
