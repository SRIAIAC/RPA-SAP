"""Safety-net recipe for any workflow.key without a registered recipe in
RECIPES (keeps the engine extensible for future workflows added to
seed_data.py before a bespoke recipe is written for them). Still walks the
workflow's declared steps and still ends in a deterministic-looking
completion — no bare `random.random()` — but doesn't call out to any mock
system, since it has no workflow-specific knowledge of what to fetch.
"""

import json

from app.workflow_engine.recipe_context import RecipeContext, RecipeOutcome


def run(ctx: RecipeContext) -> RecipeOutcome:
    steps = json.loads(ctx.workflow.steps_json)
    for step in steps:
        ctx.record_step(step)
    return RecipeOutcome(
        status="Completed",
        summary=f"Completed successfully — {len(steps)} steps processed, no exceptions.",
    )
