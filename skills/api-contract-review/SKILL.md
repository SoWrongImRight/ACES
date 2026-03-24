# Skill: API Contract Review

Use this skill when working on:
- match action endpoints
- websocket payloads
- state snapshots
- legal target responses
- action validation responses
- progression or deck APIs

## Goal
Keep the backend/client contract explicit, stable, and rules-authoritative.

## Workflow
1. Inspect the current request/response shape.
2. Verify that the client sends intent, not resolved game logic.
3. Verify that backend returns:
   - status
   - valid targets if applicable
   - updated state or event stream
4. Check that field names are explicit and stable.
5. Confirm the contract supports mobile/web equally well.

## Good Pattern
Client sends:
- action intent
- selected ids
- no legality assumptions

Backend returns:
- success/failure
- legal targets
- state updates
- reason on invalid action

## Avoid
- letting the UI infer legal targets
- hidden magic flags with unclear meaning
- response shapes that differ by platform