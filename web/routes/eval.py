# -*- coding: utf-8 -*-
"""Evaluation routes and APIs."""

from __future__ import annotations

from multiprocessing import cpu_count

from flask import jsonify, render_template, request

from ..eval_jobs import EvaluationJobManager
from ..evaluator import (
    MAX_PARALLEL_EVALS,
    evaluate_compare_payload,
    evaluate_payload,
    list_eval_configs,
    validate_compare_payload,
    validate_eval_payload,
)

DEFAULT_WORKERS = max(1, cpu_count() // MAX_PARALLEL_EVALS)
_JOB_MANAGER: EvaluationJobManager | None = None


def get_job_manager() -> EvaluationJobManager:
    global _JOB_MANAGER
    if _JOB_MANAGER is None:
        _JOB_MANAGER = EvaluationJobManager(
            worker_count=MAX_PARALLEL_EVALS,
            evaluator=lambda payload: evaluate_payload(payload, default_workers=DEFAULT_WORKERS),
        )
    return _JOB_MANAGER


def register_routes(app):
    @app.route("/eval")
    def eval_page():
        return render_template("eval.html")

    @app.route("/api/eval/configs", methods=["GET"])
    def eval_configs():
        return jsonify({"configs": list_eval_configs()})

    @app.route("/api/eval/jobs", methods=["POST"])
    def create_eval_job():
        data = request.get_json(silent=True)
        try:
            normalized = validate_eval_payload(data)
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

        job_manager = get_job_manager()
        try:
            job_id = job_manager.submit(normalized)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 429
        snapshot = job_manager.get_job(job_id)
        return jsonify(snapshot), 202

    @app.route("/api/eval/compare", methods=["POST"])
    def compare_eval_strategies():
        data = request.get_json(silent=True)
        try:
            normalized = validate_compare_payload(data)
            result = evaluate_compare_payload(normalized, default_workers=DEFAULT_WORKERS)
        except (TypeError, ValueError) as exc:
            message = str(exc)
            status_code = 409 if message.startswith("EVAL_QUESTIONNAIRE_INCONSISTENT:") else 400
            return jsonify({"error": message}), status_code
        return jsonify(result), 200

    @app.route("/api/eval/jobs/<job_id>", methods=["GET"])
    def eval_job_status(job_id: str):
        snapshot = get_job_manager().get_job(job_id)
        if snapshot is None:
            return jsonify({"error": "job not found"}), 404
        return jsonify(snapshot)
