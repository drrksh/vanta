"""
C Sandbox: compiles and runs contestant-submitted (or generator-produced)
C against a fixed harness, with a static safety pre-check, hardened compile
flags, and a wall-clock timeout.

Prototype-grade process isolation (subprocess + compiler sanitizers), a
deliberate, replaceable boundary -- not container/VM grade. The abstraction
(`compile_and_run`) can be swapped for a stronger sandbox later without
touching callers.

Design notes carried over from earlier development:
  - gcc compiles each .c file as an independent translation unit before
    linking, so BOTH the harness and the candidate need the shared
    struct/prototype declarations. We prepend `shared_header` to each.
  - Sanitizers (-fsanitize=undefined,address) turn UB / out-of-bounds /
    overflow into a nonzero exit, so a program that "works by accident"
    still fails here.
"""
from __future__ import annotations

import asyncio
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Constructs a contestant/generator must never use. Checked before the
# compiler is even invoked, so a malicious submission can't reach the
# filesystem, network, or spawn processes.
FORBIDDEN_PATTERNS = [
    r"\bsystem\s*\(",
    r"\bexec[lv]p?e?\s*\(",
    r"\bfork\s*\(",
    r"\bpopen\s*\(",
    r"\bfopen\s*\(",
    r"\bfreopen\s*\(",
    r"\bremove\s*\(",
    r"\bunlink\s*\(",
    r"\brename\s*\(",
    r"#\s*include\s*<unistd\.h>",
    r"#\s*include\s*<sys/",
    r"#\s*include\s*<fcntl\.h>",
    r"\basm\b",
    r"__asm__",
]


class UnsafeCSourceError(Exception):
    pass


def static_safety_check(source: str) -> None:
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, source):
            raise UnsafeCSourceError(
                f"Submitted C source contains a disallowed construct matching '{pattern}'."
            )


@dataclass
class CRunResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    compile_error: str | None = None
    runtime_error: str | None = None
    timed_out: bool = False
    exit_code: int | None = None


class CSandbox:
    def __init__(self, timeout_seconds: float = 10.0, compiler: str = "gcc"):
        self.timeout_seconds = timeout_seconds
        self.compiler = compiler

    async def compile_and_run(
        self,
        harness_source: str,
        candidate_source: str,
        shared_header: str = "",
    ) -> CRunResult:
        try:
            static_safety_check(candidate_source)
        except UnsafeCSourceError as exc:
            return CRunResult(success=False, compile_error=str(exc))

        workdir = Path(tempfile.mkdtemp(prefix="vanta_c_"))
        try:
            harness_path = workdir / "harness_main.c"
            candidate_path = workdir / "candidate.c"
            harness_path.write_text(shared_header + "\n" + harness_source)
            candidate_path.write_text(shared_header + "\n" + candidate_source)

            binary_path = workdir / "a.out"
            compile_cmd = [
                self.compiler,
                "-Wall",
                "-Wextra",
                "-fsanitize=undefined,address",
                "-O0",
                "-g",
                str(harness_path),
                str(candidate_path),
                "-o",
                str(binary_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *compile_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _out, err = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                proc.kill()
                return CRunResult(success=False, compile_error="Compilation timed out.")

            if proc.returncode != 0:
                return CRunResult(success=False, compile_error=err.decode("utf-8", "replace"))

            run_proc = await asyncio.create_subprocess_exec(
                str(binary_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workdir),
            )
            try:
                r_out, r_err = await asyncio.wait_for(
                    run_proc.communicate(), timeout=self.timeout_seconds
                )
            except asyncio.TimeoutError:
                run_proc.kill()
                await run_proc.communicate()
                return CRunResult(
                    success=False, timed_out=True, runtime_error="Execution timed out."
                )

            stdout_text = r_out.decode("utf-8", "replace")
            stderr_text = r_err.decode("utf-8", "replace")
            if run_proc.returncode != 0:
                return CRunResult(
                    success=False,
                    stdout=stdout_text,
                    stderr=stderr_text,
                    runtime_error=f"Program exited with code {run_proc.returncode}.",
                    exit_code=run_proc.returncode,
                )
            return CRunResult(success=True, stdout=stdout_text, stderr=stderr_text, exit_code=0)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
