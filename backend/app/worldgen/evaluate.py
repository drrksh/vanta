"""
Evaluates a C submission against a generated world's own harness.

Pure execution -- no LLM in the accept/reject path. The harness prints one
VANTA_TEST_RESULT line per test plus a VANTA_OVERALL line; we parse those.
"""
from __future__ import annotations

from app.execution.c_sandbox import CSandbox
from app.worldgen.archetype import GeneratedWorld


def parse_results(stdout: str) -> list[dict]:
    tests = []
    for line in stdout.splitlines():
        if line.startswith("VANTA_TEST_RESULT|"):
            _, name, violations, passed = line.split("|")
            tests.append({"test": name, "violations": int(violations), "passed": passed == "1"})
    return tests


async def evaluate_submission(
    world: GeneratedWorld, candidate_source: str, sandbox: CSandbox
) -> dict:
    result = await sandbox.compile_and_run(
        world.harness_source, candidate_source, world.shared_header
    )
    if result.compile_error:
        return {"verdict": "rejected", "reason": "compile_error", "detail": result.compile_error}
    if result.timed_out:
        return {"verdict": "rejected", "reason": "timeout", "detail": result.runtime_error}

    # The harness prints VANTA_TEST_RESULT / VANTA_OVERALL lines and then
    # returns exit code 1 when any test failed. A nonzero exit is therefore
    # EXPECTED for a failing submission, not a crash -- so we always parse
    # the printed results first. We only treat it as a genuine runtime error
    # (crash/sanitizer trap) when the program produced no overall verdict
    # line at all.
    tests = parse_results(result.stdout)
    has_overall = "VANTA_OVERALL|" in result.stdout
    if not has_overall:
        # No verdict line => the harness itself crashed before finishing.
        return {
            "verdict": "rejected",
            "reason": "runtime_error",
            "detail": result.runtime_error or result.stderr,
            "tests": tests,
        }
    overall = "VANTA_OVERALL|1" in result.stdout
    return {
        "verdict": "accepted" if overall else "rejected",
        "reason": None if overall else "failed_tests",
        "tests": tests,
    }
