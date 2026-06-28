import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from signals.signal1_semantic import get_semantic_score
from signals.signal2_stylometric import get_stylometric_score
from scoring import combine_scores, get_verdict

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

AUDIT_LOG = Path(__file__).parent / "audit_log.json"


def write_audit_entry(entry: dict):
    if AUDIT_LOG.exists():
        with open(AUDIT_LOG, "r") as f:
            log = json.load(f)
    else:
        log = []
    log.append(entry)
    with open(AUDIT_LOG, "w") as f:
        json.dump(log, f, indent=2)


def get_log() -> list:
    if not AUDIT_LOG.exists():
        return []
    with open(AUDIT_LOG, "r") as f:
        return json.load(f)


def update_audit_entry(submission_id: str, updates: dict) -> bool:
    log = get_log()
    for entry in log:
        if entry.get("submission_id") == submission_id:
            entry.update(updates)
            with open(AUDIT_LOG, "w") as f:
                json.dump(log, f, indent=2)
            return True
    return False


@app.route("/api/submit", methods=["POST"])
@limiter.limit("5 per minute;50 per day")
def submit():
    data = request.get_json(silent=True)
    if not data or "creator_id" not in data or "text" not in data:
        return jsonify({"error": "Request must include creator_id and text"}), 400

    text = data["text"]

    try:
        signal1_score = get_semantic_score(text)
    except Exception as e:
        return jsonify({"error": f"Signal 1 failed: {str(e)}"}), 500

    signal2_score = get_stylometric_score(text)
    confidence = combine_scores(signal1_score, signal2_score)
    verdict, label = get_verdict(confidence)

    submission_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    write_audit_entry({
        "submission_id": submission_id,
        "creator_id": data["creator_id"],
        "timestamp": timestamp,
        "attribution": verdict,
        "confidence": confidence,
        "llm_score": signal1_score,
        "stylometric_score": signal2_score,
        "status": "classified"
    })

    return jsonify({
        "submission_id": submission_id,
        "attribution": verdict,
        "confidence": confidence,
        "label": label
    }), 200


@app.route("/api/appeal", methods=["POST"])
@limiter.limit("3 per minute")
def appeal():
    data = request.get_json(silent=True)
    if not data or "submission_id" not in data or "creator_id" not in data or "creator_reasoning" not in data:
        return jsonify({"error": "Request must include submission_id, creator_id, and creator_reasoning"}), 400

    if not data["creator_reasoning"].strip():
        return jsonify({"error": "creator_reasoning cannot be empty"}), 400

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    updated = update_audit_entry(data["submission_id"], {
        "status": "under_review",
        "appeal": {
            "creator_id": data["creator_id"],
            "creator_reasoning": data["creator_reasoning"],
            "appeal_timestamp": timestamp
        }
    })

    if not updated:
        return jsonify({"error": f"submission_id not found: {data['submission_id']}"}), 404

    return jsonify({
        "status": "success",
        "message": "Appeal successfully logged. Content status updated to under review.",
        "submission_id": data["submission_id"]
    }), 200


@app.route("/api/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log()}), 200


if __name__ == "__main__":
    app.run(debug=True)
