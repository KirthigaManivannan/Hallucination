"""Hallucination Showdown: one question, two prompt configurations of ONE model.

The Guessing Agent and the Cautious Agent use the exact same OpenRouter model
and receive the exact same question. Only the system prompt differs.
Nothing here fact-checks or verifies either answer.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

# Read variables from a local .env file (if present). Real environment
# variables (e.g. on a hosting platform) are used as-is.
load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.2-3b-instruct"

MAX_QUESTION_LENGTH = 500
MAX_OUTPUT_TOKENS = 300
TEMPERATURE = 0.7
# (connect timeout, read timeout) in seconds
REQUEST_TIMEOUT = (5, 45)

GUESSING_PROMPT = (
    "You are the Guessing Agent. Always answer the user's question directly "
    "and confidently. If you do not have enough information, make your best "
    "plausible guess and present it as a clear answer. Do not say that you "
    "don't know and do not refuse. Keep your answer under 150 words."
)

CAUTIOUS_PROMPT = (
    "You are the Cautious Agent. Answer the user's question carefully. "
    "Clearly separate what you have good reason to believe is true from "
    "anything you are unsure about. If you do not know, or the question "
    "seems to rely on something you cannot confirm, say so plainly instead "
    "of guessing. Never invent facts, names, numbers, quotes or sources. "
    "Keep your answer under 150 words."
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("hallucination-showdown")


def get_config():
    """Read settings at request time so .env changes are picked up on restart."""
    return {
        "api_key": (os.environ.get("OPENROUTER_API_KEY") or "").strip(),
        "model": (os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL).strip(),
        "app_url": (os.environ.get("APP_URL") or "").strip(),
    }


def ask_model(system_prompt, question, config):
    """Send one request to OpenRouter.

    Always returns a dict: {"ok": True, "answer": str} or
    {"ok": False, "error": str}. Error messages are safe to show to users
    (they never include the API key or raw upstream responses).
    """
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "X-Title": "Hallucination Showdown",
    }
    if config["app_url"]:
        headers["HTTP-Referer"] = config["app_url"]

    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }

    try:
        resp = requests.post(
            OPENROUTER_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "The model took too long to respond. Please try again."}
    except requests.exceptions.RequestException:
        log.warning("Network error while contacting OpenRouter")
        return {"ok": False, "error": "Could not reach OpenRouter. Check your connection and try again."}

    if resp.status_code != 200:
        log.warning("OpenRouter returned HTTP %s", resp.status_code)
        messages = {
            400: "OpenRouter rejected the request. The model ID may be wrong or unavailable.",
            401: "OpenRouter rejected the API key. Check OPENROUTER_API_KEY on the server.",
            402: "Your OpenRouter account may be out of credits.",
            403: "OpenRouter refused this request (access or moderation).",
            404: "The configured model was not found. Check OPENROUTER_MODEL.",
            408: "OpenRouter timed out. Please try again.",
            429: "Rate limit reached. Please wait a moment and try again.",
        }
        if resp.status_code in messages:
            msg = messages[resp.status_code]
        elif resp.status_code >= 500:
            msg = "OpenRouter or the model provider had a problem. Please try again shortly."
        else:
            msg = f"Unexpected response from OpenRouter (HTTP {resp.status_code})."
        return {"ok": False, "error": msg}

    try:
        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        log.warning("Unexpected response format from OpenRouter")
        return {"ok": False, "error": "Received a response in an unexpected format."}

    if not isinstance(answer, str) or not answer.strip():
        return {"ok": False, "error": "The model returned an empty answer."}

    return {"ok": True, "answer": answer.strip()}


@app.route("/")
def index():
    config = get_config()
    return render_template(
        "index.html",
        model=config["model"],
        max_length=MAX_QUESTION_LENGTH,
    )


@app.route("/api/compare", methods=["POST"])
def compare():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Invalid request. Please send a JSON body."}), 400

    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "Please enter a question."}), 400
    question = question.strip()
    if len(question) > MAX_QUESTION_LENGTH:
        return jsonify(
            {"error": f"Question is too long. Please keep it under {MAX_QUESTION_LENGTH} characters."}
        ), 400

    config = get_config()
    if not config["api_key"]:
        log.error("OPENROUTER_API_KEY is not set")
        return jsonify(
            {"error": "The server is not configured yet: the OpenRouter API key is missing."}
        ), 500

    # Same question, same model, two different system prompts, sent concurrently.
    with ThreadPoolExecutor(max_workers=2) as pool:
        guessing_future = pool.submit(ask_model, GUESSING_PROMPT, question, config)
        cautious_future = pool.submit(ask_model, CAUTIOUS_PROMPT, question, config)
        guessing = guessing_future.result()
        cautious = cautious_future.result()

    return jsonify(
        {
            "model": config["model"],
            "question": question,
            "guessing": guessing,
            "cautious": cautious,
        }
    )


if __name__ == "__main__":
    # Local development server only. In production, gunicorn runs `app`.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
