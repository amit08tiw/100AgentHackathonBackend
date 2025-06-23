import os
import requests
from flask import Flask, request, jsonify
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

# === API Keys (replace with your secrets or set as Vercel env vars) ===
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY") or "578f49f0c591a12db071147ae6298c632b5f4388bdaf36704cfe2d59d150e7ec"
TAVILY_KEY = os.getenv("TAVILY_KEY") or "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"

if not TOGETHER_API_KEY or not TAVILY_KEY:
    raise RuntimeError("Missing TOGETHER_API_KEY or TAVILY_KEY")

# === Model Mapping ===
MODEL_MAP = {
    "llama": "meta-llama/Llama-3-8B-Instruct",
    "mistral": "mistralai/Mistral-7B-Instruct-v0.1",
}

# === Prompt Template ===
def build_prompt(mode: str, effect: str) -> str:
    return {
        "molecule-design":     f"Design a synthetic molecule that helps with: {effect}. Describe its structure, effect, and usage.",
        "toxicity-report":     f"Generate a toxicity profile for a synthetic molecule intended to: {effect}. Include risks, side effects, and safety thresholds.",
        "regulatory-readiness": f"What are the regulatory approval steps for a molecule targeting: {effect}? Include FDA and EMA requirements.",
        "comparison":          f"Compare two molecule strategies to achieve the effect: {effect}. Include structure, efficiency, and risk.",
        "version-history":     f"Show a version history of improvements for synthetic molecules developed to address: {effect}.",
    }.get(mode, f"Design a synthetic molecule that helps with: {effect}.")

# === /generate (Together AI) ===
@app.route("/generate", methods=["POST", "OPTIONS"])
def generate_response():
    if request.method == "OPTIONS":
        return "", 200  # CORS preflight response

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
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0.7
    }

    try:
        res = requests.post("https://api.together.xyz/inference", headers=headers, json=body, timeout=30)
        res.raise_for_status()
        result = res.json().get("output", "").strip()
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === /search-evidence (Tavily Search) ===
@app.route("/search-evidence", methods=["POST", "OPTIONS"])
def search_evidence():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True) or {}
    query = (data.get("effect") or "").strip()

    if not query:
        return jsonify({"error": "Missing effect"}), 400

    try:
        res = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {TAVILY_KEY}"},
            json={
                "query": f"{query} synthetic molecule biomedical research",
                "search_depth": "advanced"
            },
            timeout=20
        )
        res.raise_for_status()
        return jsonify({"evidence": res.json().get("results", [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Health Check ===
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 200
