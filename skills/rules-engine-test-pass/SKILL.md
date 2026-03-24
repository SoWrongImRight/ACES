# Skill: Rules Engine Test Pass

Use this skill when changing:
- target legality
- hazards
- combat resolution
- refit behavior
- fuel behavior
- exhaustion behavior
- win conditions
- runway interaction
- aircraft action sequencing

## Goal
Ensure game rule changes are correct, deterministic, and covered by tests.

## Workflow
1. Identify the rule being changed.
2. Find where legality is validated.
3. Find where resolution is applied.
4. Update or add tests for:
   - happy path
   - illegal path
   - at least one edge case
5. Run relevant tests.
6. Summarize what changed in game terms, not just code terms.

## Must Verify
- UI is not deciding legality
- backend remains source of truth
- trigger windows still behave correctly
- refit/launch restrictions remain correct
- exhausted cards are handled consistently

## Output Format
Summarize:
- rule changed
- files changed
- tests added/updated
- risks or follow-ups