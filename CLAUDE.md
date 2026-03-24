# CLAUDE.md
## Project: Tactical Air Combat Card Game
## Platforms: Web, iOS, Android (Cross-play)

---

# CORE DESIGN PRINCIPLES

1. No Pay-to-Win
All gameplay-affecting elements are earned or included in core products.
Monetization is strictly:
- cosmetics
- convenience (deck slots)
- expansions

2. Skill is Visible and Earned
Milestone rewards are NEVER purchasable.
Prestige reflects skill and achievement only.

3. Optional Competitive Intensity
Players choose between casual and ranked play.

4. Premium Tactical Tone
PvP is serious and clean.
PvE may be slightly humorous.

---

# CORE GAME SYSTEMS

## Zones
- Runway (Ground Zone)
- Air Zone

## Turn Structure (Per Player)
1. Command Phase
   - Play Operations (CP-based)

2. Ground Phase
   - Refit (equip + refuel)
   - Deploy aircraft to runway
   - Aircraft remain grounded

3. Air Phase
   - Launch aircraft
   - Move + attack OR attack + move
   - One attack per aircraft

4. End Phase

Players complete all phases before switching turns.

---

# COMBAT SYSTEM

Attack Resolution:
d6 + ATK vs EVD

ATK/EVD derived from:
- aircraft
- pilot
- equipment

Damage is defined by weapon cards.
No outcome table (initial design).

---

# AIRCRAFT SYSTEM

- Structure Rating (SR) = HP
- SR based on aircraft class
- Hard caps per class
- Can only be modified by equipment

Rules:
- Must launch to enter air
- One attack per turn
- Cannot act while on runway

---

# REFIT SYSTEM

Occurs during Ground Phase.

Includes:
- equipping weapons
- refueling
- removing exhaustion

Rule:
- Aircraft that refit cannot launch that turn

---

# EXHAUST SYSTEM

- Cards flipped face down are Exhausted
- Exhausted cards:
  - occupy space
  - cannot act
  - cannot be targeted

Refitting removes exhaustion.

---

# CARD TYPES

## Aircraft
Core units with SR, ATK, EVD

## Pilots
Attached to aircraft
Modify stats and behavior

## Weapons
Equipped during refit
Provide attack capability
Exhaust after use

## Operations
Played during Command Phase
Cost CP

## Hazards
Played by non-active player only
Must specify trigger conditions

Example:
Sabotage → discard weapon when equipped

---

# WIN CONDITIONS

- Destroy opponent runway
OR
- Destroy all opponent aircraft

---

# DECK SYSTEM

## Deck Library
- 5 custom decks
- 2–3 default decks

## Rules
- Deck selected before match
- Locked during match

Future:
- deck sharing codes
- deck statistics

---

# PROGRESSION SYSTEM

## Career Progression
XP earned from:
- matches
- wins
- objectives

## Achievements (Milestones)
Skill-based unlocks only

Rewards:
- avatars
- battle cries
- titles
- frames

## Mastery Tracks
Per aircraft progression

---

# CRITICAL RULE

Milestone rewards are NEVER purchasable.

---

# PVE (BOT MODE)

- Does not impact PvP progression
- Separate reward pool
- Allows humorous tone

Purpose:
- learning
- testing
- low-pressure play

---

# SEASON SYSTEM

- 3-month cadence
- Optional participation

Modes:
- Standard (casual)
- Season (ranked)

Ranked includes:
- leaderboard
- seasonal rewards

No resets of progression.

---

# COSMETIC SYSTEM

## Avatars
- free
- premium (paid)
- milestone (earned only)

## Battle Cries
- preset phrases only
- rate-limited
- no free text

---

# MATCH TYPES

## Standard
- no rank impact
- used for testing and casual play

## Ranked
- affects leaderboard
- competitive environment

---

# UI / UX

- Split screen layout (player bottom, opponent top)
- Active phase expands zone (ground/air)
- Tap + hold → card overlay
- Tap → expand children cards
- Backend defines valid targets
- UI highlights them

---

# COMMUNICATION

MVP:
- no communication

Future:
- battle cries only

---

# TECH STACK

Frontend:
- React (Web)
- Flutter (Mobile)

Backend:
- FastAPI

Data:
- JSON format

Architecture:
- server authoritative
- backend validates all actions

Crossplay supported.

---

# ROADMAP

Phase 1: Core gameplay MVP
Phase 2: Multiplayer backend
Phase 3: Progression and cosmetics
Phase 4: PvE system
Phase 5: Ranked and seasons
Phase 6: Monetization and expansions

---

# FINAL POSITIONING

A tactical, skill-driven card game with optional competition, zero pay-to-win, and strong identity systems built on earned prestige and controlled expression.
