"""
Starvation / Fairness archetype.

A single shared resource serves a stream of size-varying requests. The
"obvious" greedy strategy can starve a large legitimate request under
sustained load, or start a job it cannot finish before closing, etc.

Everything is procedurally varied per seed: domain framing, struct/field
names, function name, numeric constants, AND which of several buggy
formulations is used as the starter code. Genes shape it:
  - system_size        -> (reserved; this archetype is single-function)
  - bug_subtlety       -> picks subtler bug variants, smaller margins
  - constant_magnitude -> larger day lengths / job sizes
  - edge_density       -> (reserved; fixed strong suite here)
Correctness lessons baked in:
  - chooseNext is given minutesLeftToday, so M3 (don't start what can't
    finish before close) is a real, checkable contestant responsibility.
  - The harness never lets chooseNext consider a request before its
    submittedAt tick (that was a real harness bug that made starvation
    results an artifact rather than a property).
  - The starvation stream submits the big job INTO an already-flowing
    small-job stream, so it genuinely competes rather than winning by
    default emptiness at t=0.
  - Every hidden test checks the FULL mandatory mask (1|4|16), never a
    narrow subset (a narrow mask silently passed broken variants before).
"""
from __future__ import annotations

from app.worldgen.archetype import FlawArchetype, GeneratedAgentGrounding, GeneratedWorld

_DOMAINS = [
    {"noun": "print job", "machine": "3D printer", "place": "the student fabrication lab"},
    {"noun": "wash cycle", "machine": "washing machine", "place": "the dormitory laundry room"},
    {"noun": "render job", "machine": "shared GPU workstation", "place": "the media lab"},
    {"noun": "repair request", "machine": "bike repair stand", "place": "the campus cycling co-op"},
    {"noun": "scan request", "machine": "document scanner", "place": "the library digitization desk"},
]

_STRUCT_NAMES = ["Job", "Task", "Request", "WorkItem", "Ticket"]
_FUNC_NAMES = ["chooseNext", "selectNext", "pickNextJob", "nextToRun", "scheduleNext"]
# Ordered roughly easy->subtle; bug_subtlety biases the pick toward the end.
_BUG_VARIANTS = ["no_close_check", "pure_shortest_first", "truncating_priority"]


