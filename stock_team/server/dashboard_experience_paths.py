from __future__ import annotations

from dataclasses import dataclass


MAX_HIGH_PRIORITY_ISSUES = 3
MAX_FIXES_PER_ROUND = 2
PROTECTED_SCOPE_TOKENS = (
    "backtest",
    "joint_backtest",
    "parameter_sweep",
    "sweep",
    "simulation",
)


@dataclass(frozen=True)
class ExperiencePath:
    id: str
    title: str
    goal: str
    entry_hint: str
    success_signal: str


EXPERIENCE_PATHS = (
    ExperiencePath(
        id="path_a_premarket_orientation",
        title="Premarket Orientation",
        goal="Identify market phase and current top action from the landing view.",
        entry_hint="Open the dashboard landing page.",
        success_signal="Current phase and top action are obvious within one screen.",
    ),
    ExperiencePath(
        id="path_b_premarket_readiness",
        title="Premarket Readiness",
        goal="Confirm today focus and determine which symbols deserve attention first.",
        entry_hint="Start from the landing overview and inspect today's focus area.",
        success_signal="Ready vs not-ready symbols can be differentiated without cross-reading multiple modules.",
    ),
    ExperiencePath(
        id="path_c_symbol_action",
        title="Move Into Symbol-Level Action",
        goal="Enter a focus symbol and find price, node, and action-relevant data quickly.",
        entry_hint="Open a symbol detail view from the overview.",
        success_signal="Price, node, and action context are visible without hunting across sections.",
    ),
    ExperiencePath(
        id="path_d_return_to_global",
        title="Return To Global Monitoring",
        goal="Return from symbol detail and recover the next global monitoring priority.",
        entry_hint="Navigate back from a symbol detail view.",
        success_signal="The next monitoring target is obvious after returning to the global view.",
    ),
)


def path_ids() -> list[str]:
    return [path.id for path in EXPERIENCE_PATHS]
