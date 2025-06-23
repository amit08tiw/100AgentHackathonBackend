# api/index.py

import os
import requests
import serverless_wsgi
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai._exceptions import RateLimitError, OpenAIError

# === Initialize Flask App ===
app = Flask(__name__)
CORS(app)

# === Environment Variables ===
# On Vercel, set these in the Dashboard under Settings → Environment Variables
# os.environ["OPENROUTER_API_KEY"] = "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"
# os.environ["TAVILY_API_KEY"] = "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"
OPENROUTER_KEY = "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"
TAVILY_KEY     = "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"

BASE_URL = "https://openrouter.ai/api/v1"
MODEL_MAP = {
    "llama":   "meta-llama/llama-4-maverick:free",
    "mistral": "mistralai/mistral-small-3.1-24b-instruct:free",
}

# === Prompt Generator ===
def build_prompt(mode: str, effect: str) -> str:
    prompts = {
        "molecule-design":     f"Design a synthetic molecule that helps with: {effect}. Describe its structure, effect, and usage.",
        "toxicity-report":     f"Generate a toxicity profile for a synthetic molecule intended to: {effect}. Include risks, side effects, and safety thresholds.",
        "regulatory-readiness": f"What are the regulatory approval steps for a molecule targeting: {effect}? Include FDA and EMA requirements.",
        "comparison":          f"Compare two molecule strategies to achieve the effect: {effect}. Include structure, efficiency, and risk.",
        "version-history":     f"Show a version history of improvements for synthetic molecules developed to address: {effect}."
    }
    return prompts.get(mode, prompts["molecule-design"])

# === /generate Route ===
@app.route("/generate", methods=["POST"])
def generate_response():
    data      = request.get_json(silent=True) or {}
    effect    = (data.get("effect") or "").strip()
    model_key = data.get("model", "llama")
    mode      = data.get("mode", "molecule-design")

    if not effect:
        return jsonify({"error": "Missing effect input"}), 400

    model  = MODEL_MAP.get(model_key, MODEL_MAP["llama"])
    prompt = build_prompt(mode, effect)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://<your-vercel-app>.vercel.app",
        "X-Title":       "AgentNet BioForge"
    }
    body = {
        "model":       model,
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        res = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=body)
        res.raise_for_status()
        choices = res.json().get("choices", [])
        message = ""
        if choices:
            message = choices[0].get("message", {}).get("content", "").strip()
        if not message:
            raise ValueError("LLM responded but returned empty content")
        return jsonify({"result": message})
    except (RateLimitError, OpenAIError) as e:
        return jsonify({"error": f"LLM API error: {e}"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === /search-evidence Route ===
@app.route("/search-evidence", methods=["POST"])
def search_evidence():
    data  = request.get_json(silent=True) or {}
    query = (data.get("effect") or "").strip()
    if not query:
        return jsonify({"error": "No effect provided"}), 400

    tavily_url = "https://api.tavily.com/search"
    headers    = {"Authorization": f"Bearer {TAVILY_KEY}"}
    payload    = {
        "query":        f"{query} synthetic molecule biomedical research",
        "search_depth": "advanced"
    }

    try:
        res = requests.post(tavily_url, headers=headers, json=payload)
        res.raise_for_status()
        results = res.json().get("results", [])
        return jsonify({"evidence": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Vercel Serverless Handler ===
def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