class StarvationArchetype(FlawArchetype):
    id = "starvation_fairness"
    title = "Shared Resource Fairness"
    domain = "resource_allocation"

    def generate(self, seed: int, genes: dict | None = None) -> GeneratedWorld:
        genes = self.resolve_genes(genes)
        rng = self.rng(seed)

        domain = rng.choice(_DOMAINS)
        struct_name = rng.choice(_STRUCT_NAMES)
        func_name = rng.choice(_FUNC_NAMES)

        # bug_subtlety biases which variant we pick: higher -> later (subtler).
        subtlety = genes["bug_subtlety"]
        weights = [1.0 - subtlety, 0.5, 0.3 + subtlety]
        bug_variant = rng.choices(_BUG_VARIANTS, weights=weights, k=1)[0]

        # constant_magnitude scales the day length and job sizes.
        mag = genes["constant_magnitude"]
        day_length = rng.choice([360, 420, 480, 540, 600])
        day_length = int(day_length * (0.8 + 0.6 * mag))
        big_job_minutes = rng.randint(int(day_length * 0.55), day_length - 10)
        small_job_minutes = rng.randint(5, 15)
        # The starvation-stream test must SATURATE the machine: small jobs
        # have to arrive at least as fast as they complete, or the queue
        # drains and the big job gets served (no starvation, bug doesn't
        # manifest). Interval strictly less than service time guarantees a
        # perpetually non-empty queue. (A real bug found in testing: when
        # interval > service time the queue empties and even pure
        # shortest-first serves the big job on time.)
        small_interval = rng.randint(2, max(2, small_job_minutes - 1))
        big_submitted_at = small_interval * rng.randint(8, 20)
        starve_bound = rng.randint(1500, 2500)

        shared_header = f"""
#define MAX_JOBS 700
struct {struct_name} {{
    int id;
    int minutesNeeded;
    int submittedAt;
    int isAbandoned;
    int isFinished;
    int isRejected;
    int startedAt;
    int finishedAt;
}};
int {func_name}(struct {struct_name} jobs[], int count, int now, int minutesLeftToday);
"""

        starter_source = self._starter(struct_name, func_name, bug_variant)
        harness_source = self._harness(
            struct_name, func_name, day_length, starve_bound,
            big_job_minutes, big_submitted_at, small_job_minutes, small_interval,
        )

        mandatory = [
            f"No submitted, valid {domain['noun']} is ignored forever.",
            f"An abandoned {domain['noun']} must eventually free the {domain['machine']}.",
            f"The {domain['machine']} never starts a {domain['noun']} that can't finish before close.",
            "A request needing more time than a full day allows must be rejected.",
            "The program terminates for every finite input.",
            "No request is started twice; every request's final status is accounted for.",
        ]
        optional = [
            "Minimize average completion time.",
            "Minimize the maximum wait for any single request.",
            f"Minimize idle time on the {domain['machine']}.",
            "Favor implementation simplicity.",
            "Resist one person monopolizing the machine with many tiny requests.",
        ]

        briefing = (
            f"{domain['place'].capitalize()} has one {domain['machine']} available to everyone. "
            f"People submit {domain['noun']}s throughout the week. The {domain['machine']} is only "
            f"usable part of the day and runs one job at a time. Some people say the current process "
            f"lets certain people dominate it; others say the complaints are overblown. Figure out "
            f"what's actually going on and propose how requests should be handled."
        )
        specification = (
            f"Implement {func_name}(), which decides which pending {domain['noun']} the "
            f"{domain['machine']} should run next, given the request list and the minutes "
            f"remaining before close today. Base your design on what you learn by investigating. "
            f"Many different designs can be correct."
        )
        sample_desc = f"A day is {day_length} simulated minutes. Build your own test cases."

        groundings = [
            GeneratedAgentGrounding("frequent_small_user", {"own_job_minutes": small_job_minutes,
                                                            "machine": domain["machine"]}),
            GeneratedAgentGrounding("infrequent_large_user", {"own_job_minutes": big_job_minutes,
                                                             "machine": domain["machine"]}),
            GeneratedAgentGrounding("developer", {"day_length": day_length, "variant": bug_variant}),
            GeneratedAgentGrounding("manager", {"machine": domain["machine"]}),
            GeneratedAgentGrounding("facilities", {"machine": domain["machine"]}),
        ]

        return GeneratedWorld(
            archetype_id=self.id, seed=seed, genes=genes,
            title=domain["place"].replace("the ", "").title(),
            briefing=briefing, specification=specification,
            starter_source=starter_source, function_name=func_name,
            function_signature=(
                f"int {func_name}(struct {struct_name} jobs[], int count, int now, int minutesLeftToday)"
            ),
            shared_header=shared_header,
            mandatory_properties=mandatory, optional_objectives=optional,
            sample_input_description=sample_desc, agent_groundings=groundings,
            harness_source=harness_source,
            ground_truth_summary=(
                f"archetype={self.id} bug_variant={bug_variant} day_length={day_length} "
                f"big_job_minutes={big_job_minutes} big_submitted_at={big_submitted_at} "
                f"small_job_minutes={small_job_minutes} small_interval={small_interval} "
                f"starve_bound={starve_bound} subtlety={subtlety:.2f} mag={mag:.2f}"
            ),
        )

    def _starter(self, struct_name, func_name, bug_variant) -> str:
        if bug_variant == "pure_shortest_first":
            return f"""
int {func_name}(struct {struct_name} jobs[], int count, int now, int minutesLeftToday) {{
    int best = -1;
    for (int i = 0; i < count; i++) {{
        if (jobs[i].isAbandoned || jobs[i].isFinished || jobs[i].isRejected) continue;
        if (jobs[i].startedAt != -1) continue;
        if (jobs[i].submittedAt > now) continue;
        if (jobs[i].minutesNeeded > minutesLeftToday) continue;
        if (best == -1 || jobs[i].minutesNeeded < jobs[best].minutesNeeded) best = i;
    }}
    return best;
}}
"""
        if bug_variant == "no_close_check":
            return f"""
int {func_name}(struct {struct_name} jobs[], int count, int now, int minutesLeftToday) {{
    (void)minutesLeftToday;
    int oldest = -1;
    for (int i = 0; i < count; i++) {{
        if (jobs[i].isAbandoned || jobs[i].isFinished || jobs[i].isRejected) continue;
        if (jobs[i].startedAt != -1) continue;
        if (jobs[i].submittedAt > now) continue;
        if (oldest == -1 || jobs[i].submittedAt < jobs[oldest].submittedAt) oldest = i;
    }}
    return oldest;
}}
"""
        return f"""
int {func_name}(struct {struct_name} jobs[], int count, int now, int minutesLeftToday) {{
    int best = -1, bestScore = -1;
    for (int i = 0; i < count; i++) {{
        if (jobs[i].isAbandoned || jobs[i].isFinished || jobs[i].isRejected) continue;
        if (jobs[i].startedAt != -1) continue;
        if (jobs[i].submittedAt > now) continue;
        if (jobs[i].minutesNeeded > minutesLeftToday) continue;
        int waited = now - jobs[i].submittedAt;
        int score = (waited > 0) ? (jobs[i].minutesNeeded / waited) : jobs[i].minutesNeeded;
        if (score > bestScore) {{ bestScore = score; best = i; }}
    }}
    return best;
}}
"""

    def _harness(self, struct_name, func_name, day_length, starve_bound,
                 big_minutes, big_submitted_at, small_minutes, small_interval) -> str:
        small_inits = []
        jid = 1
        t = 0
        while t < 25000 and len(small_inits) < 600:
            small_inits.append(
                f"jobs[idx++] = (struct {struct_name}){{{jid}, {small_minutes}, {t}, 0, 0, 0, -1, -1}};"
            )
            jid += 1
            t += small_interval
        big_line = (
            f"jobs[idx++] = (struct {struct_name}){{9999, {big_minutes}, "
            f"{big_submitted_at}, 0, 0, 0, -1, -1}};"
        )
        small_block = "\n        ".join(small_inits)

        return f"""
#include <stdio.h>
#include <string.h>
#define OPEN_MINUTES_PER_DAY {day_length}
#define MAX_DAYS 120
#define TICK_STARVE_BOUND {starve_bound}

static int allDone(struct {struct_name} jobs[], int count) {{
    for (int i = 0; i < count; i++)
        if (!jobs[i].isFinished && !jobs[i].isRejected && !jobs[i].isAbandoned) return 0;
    return 1;
}}

/* bitmask: 1=starvation 4=started-too-late 16=bad-pick */
static int runSimulation(struct {struct_name} jobs[], int count) {{
    int violations = 0, currentJob = -1, currentJobDeadline = -1;
    for (int i = 0; i < count; i++)
        if (jobs[i].minutesNeeded > OPEN_MINUTES_PER_DAY) jobs[i].isRejected = 1;

    for (int day = 0; day < MAX_DAYS; day++) {{
        int dayStart = day * OPEN_MINUTES_PER_DAY, dayEnd = dayStart + OPEN_MINUTES_PER_DAY;
        for (int t = dayStart; t < dayEnd; t++) {{
            if (currentJob != -1 && jobs[currentJob].isAbandoned) currentJob = -1;
            if (currentJob != -1 && t >= currentJobDeadline) {{
                jobs[currentJob].isFinished = 1;
                jobs[currentJob].finishedAt = t;
                currentJob = -1;
            }}
            if (currentJob == -1) {{
                int pick = {func_name}(jobs, count, t, dayEnd - t);
                if (pick != -1) {{
                    if (pick < 0 || pick >= count) {{
                        violations |= 16;
                    }} else if (jobs[pick].submittedAt > t || jobs[pick].isFinished ||
                               jobs[pick].isRejected || jobs[pick].isAbandoned ||
                               jobs[pick].startedAt != -1) {{
                        violations |= 16;
                    }} else {{
                        int deadline = t + jobs[pick].minutesNeeded;
                        if (deadline > dayEnd) {{
                            violations |= 4;
                        }} else {{
                            jobs[pick].startedAt = t;
                            currentJob = pick;
                            currentJobDeadline = deadline;
                        }}
                    }}
                }}
            }}
            for (int i = 0; i < count; i++) {{
                if (!jobs[i].isFinished && !jobs[i].isRejected && !jobs[i].isAbandoned &&
                    jobs[i].startedAt == -1 && t - jobs[i].submittedAt > TICK_STARVE_BOUND) {{
                    violations |= 1;
                }}
            }}
        }}
        if (allDone(jobs, count)) break;
    }}
    if (!allDone(jobs, count)) {{
        for (int i = 0; i < count; i++)
            if (!jobs[i].isFinished && !jobs[i].isRejected && !jobs[i].isAbandoned) violations |= 1;
    }}
    return violations;
}}

static void report(const char *name, int v, int forbidden, int *overall) {{
    int pass = (v & forbidden) == 0;
    printf("VANTA_TEST_RESULT|%s|%d|%d\\n", name, v, pass);
    if (!pass) *overall = 0;
}}

int main(void) {{
    int overallPass = 1;
    {{
        struct {struct_name} jobs[3];
        memset(jobs, 0, sizeof(jobs));
        jobs[0] = (struct {struct_name}){{1, {small_minutes}, 0, 0, 0, 0, -1, -1}};
        jobs[1] = (struct {struct_name}){{2, {small_minutes+2}, 3, 0, 0, 0, -1, -1}};
        jobs[2] = (struct {struct_name}){{3, {small_minutes+1}, 6, 0, 0, 0, -1, -1}};
        report("public_simple", runSimulation(jobs, 3), (1|4|16), &overallPass);
    }}
    {{
        struct {struct_name} jobs[1];
        memset(jobs, 0, sizeof(jobs));
        jobs[0] = (struct {struct_name}){{1, 30, 0, 0, 0, 0, -1, -1}};
        report("public_single", runSimulation(jobs, 1), (1|4|16), &overallPass);
    }}
    {{
        struct {struct_name} jobs[1];
        report("hidden_zero_jobs", runSimulation(jobs, 0), (1|4|16), &overallPass);
    }}
    {{
        struct {struct_name} jobs[1];
        memset(jobs, 0, sizeof(jobs));
        jobs[0] = (struct {struct_name}){{1, OPEN_MINUTES_PER_DAY, 0, 0, 0, 0, -1, -1}};
        report("hidden_exact_fit", runSimulation(jobs, 1), (1|4|16), &overallPass);
    }}
    {{
        struct {struct_name} jobs[2];
        memset(jobs, 0, sizeof(jobs));
        jobs[0] = (struct {struct_name}){{1, OPEN_MINUTES_PER_DAY + 1, 0, 0, 0, 0, -1, -1}};
        jobs[1] = (struct {struct_name}){{2, 30, 0, 0, 0, 0, -1, -1}};
        int v = runSimulation(jobs, 2);
        int pass = (v & (1|4|16)) == 0 && jobs[0].isRejected && jobs[1].isFinished;
        printf("VANTA_TEST_RESULT|hidden_oversized_rejected|%d|%d\\n", v, pass ? 1 : 0);
        if (!pass) overallPass = 0;
    }}
    {{
        static struct {struct_name} jobs[{len(small_inits) + 1}];
        memset(jobs, 0, sizeof(jobs));
        int idx = 0;
        {small_block}
        {big_line}
        report("hidden_starvation_stream", runSimulation(jobs, idx), (1|4|16), &overallPass);
    }}
    {{
        struct {struct_name} jobs[2];
        memset(jobs, 0, sizeof(jobs));
        jobs[0] = (struct {struct_name}){{1, 50, 0, 1, 0, 0, -1, -1}};
        jobs[1] = (struct {struct_name}){{2, 20, 5, 0, 0, 0, -1, -1}};
        report("hidden_abandonment", runSimulation(jobs, 2), (1|4|16), &overallPass);
    }}
    {{
        struct {struct_name} jobs[3];
        memset(jobs, 0, sizeof(jobs));
        jobs[0] = (struct {struct_name}){{3, 15, 20, 0, 0, 0, -1, -1}};
        jobs[1] = (struct {struct_name}){{2, {small_minutes}, 5, 0, 0, 0, -1, -1}};
        jobs[2] = (struct {struct_name}){{1, {big_minutes}, 0, 0, 0, 0, -1, -1}};
        report("hidden_reverse_order", runSimulation(jobs, 3), (1|4|16), &overallPass);
    }}
    printf("VANTA_OVERALL|%d\\n", overallPass);
    return overallPass ? 0 : 1;
}}
"""
