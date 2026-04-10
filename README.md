# fbpro98-gameplanwriter

Updates the 64 normal-play slots in a Front Page Sports Football Pro '98 gameplan (`.pln`) file
from a text file of play names. Uses `pnfl-playpool` to resolve play names to file paths and
`fbpro98-gameplan` to read and write the binary `.pln` format. Special-teams and clock plays are
preserved untouched. Offensive/defensive play types are validated against the gameplan's profile
type.

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
pnfl write-gameplan offense.pln plays.txt --play-path E:\SIERRA\FbPro98\PNFL
```

Or via module:

```bash
py -m fbpro98_gameplanwriter offense.pln plays.txt --play-path E:\SIERRA\FbPro98\PNFL
```

`--play-path` overrides the config file. Without it, the play path is read from
the first config found, or falls back to `C:\SIERRA\FbPro98\PNFL`.

Config lookup order (first match wins; `.dev.ini` variants take precedence at each level):

1. `write-gameplan.dev.ini` / `write-gameplan.ini` in the current working directory
2. `config/write-gameplan.dev.ini` / `config/write-gameplan.ini` at the project root
3. `src/fbpro98_gameplanwriter/write-gameplan.dev.ini` / `src/fbpro98_gameplanwriter/write-gameplan.ini`

### Input format

The plays text file has one play name per line:

- Blank lines mean the slot is empty
- If fewer than 64 lines, remaining slots are emptied
- If more than 64 lines, only the first 64 are used
- Play names are case-insensitive
- Unknown play names are skipped with a warning
- Defensive plays in an offensive gameplan (and vice versa) are skipped with a warning

### Example plays.txt

```
OR45RL01
OR10RLRG

SF35Hevy
OR36RL01
```

Slot 3 (the blank line) would be empty in the gameplan.

## Building a Release

This project is distributed as part of the [`pnfl`](../pnfl) umbrella CLI.
See `pnfl/scripts/build_release.py` for release packaging.

## Testing

```bash
pytest
```

Current tests cover:

- writing plays from a text file and reading them back
- blank lines produce empty slots
- more than 64 lines truncated to 64
- fewer than 64 lines pad remaining slots as empty
- unknown play name skipped with warning
- special-teams plays preserved after write
- case-insensitive play name resolution
- defensive play in offensive gameplan skipped with warning
- offensive play in defensive gameplan skipped with warning
- defensive plays write correctly to defensive gameplan
