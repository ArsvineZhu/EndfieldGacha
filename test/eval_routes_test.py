import json
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def _build_eval_payload():
    return {
        "resource": {
            "chartered_permits": 2,
            "oroberyl": 61000,
            "arsenal_tickets": 6000,
            "origeometry": 100,
        },
        "initial_counters": {
            "total": 0,
            "no_6star": 0,
            "no_5star_plus": 0,
            "no_up": 0,
            "guarantee_used": False,
            "urgent_used": False,
        },
        "preferences": {
            "goal_weight": 0.35,
            "utility_weight": 0.3,
            "resource_weight": 0.2,
            "risk_weight": 0.15,
            "alpha": 1.0,
            "current_up_value": 100.0,
            "past_up_value": 70.0,
            "normal_six_value": 45.0,
            "five_star_value": 6.0,
            "four_star_value": 1.0,
            "utility_log_map": {"low": 0.6, "high": 1.4, "curve": 1.0},
            "utility_absolute_log_map": {"low": 0.6, "high": 1.4, "curve": 1.0},
            "utility_absolute_reference": 700.0,
            "utility_mix_weight": 0.5,
            "resource_log_map": {"low": 0.6, "high": 1.5, "curve": 1.0},
            "opportunity_reference": 60.0,
            "risk_utility_weight": 0.6,
            "tail_ratio": 0.1,
            "future_resource_income": 0,
            "baseline_samples": 2,
            "baseline_seed": 20260525,
            "questionnaire_status": "completed",
            "questionnaire_consistency_ratio": 0.02,
        },
        "goals": [{"kind": "current_up", "target": 1}],
        "banner_plans": [
            {
                "config_name": "config_3",
                "strategy": {
                    "protocol_version": "strategy-protocol-v1",
                    "kind": "structured",
                    "rule": {
                        "node_type": "group",
                        "match": "any",
                        "children": [
                            {
                                "node_type": "condition",
                                "kind": "current_up",
                                "operator": ">=",
                                "value": 1,
                            },
                            {
                                "node_type": "condition",
                                "kind": "draws",
                                "operator": ">=",
                                "value": 10,
                            },
                        ],
                    },
                },
                "resource_increment": {
                    "chartered_permits": 0,
                    "oroberyl": 0,
                    "arsenal_tickets": 0,
                    "origeometry": 0,
                },
                "check_in": False,
                "use_origeometry": False,
                "is_core": True,
            }
        ],
        "scale": 4,
    }


def test_gacha_and_eval_pages_are_available():
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()

    assert client.get("/").status_code == 200
    assert client.get("/gacha").status_code == 200

    eval_response = client.get("/eval")
    assert eval_response.status_code == 200
    assert "终末地抽卡策略评估".encode("utf-8") in eval_response.data
    assert "跨卡池单方案评分器".encode("utf-8") in eval_response.data
    assert b"ARCHIVE / ORBITAL REVIEW" not in eval_response.data
    assert b"EVAL-01" not in eval_response.data


def test_eval_page_uses_ordered_classic_scripts_in_production():
    from web.app import create_app

    app = create_app(dev_mode=False)
    client = app.test_client()

    response = client.get("/eval")

    assert response.status_code == 200
    assert b'type="module"' not in response.data
    assert response.data.count(b"<script") == 5


def test_eval_configs_lists_all_char_banners():
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()

    response = client.get("/api/eval/configs")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    config_ids = [item["id"] for item in payload["configs"]]
    assert config_ids == [f"config_{index}" for index in range(1, 8)]
    assert payload["configs"][0]["pool_name"]
    assert "current_up" in payload["configs"][0]
    assert "past_up" in payload["configs"][0]


def test_eval_jobs_reject_invalid_payload():
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps({"banner_plans": [], "goals": []}),
        content_type="application/json",
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload is not None
    assert "error" in payload


def test_eval_job_submission_returns_job_id_and_status():
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps(_build_eval_payload()),
        content_type="application/json",
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload is not None
    assert payload["status"] == "queued"
    assert payload["job_id"]

    poll_response = client.get(f"/api/eval/jobs/{payload['job_id']}")
    assert poll_response.status_code == 200
    poll_payload = poll_response.get_json()
    assert poll_payload is not None
    assert poll_payload["job_id"] == payload["job_id"]
    assert poll_payload["status"] in {"queued", "running", "succeeded"}


