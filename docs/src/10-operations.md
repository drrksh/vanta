# Installing and running {#ch-ops}

## Requirements

| Tool | Version used | Needed for |
|---|---|---|
| Python | 3.13 (3.11+ should work) | Backend and Discord bot |
| gcc | any recent version with AddressSanitizer and UBSan | Compiling worlds and submissions |
| Node.js + npm | Node 22 | Frontend |
| A modern browser | — | Using the web UI |

The sanitizers need a Linux or macOS toolchain. On Windows, use WSL (Windows Subsystem for
Linux).

## First-time setup

```bash
# 1. backend
cd backend
python3 -m venv .venv
.venv/bin/pip install fastapi uvicorn pydantic httpx pytest pytest-asyncio "discord.py>=2.4"

# 2. frontend
cd ../frontend
npm install
```

## Starting everything

```bash
./run_dev.sh            # from the repository root: API on :8811, web on :5173
```

Or start each one in its own terminal:

```bash
cd backend  && .venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8811
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
```

Then open `http://127.0.0.1:5173`. The Vite dev server forwards `/api` to port 8811. The
interactive API explorer is at `http://127.0.0.1:8811/docs`.

**Production build.** `npm run build` writes static files to `frontend/dist/`. Serve them with
any web server that forwards `/api` to the backend.

## Configuration (environment variables)

| Variable | Read by | Meaning |
|---|---|---|
| `VANTA_ADMIN_TOKEN` | API and bot | Secret for admin actions. If unset on the API, any `X-Vanta-Admin` header counts as admin (demo mode) |
| `DISCORD_TOKEN` | bot | The bot's token from the Discord Developer Portal (required for the bot) |
| `VANTA_API_URL` | bot | Where the API is (default `http://127.0.0.1:8811`) |
| `VANTA_WEB_URL` | bot | If set, world embeds link to `<url>/worlds/<id>` |
| `DISCORD_GUILD_ID` | bot | Sync commands to this one server instantly (otherwise global sync, which can take up to an hour) |

## Setting up the Discord bot, step by step

1. Go to the Discord Developer Portal, create an **Application**, open **Bot**, and copy the
   **token**.
2. Under **OAuth2 → URL Generator** choose the scopes `bot` and `applications.commands` and the
   permissions *Send Messages*, *Attach Files* and *Embed Links*. Open the generated URL and add
   the bot to your server.
3. Turn on Discord's Developer Mode, right-click your server, and choose *Copy Server ID*.
4. With the API running, start the bot from the repository root:

```bash
pip install -r discord_bot/requirements.txt
DISCORD_TOKEN=... DISCORD_GUILD_ID=... \
VANTA_API_URL=http://127.0.0.1:8811 VANTA_WEB_URL=http://127.0.0.1:5173 \
python -m discord_bot.bot
```

**Step 5.** Type `/vanta` in your server. The 16 commands should appear.

For admin commands to work with a token configured, set the **same** `VANTA_ADMIN_TOKEN` for the
API and the bot.

## Ports and processes

| Process | Port | Log (when started by run_dev.sh) |
|---|---|---|
| Uvicorn (FastAPI) | 8811 | `backend/server.log` |
| Vite dev server | 5173 | `frontend/vite.log` |
| Discord bot | — (outbound only) | console |

## Common tasks

| Task | How |
|---|---|
| Reset everything | Stop the API, delete `backend/vanta_worlds.db`, start it again |
| Delete every world (keep ratings and cohorts) | `curl -X DELETE -H "X-Vanta-Admin: <token>" http://127.0.0.1:8811/api/worlds` |
| See a world's planted bug | `curl -H "X-Vanta-Admin: <token>" http://127.0.0.1:8811/api/admin/worlds/<id>` |
| Rebuild this PDF | `python3 docs/build_docs.py` (needs `markdown`, `pygments`, `pypdf`, Node and Playwright) |
| Run the tests | `cd backend && .venv/bin/python3 -m pytest tests -q` |
