# fbpro98-gameplanwriter — Architecture

CLI tool that updates the normal and/or custom-special slots of an existing `.pln` from text input.

For system-level context, see [pnfl-docs/Design/gameplan-architecture.md](../pnfl-docs/Design/gameplan-architecture.md).

For validation ownership, see [pnfl-docs/Design/gameplan-validation.md](../pnfl-docs/Design/gameplan-validation.md).

## Module layout

```
src/fbpro98_gameplanwriter/
├── __init__.py
├── cli.py                 # argparse + main()
├── main.py                # update_gameplan(), source-loading helpers
├── gameplan_writer.py     # GamePlanWriter class, apply_*_plays methods
└── config.py              # Config dataclass, load_config()
```

## What this package does

- Provides a CLI: `pnfl write-gameplan DEST.pln [--normal-plays SOURCE] [--special-plays SOURCE] [--config FILE] [--play-path DIR]`
- Reads `--normal-plays` / `--special-plays` from a file path or `-` (stdin)
- Loads the play pool via `pnfl-playpool.read_play_pool()`
- Resolves each input line to a typed play record from the pool
- Reads the existing target `.pln`, applies the requested updates, writes back
- Logs warnings for skipped lines (unknown play, wrong side, duplicate, etc.) and continues

## What this package assumes

- The target `.pln` is well-formed; failure to parse raises `InvalidGamePlanError` from the underlying library
- The play pool root contains valid `.ply` files; failure to scan raises errors from `pnfl-playpool`
- A `--normal-plays` source of `N < 64` lines means "first N slots get these plays, slots N..63 are cleared." Likewise `--special-plays` with `N < 10` clears the unfilled categories.

## What this package enforces

CLI-level (raise SystemExit):
- `gameplan_path` provided
- At least one of `--normal-plays` / `--special-plays` provided

Source-level (raise `ValueError`):
- Shared source (same path/`-` for both flags) has exactly 74 lines
- `--normal-plays` source has ≤ 64 lines
- `--special-plays` source has ≤ 10 lines

Per-line (warn and skip; never abort the write):
- Unknown play name → skip
- Play side mismatches gameplan profile → skip
- Special-teams play in normal section → skip
- Normal play in special section → skip
- Duplicate play name in normal section → skip
- Duplicate play name in special section → skip
- Two custom specials targeting the same `special_category` → skip second

## What this package does NOT do

- Parse `.pln` bytes (delegates to `fbpro98-gameplan`)
- Validate model-level invariants (delegated to `GamePlan.__post_init__` via `with_normal_plays` / `with_custom_special_plays`)
- Parse `.ply` files (delegated transitively via `pnfl-playpool` → `fbpro98-play`)
- Modify the play pool

## Input contract

Input is positional and headerless. Line N of `--normal-plays` corresponds to slot N. Line N of `--special-plays` corresponds to `special_category` N+1 — but each play self-slots by its own `special_category`, so the line position is informational, not authoritative.

Compatible with `fbpro98-gameplanreader`'s headerless modes:
- `pnfl read-gameplan src.pln --normal-out - | pnfl write-gameplan dst.pln --normal-plays -`
- `pnfl read-gameplan src.pln --normal-out - --special-out - | pnfl write-gameplan dst.pln --normal-plays - --special-plays -`

The reader's default-mode (with-headers) output is **not** compatible with the writer.

## Testing

- `tests/test_gameplan_writer.py` — `GamePlanWriter.apply_normal_plays` / `apply_special_plays` semantics, with byte-compare against game-produced expected `.pln` files in `tests/data/expected/`
- `tests/test_cli.py` — argparse contract, source dispatch (file/stdin/shared), config wiring

The expected `.pln` fixtures are produced by FbPro '98 itself and are the authoritative ground truth — any test that writes bytes ultimately compares to one of these.
