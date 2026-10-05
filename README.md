# VANTA

**Virtualized Adversarial Network & Technical Assessment**

> "Don't give the contestant a problem. Give them a world."

VANTA generates a small, broken C system on demand: its own names, its own
numbers, and one real defect drawn from a pool of defect classes. It
compiles and runs every candidate world to prove three things before anyone
sees it: the defect is real, the system can be fixed, and at least two
architecturally different fixes pass. Contestants then investigate (talk to
witnesses, run experiments) and submit C code that is graded by execution,
not by a person or a language model.

No problem, answer or character backstory is stored anywhere. Everything a
contestant reads, every witness statement and every experiment result comes
from running code.

## The four layers

| Layer | What it does | Where |
|---|---|---|
| **Archetypes** | Programs that build a world from `(seed, genes)`: struct and function names, constants, which bug variant, the hidden test harness. | `backend/app/worldgen/` |
| **Evolution** | Generate → compile → test → score → select → mutate. Fitness = broken + fixable + ≥2 distinct fixes + closeness to the target difficulty. Only viable worlds are served. | `backend/app/evolution/` |
| **Investigation** | *Probe lab*: the contestant writes a JSON experiment; VANTA builds a harness for it and runs the original system or their patch. *Witnesses*: each one lived through one real execution of a generated busy period and reports only what their vantage could see. They can relive the same period under the contestant's code. | `backend/app/investigation/` |
| **Adaptation** | Elo-style rating per contestant. A world of difficulty *d* is an opponent rated `800 + 1200·d`; the next world is aimed slightly above the contestant's current level. | `backend/app/core/profiles.py` |

### Why witnesses can't be argued with

Witnesses aren't characters with a script. A witness is a vantage point: "submits short jobs every morning", "works the returns desk",
"reconciles the books". VANTA runs the system once over a week (or a
day) of realistic load, and each witness's answers are computed from their
slice of that run. The same question always gets the same answer. Questions
about the code get "I'm not the one who wrote it". There is no knowledge
base, so there is nothing to coax out of them.

### Why two people's solutions differ

- Each world has unique names and constants, and the bug variant is drawn from several per class.
- Each defect class admits several correct designs. For example, aging versus
  oldest-first scheduling, or forward versus backward slot scans. The
  evolution loop proves at least two of them pass.
- Witness replays expose trade-offs between correct designs. A fix that
  stops the big job starving can make the frequent small user wait longer, and
  that witness will say so.

## Running it

```bash
# backend (Python 3.12+, gcc)
cd backend
python3 -m venv .venv && .venv/bin/pip install fastapi uvicorn pydantic httpx pytest pytest-asyncio
.venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8811

# frontend
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173      # proxies /api to :8811
```

Open http://127.0.0.1:5173.

Tests: `cd backend && .venv/bin/python3 -m pytest tests -q`. The evolution tests compile many worlds and take a few minutes.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/archetypes` | Defect classes in the pool |
| POST | `/api/worlds` | Evolve a new world. `target_difficulty: null` calibrates it to the creator's rating |
| GET / DELETE | `/api/worlds`, `/api/worlds/{id}` | List, read (contestant view) and delete worlds |
| POST | `/api/worlds/{id}/submit` | Grade C code against hidden tests and update the rating |
| GET / POST | `/api/worlds/{id}/probe` | Probe lab: scenario format, and run an experiment |
| GET | `/api/worlds/{id}/witnesses` | Who was there and what they can be asked |
| POST | `/api/worlds/{id}/witnesses/{key}/ask` | `{topic \| question, c_source?}`: ask, optionally relive the period under your code |
| GET | `/api/profiles/{user}` | Rating, level, recommended difficulty, history |
| GET | `/api/admin/worlds/{id}` | Ground truth, genes and fitness (admin only) |

## A five-minute demo

1. Generate a world with the difficulty set to **Calibrated to you**. VANTA evolves and proves it in a few seconds.
2. Ask the witnesses what happened. Open the record behind an answer to see the raw execution data.
3. In the Probe lab, design an experiment that isolates the symptom you suspect. Run it against the original system.
4. Edit the source. Run the same experiment against your code, and tick "relive under my code" to see how each witness's week changes.
5. Submit. Hidden tests grade it, the rating moves, and the next world is pitched to the new level.
