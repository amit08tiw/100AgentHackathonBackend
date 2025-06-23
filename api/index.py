# api/index.py

import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai._exceptions import RateLimitError, OpenAIError

# ————————————————
# 1) Create the Flask app
# ————————————————
app = Flask(__name__)
CORS(app)

# ————————————————
# 2) Read & validate your env-vars
# ————————————————
OPENROUTER_KEY = "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"
TAVILY_KEY     = "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"

if not OPENROUTER_KEY or not TAVILY_KEY:
    raise RuntimeError(
        "Missing one of OPENROUTER_API_KEY or TAVILY_API_KEY in environment"
    )
# meta-llama/llama-4-maverick:free
# ————————————————
# 3) Constants & prompt builder
# ————————————————
BASE_URL = "https://openrouter.ai/api/v1"
MODEL_MAP = {
    "llama":   "meta-llama/llama-4-maverick:free",
    "mistral": "mistralai/mistral-small-3.1-24b-instruct:free",
}

def build_prompt(mode: str, effect: str) -> str:
    prompts = {
        "molecule-design":     f"Design a synthetic molecule that helps with: {effect}. Describe its structure, effect, and usage.",
        "toxicity-report":     f"Generate a toxicity profile for a synthetic molecule intended to: {effect}. Include risks, side effects, and safety thresholds.",
        "regulatory-readiness": f"What are the regulatory approval steps for a molecule targeting: {effect}? Include FDA and EMA requirements.",
        "comparison":          f"Compare two molecule strategies to achieve the effect: {effect}. Include structure, efficiency, and risk.",
        "version-history":     f"Show a version history of improvements for synthetic molecules developed to address: {effect}.",
    }
    return prompts.get(mode, prompts["molecule-design"])

# ————————————————
# 4) /generate endpoint
# ————————————————
@app.route("/generate", methods=["POST"])
def generate_response():
    data = request.get_json(silent=True) or {}
    effect = (data.get("effect") or "").strip()
    mode = data.get("mode", "molecule-design")

    if not effect:
        return jsonify({"error": "Missing effect input"}), 400

    prompt = build_prompt(mode, effect)
    model_url = "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct"

    headers = {
        "Content-Type": "application/json",
        # For public inference models, no key needed. But if you want more speed or quota, you can set "Authorization": f"Bearer {HUGGINGFACE_KEY}"
    }

    body = {
        "inputs": prompt
    }

    try:
        res = requests.post(model_url, headers=headers, json=body)
        res.raise_for_status()
        result = res.json()

        # Hugging Face returns a list of dicts
        output = result[0].get("generated_text", "").strip()
        return jsonify({"result": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ————————————————
# 5) /search-evidence endpoint
# ————————————————
@app.route("/search-evidence", methods=["POST"])
def search_evidence():
    data  = request.get_json(silent=True) or {}
    query = (data.get("effect") or "").strip()

    if not query:
        return jsonify({"error": "No effect provided"}), 400

    try:
        res = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {TAVILY_KEY}"},
            json={
                "query":        f"{query} synthetic molecule biomedical research",
                "search_depth": "advanced"
            }
        )
        res.raise_for_status()
        return jsonify({"evidence": res.json().get("results", [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ————————————————
# 6) Optional health check
# ————————————————
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 200
