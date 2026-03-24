# AGENTS.md
## Project: A.C.E.S.
Tactical air combat card game for web, iOS, and Android.

This file gives Codex durable repo guidance. Follow it before making changes.

---

# 1. Product Intent

A.C.E.S. is a tactical, skill-driven card game with:
- no pay-to-win mechanics
- server-authoritative rules
- optional ranked play
- premium, clean UX
- strong separation between gameplay systems and monetization systems

Core product values:
- gameplay clarity over gimmicks
- backend as source of truth
- deterministic rules resolution
- UI should guide, not decide
- milestone rewards are earned only, never bought

---

# 2. Current Core Rules Summary

## Turn phases
Each player completes all phases before turn passes:
1. Command Phase
2. Ground Phase
3. Air Phase
4. End Phase

## Command Phase
- Operations are played here
- command/CP actions begin here

## Ground Phase
Aircraft on the runway may either:
- Refit
- Launch later if they did not refit
- Stay idle

## Refit
Refit is a unified action. Refit includes:
- restoring fuel to max
- un-exhausting attached weapons
- equipping weapons
- equipping airframe mods
- assigning a pilot

If an aircraft refits, it cannot launch that turn.

## Air Phase
Aircraft in the air may:
- move then attack
- attack then move
- return to runway, but return must happen before movement or attack

Each aircraft may attack at most once per Air Phase.

## Weapons
- weapons are attached to aircraft
- weapons exhaust after use
- exhausted cards are represented visually in the UI
- only refit removes weapon exhaustion unless a specific card effect says otherwise

## Hazards
- only the non-active player may play hazards
- hazard cards define their own legal trigger conditions
- hazards must state what they can respond to
- backend determines whether a hazard is legal in the current trigger window

## Win conditions
A player wins by:
- destroying the opponent's runway
- or destroying all opponent aircraft

## Important restrictions
- UI never determines legal targets
- equipping only happens via refit on the runway
- aircraft that refit cannot launch that turn
- no direct player-to-player freeform communication in matches
- bot matches do not count toward PvP progression or milestone rewards

---

# 3. Architecture Principles

## Backend is source of truth
The backend/rules engine determines:
- legal actions
- legal targets
- trigger windows
- card effect legality
- combat resolution
- win/loss state

The UI only:
- displays state
- sends player intent
- renders legal targets supplied by backend
- renders animations and overlays

Never duplicate gameplay legality in Flutter or web UI.

## Prefer deterministic systems
Rules logic should be:
- testable
- replayable
- event-driven where practical
- stable across web/mobile clients

## Avoid hidden UI-only rules
If the UI needs something like valid targets, highlighted slots, or legal actions, it must come from backend state or backend action response.

---

# 4. UX Principles

## Mobile-first but cross-platform
The game supports:
- web/desktop
- Android
- iOS
with cross-play through the same backend.

## Board layout
Default layout:
- opponent top
- player bottom
- runway and air visible at all times

Phase focus:
- only the active player's side softly expands for the current relevant zone
- non-active player's board must remain fully visible and stable

## Card interaction
- Tap: expand card and show attached child cards when not in targeting mode
- Tap again: collapse
- Tap and hold: full inspect overlay with attached cards
- Entering targeting mode cancels expansion states
- Game state changes should collapse expansions where appropriate

## Targeting UX
When in targeting mode:
- backend supplies legal targets
- UI highlights legal targets
- illegal targets remain visible but de-emphasized
- UI must not guess legality

---

# 5. Gameplay Systems Separation

Keep these concerns separate:

## Core gameplay
- aircraft
- pilots
- weapons
- hazards
- operations
- runway
- combat
- progression hooks

## Expression / monetization
- avatars
- battle cries
- UI themes
- cosmetics
- deck slots
- expansions

Never let cosmetic systems affect match outcomes.

---

# 6. Progression Rules

## PvP progression
Standard and ranked PvP can grant account progression.

## Milestone rewards
Milestone items are earned only.
Never make milestone items purchasable.

## Bot progression
Bot matches do not count toward PvP progression or milestone prestige.
Bots may have their own separate humorous reward pool.

---

# 7. Match Modes

## Standard
- unranked
- used for testing, learning, casual play

## Season / Ranked
- affects leaderboard and rank
- players may still choose standard for deck experimentation

Deck is selected before match start.

---

# 8. Coding Conventions

## General
- prefer small, composable functions
- prefer explicit names over clever names
- avoid duplicated rule logic
- preserve determinism in rules engine
- favor readability over abstraction-for-its-own-sake

## Backend
- keep match rules in the rules engine/domain layer
- transport/controller layers should stay thin
- validate every action server-side
- event/state transitions should be easy to test

## Frontend
- UI state must not become gameplay state
- render from canonical backend state
- keep animations separate from legality
- design for touch first, mouse second

---

# 9. What “Done” Means

A task is not done unless all relevant items are true:

- code compiles
- tests pass
- new logic has targeted tests if it affects rules
- no UI-only legality was introduced
- no backend/client desync risk was added
- naming and files remain consistent
- output is summarized clearly

If you change rules behavior, update:
- tests
- docs/comments where needed
- any schema/types affected
- card effect assumptions if applicable

---

# 10. High-Risk Areas

Be extra careful with:

- target legality
- hazard trigger timing
- refit / launch interaction
- exhaustion / refresh timing
- runway and win-condition resolution
- cross-platform UI state drift
- backend/client mismatch
- progression incorrectly counting bot matches
- milestone rewards accidentally becoming purchasable

---

# 11. Preferred Workflow for Larger Tasks

For non-trivial tasks:
1. inspect relevant files
2. summarize current behavior
3. propose small plan
4. implement in minimal coherent steps
5. run tests/lint
6. summarize changes and any open risks

For tricky gameplay work, plan first before editing.

---

# 12. What Not To Do

Do not:
- invent rules not supported by current design without calling it out
- move legality logic into UI
- create monetization tied to gameplay power
- allow milestone rewards to be bought
- make bot progression count for PvP prestige
- hide important enemy board state during phase focus
- create freeform in-match chat
- introduce unnecessary framework churn

---

# 13. If Unsure

When uncertain:
- preserve current rules intent
- choose simpler implementation
- keep backend authoritative
- avoid clever shortcuts that duplicate logic
- leave a concise note about the uncertainty