# pnfl-gameplanwriter — Status

**Status: Complete**

Updates the normal-play and/or custom special-teams slots of a Front Page Sports Football Pro '98 gameplan (`.pln`) file from plain-text input.

## Implemented

- CLI `write-gameplan`, distributed via the `pnfl` umbrella, with `--normal-plays`, `--special-plays`, `--config`, and `--play-path` options
- Reads play sources from a file path or stdin (`-`), including the shared-source mode where one source feeds both sections
- Resolves play names against the play pool via `pnfl-playpool` and writes the binary `.pln` via `fbpro98-gameplan`
- `PnflGamePlan` binding at load time (the writer holds a `PnflRules` and constructs a `PnflGamePlan` inside `write()`); aggregate-rule validation is opt-in at the call site via `PnflGamePlan.save()`
- Positional 64-line normal section and self-slotting 10-line custom special section, with unsupplied slots cleared
- Validation: line-count limits, play side vs. gameplan profile, normal/special section mismatch, and duplicate detection — per-line violations are collected and raised together as `InvalidPlayInputError`; the target `.pln` is not written when any violation is found
- Config file lookup with `.dev.ini` precedence and a `--play-path` override
- Stock special-teams plays and clock plays preserved untouched

## Remaining

- Nothing outstanding for the current scope.
