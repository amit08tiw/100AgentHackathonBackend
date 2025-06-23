import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai._exceptions import RateLimitError, OpenAIError

app = Flask(__name__)
CORS(app)

# Read from Vercel env variables
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

MODEL_MAP = {
    "llama": "meta-llama/llama-4-maverick:free",
    "mistral": "mistralai/mistral-small-3.1-24b-instruct:free"
}

@app.route('/generate', methods=['POST'])
def generate_response():
    try:
        data = request.json
        effect = data.get("effect")
        model_key = data.get("model", "llama")
        mode = data.get("mode", "molecule-design")

        if not effect:
            return jsonify({"error": "Missing effect input"}), 400

        model = MODEL_MAP.get(model_key, MODEL_MAP["llama"])
        prompt = build_prompt(mode, effect)

        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "HTTP-Referer": "https://your-frontend-domain.com",
            "X-Title": "AgentNet BioForge"
        }

        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }

        res = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=body)
        res.raise_for_status()
        result = res.json()

        message = (
            result.get("choices", [{}])[0]
                  .get("message", {})
                  .get("content", "")
                  .strip()
        )

        if not message:
            return jsonify({"error": "LLM responded but gave no usable content."}), 500

        return jsonify({"result": message})

    except (RateLimitError, OpenAIError) as api_err:
        return jsonify({"error": f"LLM API error: {str(api_err)}"}), 503
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@app.route('/search-evidence', methods=['POST'])
def search_evidence():
    query = request.json.get('effect', '')
    if not query:
        return jsonify({"error": "No effect provided"}), 400

    headers = {"Authorization": f"Bearer {TAVILY_KEY}"}
    payload = {
        "query": f"{query} synthetic molecule biomedical research",
        "search_depth": "advanced"
    }

    try:
        res = requests.post("https://api.tavily.com/search", headers=headers, json=payload)
        res.raise_for_status()
        return jsonify({"evidence": res.json().get("results", [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def build_prompt(mode: str, effect: str) -> str:
    prompts = {
        "molecule-design": f"Design a synthetic molecule that helps with: {effect}. Describe its structure, effect, and usage.",
        "toxicity-report": f"Generate a toxicity profile for a synthetic molecule intended to: {effect}. Include risks, side effects, and safety thresholds.",
        "regulatory-readiness": f"What are the regulatory approval steps for a molecule targeting: {effect}? Include FDA and EMA requirements.",
        "comparison": f"Compare two molecule strategies to achieve the effect: {effect}. Include structure, efficiency, and risk.",
        "version-history": f"Show a version history of improvements for synthetic molecules developed to address: {effect}."
    }
    return prompts.get(mode, prompts["molecule-design"])
