# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Renamed project and package from `fbpro98-gameplanwriter` / `fbpro98_gameplanwriter` to `pnfl-gameplanwriter` / `pnfl_gameplanwriter`. The `pnfl write-gameplan` CLI command name is unchanged.
- `GamePlanWriter` now loads the target via `PnflGamePlan.from_file` (binding the loaded gameplan to a `PnflRules` and the play pool). New `rules: PnflRules = PNFL_RULES` keyword argument on `__init__` / `from_config`. The write path itself remains `write_gameplan` for backward compatibility — PNFL aggregate-rule validation is opt-in at the call site via `PnflGamePlan.save()`.

## [0.1.0] - 2026-05-23

### Added
- Initial gameplan writer with play validation and CLI.
- Typed `PlayRecord` subclasses with enums for play classification.
- Offense gameplan tests; restructured test fixtures.
- CLI main and `from_config` tests.
- Support for custom special plays and stdout output.
- `pnfl.commands` entry point for the umbrella CLI.
- Expanded `write-gameplan --help` and release launcher.
- Collected input violations raised as `InvalidPlayInputError`.
- STATUS.md and TEST_STATUS.md documentation.
- Line-ending rules in .editorconfig.

### Changed
- Refactored with dependency injection; renamed `PlayPath`; fixed config handling.
- Migrated to the `pnfl` umbrella CLI and new gameplan API.
- Replaced section markers with positional play-list parsing.
- Renamed `special_flag` to `special_category`.
- Use the shared `pnfl` CLI logger.
- Standardized project tooling config.

### Fixed
- S98 pad to even (offense) or odd (defense) file length in tests.

### Removed
- `sys.path` hacks from conftest files in favor of editable installs.
