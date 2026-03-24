# A.C.E.S. Backend

Minimal FastAPI backend skeleton for the A.C.E.S. tactical air combat card game.

This backend is intentionally rules-authoritative:
- clients send action intent only
- legality and target validation belong to backend services
- match state snapshots come from canonical backend models

## Layout

- `src/aces_backend/domain`: match, phase, and player placeholders
- `src/aces_backend/rules`: legality and target validation stubs
- `src/aces_backend/api`: HTTP routes and response contracts
- `../tests`: backend tests

## Run

```bash
cd backend/app
python -m uvicorn aces_backend.main:app --reload
```

## Test

```bash
cd backend/app
pytest
```
