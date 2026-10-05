"""
Originality across a cohort: how many genuinely different approaches did
people take to the same problem?

Every cohort member fixes the same defect, but in their own world: their
struct and function names differ, and so do the constants. Comparing raw
source would therefore say everyone is different. Comparing it naively the
other way would say everyone is the same, because they all started from the
same starter shape. So, in the spirit of MOSS:

  1. Normalize each submission against its own world: the world's own struct
     and function names become STRUCT / FN / FN2, other identifiers are
     renamed by first appearance (so renaming variables doesn't hide
     anything), numbers become NUM, comments and strings disappear.
  2. Fingerprint it as hashed token k-grams.
  3. Subtract the fingerprints of that member's own starter. What's left is
     what the person actually wrote.
  4. Compare those "novel" sets pairwise (Jaccard) and group accepted
     solutions whose novel parts overlap heavily into one approach.

This is a measure of approach diversity, not a plagiarism verdict: two
people can independently make the same small fix. The host sees the
numbers and decides.
"""
from __future__ import annotations

import hashlib
import re

from app.worldgen.archetype import GeneratedWorld

_C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else",
    "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long", "register",
    "restrict", "return", "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
    "union", "unsigned", "void", "volatile", "while", "_Bool", "bool", "true", "false", "NULL",
}
_TOKEN = re.compile(
    r"[A-Za-z_]\w*|\d+|->|\+\+|--|<=|>=|==|!=|&&|\|\||\+=|-=|\*=|/=|%=|<<|>>|[^\s\w]"
)
K = 6
APPROACH_THRESHOLD = 0.55
NEAR_IDENTICAL = 0.85


def _strip(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", " ", source, flags=re.S)
    source = re.sub(r"//[^\n]*", " ", source)
    source = re.sub(r'"(?:\\.|[^"\\])*"', ' "S" ', source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", " 'C' ", source)
    source = re.sub(r"^\s*#[^\n]*", " ", source, flags=re.M)
    return source


def _world_names(world: GeneratedWorld) -> dict[str, str]:
    p = world.params or {}
    names = {}
    if p.get("struct_name"):
        names[p["struct_name"]] = "STRUCT"
    names[world.function_name] = "FN"
    if p.get("checkout_func"):
        names[p["checkout_func"]] = "FN2"
    return names


def _fields(world: GeneratedWorld) -> set[str]:
    body = re.search(r"struct \w+ \{(.*?)\};", world.shared_header, flags=re.S)
    if not body:
        return set()
    return set(re.findall(r"\b(\w+)\s*;", body.group(1)))


def normalize(source: str, world: GeneratedWorld) -> list[str]:
    canon = _world_names(world)
    keep = _C_KEYWORDS | _fields(world)
    rename: dict[str, str] = {}
    out = []
    for tok in _TOKEN.findall(_strip(source)):
        if tok in canon:
            out.append(canon[tok])
        elif tok in keep:
            out.append(tok)
        elif tok[0].isalpha() or tok[0] == "_":
            if tok not in rename:
                rename[tok] = f"V{len(rename)}"
            out.append(rename[tok])
        elif tok.isdigit():
            out.append(tok if tok in ("0", "1") else "NUM")
        else:
            out.append(tok)
    return out


def fingerprints(tokens: list[str], k: int = K) -> set[str]:
    if len(tokens) < k:
        return {hashlib.blake2b(" ".join(tokens).encode(), digest_size=8).hexdigest()} if tokens else set()
    return {
        hashlib.blake2b(" ".join(tokens[i:i + k]).encode(), digest_size=8).hexdigest()
        for i in range(len(tokens) - k + 1)
    }


def novel_fingerprints(source: str, world: GeneratedWorld) -> set[str]:
    return fingerprints(normalize(source, world)) - fingerprints(normalize(world.starter_source, world))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def analyze(entries: list[dict]) -> dict:
    """entries: [{"member": str, "world": GeneratedWorld, "source": str, "accepted": bool}].
    Uses each member's most recent submission (caller passes one per member)."""
    prepared = []
    for e in entries:
        nov = novel_fingerprints(e["source"], e["world"])
        prepared.append({**e, "novel": nov})
    changed = [e for e in prepared if len(e["novel"]) >= 3]

    pairs = []
    for i in range(len(changed)):
        for j in range(i + 1, len(changed)):
            a, b = changed[i], changed[j]
            pairs.append({"a": a["member"], "b": b["member"],
                          "similarity": round(jaccard(a["novel"], b["novel"]), 3),
                          "both_accepted": a["accepted"] and b["accepted"]})
    pairs.sort(key=lambda x: -x["similarity"])

    # Greedy single-link grouping of ACCEPTED solutions into approaches.
    accepted = [e for e in changed if e["accepted"]]
    groups: list[list[dict]] = []
    for e in accepted:
        home = None
        for g in groups:
            if any(jaccard(e["novel"], x["novel"]) >= APPROACH_THRESHOLD for x in g):
                home = g
                break
        if home is None:
            groups.append([e])
        else:
            home.append(e)

    return {
        "submissions_compared": len(changed),
        "unchanged_from_starter": [e["member"] for e in prepared if len(e["novel"]) < 3],
        "accepted": len(accepted),
        "distinct_approaches": len(groups),
        "approaches": [sorted(x["member"] for x in g) for g in groups],
        "pairs": pairs[:25],
        "near_identical": [p for p in pairs if p["similarity"] >= NEAR_IDENTICAL],
        "method": (f"token {K}-grams after renaming each world's own identifiers, minus the "
                   f"member's starter; approaches grouped at Jaccard >= {APPROACH_THRESHOLD}"),
    }
