import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from signals.signal1_semantic import get_semantic_score

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
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


@app.route("/api/submit", methods=["POST"])
@limiter.limit("5 per minute")
def submit():
    data = request.get_json(silent=True)
    if not data or "creator_id" not in data or "text" not in data:
        return jsonify({"error": "Request must include creator_id and text"}), 400

    text = data["text"]

    try:
        signal1_score = get_semantic_score(text)
    except Exception as e:
        return jsonify({"error": f"Signal 1 failed: {str(e)}"}), 500

    # Signal 2 not yet wired — using signal1 score as the full confidence for now
    confidence = round(signal1_score, 4)

    if confidence <= 0.35:
        verdict = "high_confidence_human"
        label = (
            "Verified Human Creator: Our automated system has analyzed the content's "
            "structure, semantics and stylistics pattern and are highly confident that "
            "this was written entirely by a human."
        )
    elif confidence <= 0.74:
        verdict = "uncertain"
        label = (
            "Uncertain Attribution: Our automated system has analyzed given text but is "
            "unable to confidently say that this is human-written due to mixed signals. "
            "We are improving our systems in this regard, thank you for your patience!"
        )
    else:
        verdict = "high_confidence_ai"
        label = (
            "AI-generated Content: This uploaded text was analyzed by our system and we "
            "have detected AI written structure and semantics. If you are the creator and "
            "believe this classification is a mistake, you can submit your appeal and it "
            "will be reviewed by our moderators."
        )

    submission_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    write_audit_entry({
        "submission_id": submission_id,
        "creator_id": data["creator_id"],
        "timestamp": timestamp,
        "attribution": verdict,
        "confidence": confidence,
        "llm_score": signal1_score,
        "status": "classified"
    })

    return jsonify({
        "submission_id": submission_id,
        "attribution": verdict,
        "confidence": confidence,
        "label": label
    }), 200


@app.route("/api/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log()}), 200


if __name__ == "__main__":
    app.run(debug=True)
