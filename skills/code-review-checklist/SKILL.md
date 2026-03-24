# Skill: Code Review Checklist

Use this skill when reviewing a branch, diff, or PR.

## Goal
Catch correctness, architecture, and product-alignment issues before merge.

## Review Checklist

### Rules / correctness
- Is backend still the source of truth?
- Was any legality duplicated in UI?
- Are turn/phase restrictions preserved?
- Are hazards validated by actual trigger conditions?
- Are refit and launch interactions still correct?
- Is exhaustion handled consistently?

### UX
- Does the change preserve board clarity?
- Is non-active board still visible?
- Are legal targets highlighted from backend data?
- Are interactions consistent with tap / hold / targeting rules?

### Product alignment
- Any pay-to-win risk introduced?
- Any milestone reward accidentally purchasable?
- Any bot result counting toward PvP prestige?
- Any communication feature violating current no-chat rule?

### Engineering quality
- Are tests present where rules changed?
- Are names clear?
- Is logic duplicated?
- Are summaries/documentation updated where needed?

## Output
Summarize:
- high-risk findings first
- required fixes
- optional polish items
- merge confidence