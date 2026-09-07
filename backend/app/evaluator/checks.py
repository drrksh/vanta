"""
Deterministic check functions.

Each function takes (world, solution_claims, params) and returns bool.
`solution_claims` is a structured dict produced by the claim parser
(app.evaluator.claim_parser) -- e.g. {"mechanisms": ["versioned_writes", ...]}.

These test PROPERTIES the solution must satisfy, not exact wording (spec
section 24). A scenario's evaluation.tests reference these by `check` name.
"""
from __future__ import annotations

from typing import Callable

CheckFn = Callable[[dict, dict, dict], bool]

_REGISTRY: dict[str, CheckFn] = {}


def register(name: str):
    def deco(fn: CheckFn):
        _REGISTRY[name] = fn
        return fn

    return deco


def get_check(name: str) -> CheckFn:
    if name not in _REGISTRY:
        raise KeyError(f"No evaluator check registered under '{name}'")
    return _REGISTRY[name]


def _mechanisms(claims: dict) -> set[str]:
    return set(claims.get("mechanisms", []))


def _root_cause_ids(claims: dict) -> set[str]:
    return set(claims.get("root_cause_ids", []))


# ---------------------------------------------------------------------
# Generic, reusable checks
# ---------------------------------------------------------------------


@register("requires_any_mechanism")
def requires_any_mechanism(ground_truth: dict, claims: dict, params: dict) -> bool:
    """Passes if the solution claims at least one of params['any_of']."""
    required = set(params.get("any_of", []))
    return bool(_mechanisms(claims) & required)


@register("requires_all_mechanisms")
def requires_all_mechanisms(ground_truth: dict, claims: dict, params: dict) -> bool:
    """Passes only if ALL of params['all_of'] are present."""
    required = set(params.get("all_of", []))
    return required.issubset(_mechanisms(claims))


@register("forbids_mechanism")
def forbids_mechanism(ground_truth: dict, claims: dict, params: dict) -> bool:
    """Fails if the solution relies on a mechanism that doesn't actually fix it."""
    forbidden = set(params.get("none_of", []))
    return not (_mechanisms(claims) & forbidden)


@register("identifies_root_cause")
def identifies_root_cause(ground_truth: dict, claims: dict, params: dict) -> bool:
    """
    Passes if the contestant's identified root cause matches the ground
    truth's root_cause_id (or one of an accepted set of equivalent ids,
    since several correct framings may exist).
    """
    accepted = set(params.get("accepted_root_cause_ids", []))
    accepted.add(ground_truth["root_cause_id"])
    return bool(_root_cause_ids(claims) & accepted)


@register("addresses_invariant")
def addresses_invariant(ground_truth: dict, claims: dict, params: dict) -> bool:
    """
    Passes if the solution's claimed mechanisms are known (from the
    scenario's known_mechanisms list) to satisfy the named invariant.
    params: {"invariant": str, "satisfying_mechanisms": [str, ...]}
    """
    satisfying = set(params.get("satisfying_mechanisms", []))
    return bool(_mechanisms(claims) & satisfying)
