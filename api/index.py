import os
import requests
from flask import Flask, request, jsonify
from flask import make_response
from flask_cors import CORS

# === Initialize Flask App & CORS ===
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.after_request
def after_request(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp

# === API Keys ===
TOGETHER_API_KEY = "578f49f0c591a12db071147ae6298c632b5f4388bdaf36704cfe2d59d150e7ec"
TAVILY_KEY = "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"
if not TOGETHER_API_KEY or not TAVILY_KEY:
    raise RuntimeError("Missing TOGETHER_API_KEY or TAVILY_API_KEY")

# === Model Mapping ===
MODEL_MAP = {
    "llama": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "mistral": "mistralai/Mistral-7B-Instruct-v0.1",
}

# === Prompt Builder ===
def build_prompt(mode: str, effect: str) -> str:
    return {
        "molecule-design":     f"Design a synthetic molecule that helps with: {effect}. Describe its structure, effect, and usage.",
        "toxicity-report":     f"Generate a toxicity profile for a synthetic molecule intended to: {effect}. Include risks, side effects, and safety thresholds.",
        "regulatory-readiness": f"What are the regulatory approval steps for a molecule targeting: {effect}? Include FDA and EMA requirements.",
        "comparison":          f"Compare two molecule strategies to achieve the effect: {effect}. Include structure, efficiency, and risk.",
        "patents":             f"Create a sample patent documents for the effect: {effect}. Provide sample title and other sample details that can be included as probable patentable documents .",
        "version-history":     f"Show a version history of improvements for synthetic molecules developed to address: {effect}.",
        "sketch":              f"Generate an SVG sketch of a synthetic molecule for the biological effect: {effect}. Return only the SVG code."
    }.get(mode, "Describe a molecule that helps with: " + effect)

# === /generate endpoint ===
@app.route("/generate", methods=["POST", "OPTIONS"])
def generate_response():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True) or {}
    effect = (data.get("effect") or "").strip()
    model_key = data.get("model", "llama")
    mode = data.get("mode", "molecule-design")

    if not effect:
        return jsonify({"error": "Missing effect input"}), 400

    model = MODEL_MAP.get(model_key, MODEL_MAP["llama"])
    prompt = build_prompt(mode, effect)

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024 if mode == "sketch" else 512
    }

    try:
        r = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=body, timeout=30)
        r.raise_for_status()
        result = r.json().get("choices", [])[0]["message"]["content"]
        return jsonify({"result": result.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === /search-evidence endpoint ===
@app.route("/search-evidence", methods=["POST", "OPTIONS"])
def search_evidence():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True) or {}
    query = (data.get("effect") or "").strip()

    if not query:
        return jsonify({"error": "Missing effect"}), 400

    try:
        r = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {TAVILY_KEY}"},
            json={"query": f"{query} synthetic molecule biomedical research", "search_depth": "advanced"},
            timeout=20
        )
        r.raise_for_status()
        return jsonify({"evidence": r.json().get("results", [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Health check ===
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})
