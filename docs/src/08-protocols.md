# C protocols and formats {#ch-protocols}

VANTA's Python side and its generated C programs talk through plain text printed to standard
output. This chapter defines those formats exactly.

## How the two C files are put together

```text
harness_main.c = shared_header + "\n" + harness_source      (has main())
candidate.c    = shared_header + "\n" + contestant source   (has the functions)
gcc harness_main.c candidate.c -o a.out
```

Each file is a separate *translation unit*, so both get the shared header (struct + prototypes).
The contestant must define every function that the shared header declares and the harness calls.
In pool worlds that means both the checkout and the release function.

## Grading output

Printed by every hidden-test harness:

```text
VANTA_TEST_RESULT|<test name>|<violations>|<passed 0/1>
...
VANTA_OVERALL|<1 if every test passed, else 0>
```

- `violations` is a number. For scheduler worlds it is a bitmask: 1 = a job was starved, 4 = a
  job was started that could not finish before closing, 16 = a bad pick. For pool worlds it is 0
  for a pass and 1 for a fail.
- The program exits with 0 if everything passed and 1 otherwise.
- If `VANTA_OVERALL|` never appears, the program crashed (a sanitizer trap, a segmentation fault,
  or an `abort`), and the verdict is `runtime_error`.

## Scheduler probe output (`job_queue`)

```text
PROBE_EVENT|<minute>|<kind>|<job id or index>        (at most event_cap lines)
PROBE_JOB|<id>|<minutes>|<submitted>|<started or -1>|<finished or -1>|<status>
PROBE_STAT|<busy>|<open>|<idle_waiting>|<too_late>|<invalid>|<days>|<events>|<max_queue>
PROBE_DONE
```

| Event kind | Meaning |
|---|---|
| `start`, `finish` | The machine began or completed a job |
| `abandoned` | The owner walked away (`abandon_after`) |
| `freed` | A running job was abandoned, so the machine stopped it |
| `rejected` | The job was longer than a whole day, so it was refused up front |
| `refused_too_late` | The scheduler chose a job that couldn't finish before closing; the machine idled that minute (logged once per job per day) |
| `invalid_pick` | The scheduler chose a job not yet submitted, already finished, or already started |
| `invalid_index` | The scheduler returned an index outside 0…count−1 |

Job ids are assigned 1, 2, 3 … in the order the scenario entries are expanded. `PROBE_DONE` is
always the last line. If it is missing, the run crashed.

## Pool probe output (`pool`)

```text
PROBE_OP|<k>|<0 checkout / 1 release>|<holder>|<returned>|<in use after>|<receipts after>
PROBE_SLOT|<slot>|<in use 0/1>|<holderId stored in memory>
PROBE_STAT|<pool size>|<in use>|<receipts>|<operation count>
PROBE_DONE
```

"Receipts" are kept by the harness: +1 when a checkout returns something other than −1, and −1
when a release returns non-zero.

## Scenario JSON schemas

### Scheduler

```text
{
  "days": int 1..30            (optional, default 3)
  "jobs": [                    (required, 1..700 jobs after expansion)
    {
      "minutes": int 1..20000,             required
      "at": int 0..days*L,                 required, submission minute
      "repeat": int 1..700,                optional, default 1
      "every": int 1..100000,              optional, default 1
      "abandon_after": int 0..1000000,     optional, minutes after submission
      "owner": string                      optional, used internally by witnesses
    }
  ]
}
```

### Pool

```text
{
  "ops": [                     (required, 1..3000 operations after expansion)
    {
      "op": "checkout" | "release" | "cycle",   required
      "holder": int 0..10000000,                required
      "repeat": int 1..3000,                    optional, default 1
      "step": int 0..100000,                    optional, default 0
      "owner": string                           optional
    }
  ]
}
```

Booleans and non-integer numbers are rejected. Values out of range produce a 422 error that names
the field, for example `'ops[2].holder' must be between 0 and 10000000 (got -4)`.

## Code safety rules

Before anything is compiled, contestant code (for grading, probes and replays) is checked against
these patterns. A match is reported as a compile error:

```text
system(   exec*(   fork(   popen(   fopen(   freopen(   remove(   unlink(   rename(
#include <unistd.h>   #include <sys/...>   #include <fcntl.h>   asm   __asm__
```

Then the code is compiled with sanitizers and run with a 15-second limit (grading and probes) in
a temporary folder that is deleted afterwards. Chapter 11 discusses what this does and does not
protect against.
