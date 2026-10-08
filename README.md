# Hallucination Showdown

Type one question and see two answers side by side:

- **Guessing Agent**: its system prompt encourages a confident answer and a plausible guess when it lacks information.
- **Cautious Agent**: its system prompt encourages separating supported information from uncertainty and saying "I don't know" when appropriate.

Both agents receive the **exact same question** and use the **same OpenRouter model**. They are two prompt configurations of one model, not two separately trained models. **Neither answer is fact-checked or independently verified.**

> ## ⚠️ Cost notice
> **Each comparison makes TWO model requests** to OpenRouter and may use credits on your account. Check pricing before heavy use.

This version has no evidence search or verification. That is planned for a later version.

## Project layout

```
app.py              Flask backend (prompts, OpenRouter calls, /api/compare)
templates/index.html  Page markup
static/style.css    Responsive styling
static/app.js       Frontend logic (safe DOM rendering via textContent)
requirements.txt    Python dependencies
.env.example        Template for your private settings
.gitignore          Keeps .env and virtualenvs out of Git
Procfile            Production start command (gunicorn)
```

## Run locally (Windows PowerShell)

1. **Open PowerShell** in the project folder (the one containing `app.py`).

2. **Create a virtual environment:**
   ```powershell
   py -m venv .venv
   ```

3. **Activate it:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell says scripts are disabled, run this once and try again:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```
   Your prompt should now start with `(.venv)`.

4. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

5. **Create your `.env` file:**
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```
   Replace `your-openrouter-api-key-here` with your own key from <https://openrouter.ai/keys>, save, and close. Optionally change `OPENROUTER_MODEL`.

6. **Start the app:**
   ```powershell
   python app.py
   ```

7. **Open it** in your browser at <http://127.0.0.1:5000>.

Press `Ctrl+C` in PowerShell to stop the server. If you edit `.env`, restart the app.

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter key. Stays on the server and is never sent to the browser. |
| `OPENROUTER_MODEL` | No | Model ID used for both agents. Default: `meta-llama/llama-3.2-3b-instruct`. |
| `APP_URL` | No | Your app's public URL, sent to OpenRouter as the `HTTP-Referer` header. |

**Check the model catalog:** model IDs, availability and pricing can change. Before using or switching models, confirm the ID and current pricing in the [OpenRouter model catalog](https://openrouter.ai/models).

## Deploying

The app is ready for any host that runs a `Procfile` (Render, Railway, Heroku, Fly.io and similar). The start command is:

```
gunicorn app:app --workers 2 --threads 4 --timeout 90 --bind 0.0.0.0:${PORT:-8000}
```

General steps:

1. Push the project to a Git repository. Confirm `.env` is **not** included (it is in `.gitignore`).
2. Create a new web service on your host and connect the repository.
3. Build command: `pip install -r requirements.txt`. Start command: use the `Procfile` (or paste the gunicorn line above).
4. **Set the API key as a private environment variable** in your host's dashboard, usually under *Environment*, *Variables* or *Secrets*. Add:
   - `OPENROUTER_API_KEY` = your real key (mark it secret/private)
   - `OPENROUTER_MODEL` = your chosen model ID (optional)
   - `APP_URL` = your deployed URL (optional)
5. Deploy and open the URL the host gives you.

Do not put your key in code, in `.env.example`, or in any file you commit. Gunicorn runs on Linux hosts; for local use on Windows, use `python app.py` as above.

**Note:** anyone who can open a public deployment can trigger requests that use your OpenRouter credits. Consider setting a spending limit on your OpenRouter account, and adding authentication or rate limiting before sharing the link widely.

## Safety and behavior notes

- Questions are validated server-side: they cannot be empty and are limited to 500 characters.
- Both requests run concurrently and each has a timeout. If one agent fails, the other answer is still shown.
- Errors shown to users are friendly summaries; secrets and raw upstream responses are never shown.
- Model output is displayed as plain text (`textContent`), never as HTML.
