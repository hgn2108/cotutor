# Deploying Cotutor (free)

| Piece | Host | Cost |
|---|---|---|
| Backend (FastAPI, agents) | Render free web service, Docker, via [`render.yaml`](../render.yaml) | Free, no card (sleeps after 15 min idle, ~1 min to wake) |
| Frontend (React) | Vercel Hobby | Free |
| LLM | Gemini API free tier | Free, rate-limited |

Code execution happens in visitors' browsers, so the backend needs no GPU and never runs untrusted code.
The frontend shows "Waking up server…" and retries while a sleeping backend starts.

## 1. Backend on Render

1. Sign up at https://dashboard.render.com/register with **GitHub** (no credit card needed).
2. **New → Blueprint** → connect `hgn2108/cotutor` → Render reads `render.yaml` and proposes the `cotutor-api` service.
3. Fill in the two secrets it asks for:
   - `GEMINI_API_KEY`: a key reserved for the public demo (a separate Google AI Studio project from your personal key).
   - `COTUTOR_ALLOWED_ORIGINS`: your Vercel URL, e.g. `https://cotutor.vercel.app` (use `http://localhost:5173` until you have it).
4. **Apply**. The first build takes a few minutes. Then check `https://cotutor-api.onrender.com/api/health` (Render shows the exact URL).

Every push to `main` that changes `backend/` redeploys automatically.

## 2. Frontend on Vercel

1. https://vercel.com/new → import `hgn2108/cotutor`.
2. **Root Directory**: `web` (framework preset Vite is detected).
3. Environment variable `VITE_API_URL` = your Render URL, e.g. `https://cotutor-api.onrender.com`.
4. Deploy. Every push to `main` redeploys; pull requests get preview URLs.

## 3. Wire them together

Set `COTUTOR_ALLOWED_ORIGINS` on Render to the final Vercel URL (Environment tab, then save; Render restarts).
The backend only accepts WebSocket connections from these origins, so other sites can't spend the demo's quota.

## Operating notes

- Library and roadmap lessons that are recorded replay instantly and cost nothing. New problems use the shared key,
  limited per IP (`COTUTOR_RUNS_PER_HOUR`, default 20); visitors can add their own free key in Settings.
- Free instances have ephemeral disks: runs cached at runtime disappear on restart; recorded lessons ship with the image.
- Render gives 750 free instance hours per month, enough for one always-available service.
