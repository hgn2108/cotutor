# Deploying Cotutor (free)

| Piece | Host | Cost |
|---|---|---|
| Backend (FastAPI, agents) | Hugging Face Space, Docker SDK, free CPU | Free (sleeps after ~48h idle, wakes on first visit) |
| Frontend (React) | Vercel Hobby | Free |
| LLM | Gemini API free tier | Free, rate-limited |

Code execution happens in visitors' browsers, so the backend needs no GPU and never runs untrusted code.

## 1. Backend on Hugging Face

1. Create a **Space**: https://huggingface.co/new-space
   - Name: `cotutor-api` · SDK: **Docker** (Blank) · Hardware: **CPU basic (free)** · Public.
2. In the Space → **Settings → Variables and secrets**, add:
   - Secret `GEMINI_API_KEY`: a key reserved for the public demo (a separate Google AI Studio project from your personal key).
   - Variable `COTUTOR_ALLOWED_ORIGINS`: your Vercel URL, e.g. `https://cotutor.vercel.app`.
   - Variable `COTUTOR_ALLOWED_ORIGIN_REGEX` (optional, for preview deployments): `^https://cotutor(-[a-z0-9-]+)?\.vercel\.app$`.
3. Create a Hugging Face **access token** with *write* access: https://huggingface.co/settings/tokens
4. Let GitHub deploy for you. In the GitHub repo:
   ```bash
   gh secret set HF_TOKEN                          # paste the token when prompted
   gh variable set HF_SPACE --body "<hf-username>/cotutor-api"
   gh workflow run "Deploy backend"
   ```
   Every push to `main` that touches `backend/` redeploys the Space.
5. Check `https://<hf-username>-cotutor-api.hf.space/api/health`.

## 2. Frontend on Vercel

1. https://vercel.com/new → import `hgn2108/cotutor`.
2. **Root Directory**: `web` (framework preset: Vite, detected automatically).
3. Environment variable `VITE_API_URL` = `https://<hf-username>-cotutor-api.hf.space`.
4. Deploy. Every push to `main` redeploys; pull requests get preview URLs.

## 3. Wire them together

Put the final Vercel URL into the Space's `COTUTOR_ALLOWED_ORIGINS` (step 1.2) and restart the Space.
The backend only accepts WebSocket connections from these origins, so other sites can't spend the demo's quota.

## Operating notes

- Library problems replay from recorded runs and cost nothing. New problems use the shared key, limited per IP
  (`COTUTOR_RUNS_PER_HOUR`, default 20); visitors can add their own free key in Settings.
- The Space's disk is ephemeral: runs cached at runtime disappear on restart; the recorded library does not.
