# Skill: Card Effect Implementation

Use this skill when adding or changing:
- weapons
- hazards
- operations
- pilot effects
- support effects
- airframe mod effects

## Goal
Implement card behavior in a way that is data-driven where practical, explicit where necessary, and fully aligned with game rules.

## Workflow
1. Read the card text and restate it in normalized rule language.
2. Identify:
   - trigger
   - target restrictions
   - timing window
   - effect
   - duration if any
3. Confirm whether the effect belongs in:
   - card data
   - rules engine
   - effect resolver
4. Prefer reusable effect primitives over one-off custom logic.
5. Add tests that verify:
   - legal usage
   - illegal usage
   - effect resolution
   - interaction with exhaustion/refit/turn phase if applicable

## Important Rules
- Hazards are only playable by the non-active player
- Hazard legality must come from backend trigger state
- Refit is the only way to equip/modify aircraft by default
- Operations are played during the Command Phase

## Avoid
- putting effect rules in UI
- hardcoding card behavior in multiple places
- vague effect names without tests