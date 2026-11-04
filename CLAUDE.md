# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local daemon that lets Stream Deck buttons control Spotify without the official plugin. The README (Spanish) has full setup instructions; the notes below cover what's needed to work on the code.

```
Stream Deck button → thin script (next.py, play.py, ...) → daemon.py (FastAPI, 127.0.0.1:5111) → Spotify Web API (spotipy)
```

## Commands

```bash
pip install -r requirements.txt     # fastapi, uvicorn, spotipy, python-dotenv, requests
cp .env.example .env                # then fill SPOTIFY_CLIENT_ID/SECRET and DAEMON_TOKEN
python run.py --login               # first time only: opens browser for Spotify OAuth
python run.py                       # normal start; never opens a browser, exits 1 if no valid cached token
curl http://127.0.0.1:5111/health   # unauthenticated health check
```

There are no tests or linter configured.

## Architecture

- `daemon.py` — FastAPI app. Every endpoint except `/health` is guarded by the `verify_token` dependency (`X-Daemon-Token` header must equal `DAEMON_TOKEN` from `.env`). The module raises at import if `DAEMON_TOKEN` is missing. Each action handler follows the same pattern: get the client, call spotipy, map `SpotifyException` 404 → HTTP 409 "no active device", other errors → 502.
- `spotify_auth.py` — the only place that builds the `SpotifyOAuth` manager and touches the token cache (`.spotify_token_cache`). `ensure_authenticated(login)` runs once from `run.py` before uvicorn starts and creates the single module-level spotipy client; `get_spotify_client()` just returns it (raises `AuthError` if not initialized). Only `login=True` may open a browser.
- `run.py` — entry point: configures logging, calls `ensure_authenticated(login=args.login)` (exits 1 on `AuthError`), then launches uvicorn with `host="127.0.0.1"`. Use this instead of invoking uvicorn directly, otherwise the client is never initialized.
- Logging — `run.py` builds the uvicorn log config plus a rotating `daemon.log` (gitignored); the `daemon` logger writes to it. `daemon.py` maps `SpotifyOauthError`/`AuthError` (token revoked while running) to HTTP 401 with a re-login hint, and logs 403/409/502 cases.
- Thin button scripts in `scripts/` (`play.py`, `pause.py`, `next.py`, `previous.py`, `volume_40.py`) — each makes one `requests` call to the daemon with a 3s timeout and exits 1 on failure. They deliberately avoid importing spotipy so they start fast. `volume_40.py` is the template for parameterized buttons: copy it and change `VOLUME_LEVEL`.
- `scripts/_config.py` — shared by the thin scripts: daemon URL, and `DAEMON_TOKEN` read from the environment with `DAEMON_TOKEN_FALLBACK` as an in-file alternative. It exits at import if no token is set.

## Constraints to preserve

- Never bind the daemon to `0.0.0.0`, and don't add CORS middleware or remove the token check — these are the protection against localhost drive-by requests from web pages.
- Adding a new action means: a new endpoint in `daemon.py` (with `dependencies=[Depends(verify_token)]` and the same error mapping) plus a new thin script modeled on the existing ones.
- Needs `.env` and `.spotify_token_cache` locally; neither should be committed.
