# fbpro98-gameplanwriter

Updates the normal-play slots and/or custom special-teams slots in a Front Page Sports Football Pro '98 gameplan (`.pln`) file from text input. Uses `pnfl-playpool` to resolve play names to file paths and `fbpro98-gameplan` to read and write the binary `.pln` format. Stock special-teams plays and clock plays are preserved untouched. Offensive/defensive play types are validated against the gameplan's profile type.

## Setup

```bash
py -3.13 -m venv .venv
.venv\Scripts\activate
py -m pip install -e ..\fbpro98-play
py -m pip install -e ..\fbpro98-gameplan
py -m pip install -e ..\pnfl-playpool
py -m pip install -e ".[dev]"
```

## Usage

Distributed via the [`pnfl`](../pnfl) umbrella CLI:

```bash
pnfl write-gameplan dest.pln --normal-plays plays.txt
pnfl write-gameplan dest.pln --special-plays specials.txt
pnfl write-gameplan dest.pln --normal-plays plays.txt --special-plays specials.txt
pnfl write-gameplan dest.pln --normal-plays - --special-plays - --play-path E:\SIERRA\FbPro98\PNFL
```

At least one of `--normal-plays` or `--special-plays` is required. A section that isn't supplied is left untouched in the gameplan.

`--play-path` overrides the config file. Without it, the play path is read from the first config found, or falls back to `C:\SIERRA\FbPro98\PNFL`.

Config lookup order (first match wins; `.dev.ini` variants take precedence at each level):

1. `write-gameplan.dev.ini` / `write-gameplan.ini` in the current working directory
2. `config/write-gameplan.dev.ini` / `config/write-gameplan.ini` under the current working directory

### Input format

Each source is a plain text file (or stdin via `-`), one play name per line:

- Blank lines mean the slot is empty
- Play names are case-insensitive
- Unknown play names are skipped with a warning
- Plays of the wrong side (defensive in offensive gameplan, etc.) are skipped with a warning

**Per-flag sources:**
- `--normal-plays SOURCE` — up to **64 lines**. Line N goes to slot N. Trailing slots beyond the input are cleared. Over-max raises an error.
- `--special-plays SOURCE` — up to **10 lines**. Each play self-slots by its own `special_category`; line position doesn't matter. Categories not represented are cleared.

**Shared source** (same path or `-` passed to both flags) — must contain **exactly 74 lines**: lines 0-63 are dispatched to the normal section, lines 64-73 to the special section. This is the contract the reader's headerless `--normal-out - --special-out -` mode produces, so the two CLIs pipe cleanly:

```bash
pnfl read-gameplan src.pln --normal-out - --special-out - | pnfl write-gameplan dest.pln --normal-plays - --special-plays -
```

The reader's default-mode stdout (with `=== Normal ===` / `=== Special ===` headers) is for human reading and is **not** consumable by the writer.

### Example normal plays.txt

```
OR45RL01
OR10RLRG

SF35Hevy
OR36RL01
```

Slot 2 (the blank line) would be empty in the gameplan; slots 4-63 stay empty.

## Building a Release

This project is distributed as part of the [`pnfl`](../pnfl) umbrella CLI. See `pnfl/scripts/build_release.py` for release packaging.

## Testing

```bash
pytest
```

Cross-CLI pipeline tests (`read-gameplan` → `write-gameplan`) live in [`pnfl/tests/test_pipeline.py`](../pnfl/tests/test_pipeline.py).
