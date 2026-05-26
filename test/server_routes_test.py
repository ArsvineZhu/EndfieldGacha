import copy
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import web  # noqa: E402 — load before routes to allow monkeypatching sub-module imports
import web.user  # noqa: E402


def _build_user_info() -> dict:
    return {
        "char_gacha": {
            "total": 0,
            "no_6star": 0,
            "no_5star_plus": 0,
            "no_up": 0,
            "guarantee_used": False,
            "operations": [],
        },
        "weapon_gacha": {"total": 0, "operations": []},
        "collection": {"chars": {}, "weapons": {}},
        "resources": {
            "chartered_permits": 0,
            "oroberyl": 0,
            "arsenal_tickets": 0,
            "origeometry": 0,
            "urgent_recruitment": 1,
            "urgent_used": False,
        },
        "last_visit": "",
    }


def test_urgent_recruitment_api_guarantees_at_least_one_5star_plus(monkeypatch):
    store = {"user_id": "u-test", "user_info": _build_user_info()}

    def fake_get_or_create_current_user(_request):
        return store["user_id"], store["user_info"]

    def fake_save_user(user_id, user_info):
        store["user_id"] = user_id
        store["user_info"] = copy.deepcopy(user_info)

    # Patch BEFORE importing routes sub-modules (via create_app)
    monkeypatch.setattr(web.user, "get_or_create_current_user", fake_get_or_create_current_user)
    monkeypatch.setattr(web.user, "save_user", fake_save_user)

    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()

    for _ in range(200):
        store["user_info"]["resources"]["urgent_recruitment"] = 1
        response = client.post("/api/urgent_recruitment")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload is not None
        assert "results" in payload
        assert len(payload["results"]) == 10
        assert max(item["star"] for item in payload["results"]) >= 5
