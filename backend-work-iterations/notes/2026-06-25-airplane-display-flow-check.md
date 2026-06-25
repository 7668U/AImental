# 2026-06-25 Airplane Display Flow Check

## What I Checked

I reviewed the paper airplane frontend and backend flow after clearing the history table.

## Findings

- The frontend page fetches `/airplane/available` when it loads.
- After a pickup or a new throw, it fetches `/airplane/available?limit=1` and appends one airplane to the page.
- The backend availability query still excludes the current user's own airplanes.
- The backend default limit for available airplanes remains in place.
- The active history reset worked because `user_picked_airplanes` was cleared.

## Implication

The reset is done. If the desired product behavior later becomes "show all airplanes at once" or "also show self-posted airplanes," that will require an API and frontend behavior change, not just a database cleanup.
