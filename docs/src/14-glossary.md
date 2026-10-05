# Glossary {#ch-glossary}

| Term | Meaning |
|---|---|
| **Admin header** | `X-Vanta-Admin`; grants admin rights when it matches `VANTA_ADMIN_TOKEN` (any value in demo mode) |
| **AddressSanitizer (ASan)** | A gcc feature that makes out-of-bounds or invalid memory access crash immediately, instead of silently misbehaving |
| **Approach** | A group of accepted cohort solutions whose novel code is at least 55% similar |
| **Archetype** | A Python class that generates worlds of one defect class |
| **ASGI** | The interface between Python web frameworks and servers; FastAPI is an ASGI app and Uvicorn is an ASGI server |
| **Bitmask** | An integer whose individual bits mean different things (1, 4, 16 in scheduler tests) |
| **Busy period** | The generated week (or day) of realistic usage that witnesses live through |
| **Calibrated** | Difficulty chosen from your rating instead of picked by hand |
| **Cast** | The witnesses of a world, plus their busy period |
| **Check** | One hidden or public test, as shown to a contestant |
| **Cohort** | A group session: same defect and setting for everyone, a unique world each |
| **CORS** | Browser rule about which websites may call an API; the backend allows all |
| **Deflection** | A witness's polite refusal to discuss code or fixes |
| **Deterministic** | The same inputs always give the same output |
| **Distinct fixes** | How many architecturally different reference fixes pass a world |
| **Domain / setting** | The story frame: which machine or pool, and which place |
| **Elo rating** | A rating system from chess; here, worlds are the opponents |
| **Embed** | A formatted Discord message card |
| **Evidence / the record** | The table of raw execution data behind a witness answer |
| **Evolution** | The generate–test–select–mutate loop that finds viable worlds |
| **FastAPI** | The Python web framework used for the backend |
| **Fingerprint** | A hash of 6 consecutive normalized tokens, used for comparing code |
| **Fitness** | The score that says how good a candidate world is |
| **Genes** | Six 0–1 difficulty dials |
| **Ground truth** | The planted variant and constants; admin-only |
| **Harness** | The generated C `main()` that tests the contestant's functions |
| **Hidden check** | A test whose name and scenario are not shown to contestants |
| **Jaccard similarity** | The size of the intersection divided by the size of the union of two sets |
| **Join code** | The 6-character code for a cohort |
| **Ledger / receipts** | Checkouts granted minus returns accepted, as recorded by the desk |
| **LRU cache** | A cache that discards the least recently used entry when full |
| **Mutation** | A small random change to genes between generations |
| **Normalize** | Rewrite code so names, variables and numbers don't affect comparison |
| **Novel fingerprints** | A submission's fingerprints minus its own starter's |
| **Params** | Structured names and constants of a world, for internal tools |
| **Physical reality** | In pool worlds, who actually holds an item, worked out from what people did |
| **Pins** | A fixed variant and setting (used by cohorts) |
| **Probe / experiment** | A contestant-designed scenario run against the system |
| **Probe kit** | The per-archetype code that validates, builds, runs and parses experiments |
| **Reference fix** | A built-in correct solution used only to prove fixability |
| **Replay** | A witness living the same busy period again under the contestant's code |
| **Sanitizers** | ASan + UBSan, enabled for contestant code |
| **Seed** | The integer every random choice in a world comes from |
| **Shared header** | The struct and prototypes prepended to both C files |
| **Signature (cohort)** | A member's identifier set, kept unique within a cohort |
| **Slash command** | A Discord command such as `/vanta create` |
| **SQLite** | A database stored in one file, `backend/vanta_worlds.db` |
| **Starter source** | The broken code a contestant starts from |
| **Starvation** | A request waiting forever because others keep being chosen first |
| **Topic** | One question a witness can answer, with keywords for routing free text |
| **Trace** | The structured result of running an experiment or busy period |
| **Translation unit** | One `.c` file as the compiler sees it; why both files need the header |
| **UBSan** | UndefinedBehaviorSanitizer: makes undefined behaviour (such as signed overflow) crash |
| **Variant** | Which specific mistake an archetype planted |
| **Viable** | Broken, fixable, and at least 2 distinct fixes pass |
| **Vite** | The frontend build tool and development server |
| **Witness** | A vantage point on one real run of the system, answering bounded questions |
| **World** | One generated challenge: story, code, requirements, hidden tests |
