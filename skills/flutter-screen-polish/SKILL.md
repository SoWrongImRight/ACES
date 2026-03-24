# Skill: Flutter Screen Polish

Use this skill when improving:
- match board UI
- phase focus transitions
- card interaction flows
- overlays
- mobile readability
- target highlighting
- player HUD

## Goal
Improve clarity and premium feel without changing game rules.

## Workflow
1. Identify the exact screen and user interaction being improved.
2. Preserve current backend-driven rules behavior.
3. Improve:
   - hierarchy
   - readability
   - touchability
   - state clarity
4. Keep the non-active player's board visible and stable.
5. Ensure targeting mode uses backend-provided legal targets.
6. Keep animations subtle and fast.

## Required UX Rules
- Tap = expand/collapse if not targeting
- Tap & hold = inspect overlay
- Entering targeting mode collapses expansion views
- Active player zone may softly expand by phase
- Non-active board must never be obscured

## Avoid
- animations that hide state
- hard-coded legality in client
- modal spam
- tiny unreadable attachment layouts