def test_eval_jobs_accept_nested_strategy_groups():
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()

    payload = _build_eval_payload()
    payload["banner_plans"][0]["strategy"]["rule"] = {
        "node_type": "group",
        "match": "any",
        "children": [
            {
                "node_type": "group",
                "match": "all",
                "children": [
                    {
                        "node_type": "condition",
                        "kind": "current_up",
                        "operator": ">=",
                        "value": 1,
                    },
                    {
                        "node_type": "condition",
                        "kind": "resource_left",
                        "operator": ">=",
                        "value": 60,
                    },
                ],
            },
            {
                "node_type": "condition",
                "kind": "draws",
                "operator": ">=",
                "value": 30,
            },
        ],
    }

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 202
    body = response.get_json()
    assert body is not None
    assert body["status"] == "queued"


def test_eval_jobs_reject_inconsistent_questionnaire():
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()
    payload = _build_eval_payload()
    payload["preferences"]["questionnaire_status"] = "inconsistent"
    payload["preferences"]["questionnaire_consistency_ratio"] = 0.2

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body is not None
    assert body["error"].startswith("EVAL_QUESTIONNAIRE_INCONSISTENT:")


def test_eval_compare_returns_ranked_results_and_baseline_deltas():
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()
    strategy_payload = _build_eval_payload()
    compare_payload = {
        "resource": strategy_payload["resource"],
        "initial_counters": strategy_payload["initial_counters"],
        "preferences": strategy_payload["preferences"],
        "goals": strategy_payload["goals"],
        "scale": 3,
        "strategies": [
            {
                "id": "candidate_a",
                "label": "candidate_a",
                "banner_plans": strategy_payload["banner_plans"],
            }
        ],
        "baseline_strategy_id": "fixed_draw_cap",
    }

    response = client.post(
        "/api/eval/compare",
        data=json.dumps(compare_payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body is not None
    assert body["baseline_strategy_id"] == "fixed_draw_cap"
    assert len(body["strategies"]) == 2
    ids = {item["strategy_id"] for item in body["strategies"]}
    assert "candidate_a" in ids
    assert "baseline::fixed_draw_cap" in ids
    for item in body["strategies"]:
        assert "rank" in item
        assert "percentile" in item
        assert "score_delta_from_baseline" in item


def test_eval_jobs_reject_workers_exceeding_max():
    """workers 超过服务端上限时返回 400。"""
    from web.app import create_app
    from web.evaluator import MAX_EVAL_WORKERS

    app = create_app(dev_mode=True)
    client = app.test_client()
    payload = _build_eval_payload()
    payload["workers"] = MAX_EVAL_WORKERS + 1

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body is not None
    assert "workers" in body["error"]


def test_eval_jobs_reject_negative_resources():
    """resource 字段出现负数时返回 400。"""
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()
    payload = _build_eval_payload()
    payload["resource"]["chartered_permits"] = -1

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body is not None
    assert "不能为负数" in body["error"]


def test_eval_jobs_reject_negative_counters():
    """counters 字段出现负数时返回 400。"""
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()
    payload = _build_eval_payload()
    payload["initial_counters"]["total"] = -5

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body is not None
    assert "不能为负数" in body["error"]


def test_eval_jobs_reject_invalid_bool_fields():
    """布尔字段传入非布尔值时返回 400。"""
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()
    payload = _build_eval_payload()
    payload["initial_counters"]["guarantee_used"] = "true"  # string, not bool

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body is not None
    assert "布尔字段" in body["error"]


def test_eval_compare_rejects_excessive_strategies():
    """对比接口 strategies 超过上限时返回 400。"""
    from web.app import create_app
    from web.evaluator import MAX_COMPARE_STRATEGIES

    app = create_app(dev_mode=True)
    client = app.test_client()
    strategy_payload = _build_eval_payload()
    compare_payload = {
        "resource": strategy_payload["resource"],
        "initial_counters": strategy_payload["initial_counters"],
        "preferences": strategy_payload["preferences"],
        "goals": strategy_payload["goals"],
        "scale": 3,
        "strategies": [
            {"id": f"strategy_{i}", "label": f"strategy_{i}", "banner_plans": strategy_payload["banner_plans"]}
            for i in range(MAX_COMPARE_STRATEGIES + 1)
        ],
    }

    response = client.post(
        "/api/eval/compare",
        data=json.dumps(compare_payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body is not None
    assert "对比策略数量" in body["error"]


def test_eval_compare_ignores_custom_workers():
    """对比接口不接受自定义 workers，默认 workers 下仍然能正常工作。"""
    from web.app import create_app

    app = create_app(dev_mode=True)
    client = app.test_client()
    strategy_payload = _build_eval_payload()
    compare_payload = {
        "resource": strategy_payload["resource"],
        "initial_counters": strategy_payload["initial_counters"],
        "preferences": strategy_payload["preferences"],
        "goals": strategy_payload["goals"],
        "scale": 3,
        "workers": 9999,  # should be ignored
        "strategies": [
            {
                "id": "candidate_a",
                "label": "candidate_a",
                "banner_plans": strategy_payload["banner_plans"],
            }
        ],
    }

    response = client.post(
        "/api/eval/compare",
        data=json.dumps(compare_payload),
        content_type="application/json",
    )
    # Should still succeed (workers is ignored in compare)
    assert response.status_code == 200
    body = response.get_json()
    assert body is not None
    assert len(body["strategies"]) >= 1


def test_eval_jobs_reject_excessive_scale():
    """scale 超过上限时返回 400。"""
    from web.app import create_app
    from web.evaluator import MAX_EVAL_SCALE

    app = create_app(dev_mode=True)
    client = app.test_client()
    payload = _build_eval_payload()
    payload["scale"] = MAX_EVAL_SCALE + 1

    response = client.post(
        "/api/eval/jobs",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body is not None
    assert "scale" in body["error"]


def test_evaluation_job_manager_rejects_when_queue_full():
    """任务队列满时 submit 应抛出异常。"""
    import threading
    import time

    from web.eval_jobs import EvaluationJobManager

    hold_event = threading.Event()

    def slow_task(payload):
        hold_event.wait(timeout=10)
        return {"value": payload["value"]}

    # 2 workers, max_queue_size=3 → capacity = 2 (running) + 3 (pending) = 5
    manager = EvaluationJobManager(worker_count=2, evaluator=slow_task, max_queue_size=3)
    try:
        for i in range(2):
            manager.submit({"value": i})
            time.sleep(0.05)  # let workers pick up

        for i in range(3):
            manager.submit({"value": i + 2})

        # 6th submit should be rejected (pending queue full)
        queue_full = False
        try:
            manager.submit({"value": 99})
        except ValueError as exc:
            queue_full = True
            assert "队列已满" in str(exc)
        assert queue_full, "队列满时应抛出 ValueError"
    finally:
        hold_event.set()
        time.sleep(0.2)
        manager.shutdown(wait=True)


def test_evaluation_job_manager_limits_parallel_jobs_and_queues_extra_work():
    from web.eval_jobs import EvaluationJobManager

    def slow_task(payload):
        time.sleep(payload["sleep"])
        return {"value": payload["value"]}

    manager = EvaluationJobManager(worker_count=2, evaluator=slow_task)
    try:
        job_ids = [
            manager.submit({"sleep": 0.2, "value": index})
            for index in range(3)
        ]
        time.sleep(0.05)

        statuses = [manager.get_job(job_id)["status"] for job_id in job_ids]
        assert statuses.count("running") == 2
        assert statuses.count("queued") == 1

        deadline = time.time() + 2.0
        while time.time() < deadline:
            if all(manager.get_job(job_id)["status"] == "succeeded" for job_id in job_ids):
                break
            time.sleep(0.05)

        assert all(manager.get_job(job_id)["status"] == "succeeded" for job_id in job_ids)
        assert manager.get_job(job_ids[2])["result"] == {"value": 2}
    finally:
        manager.shutdown(wait=True)
