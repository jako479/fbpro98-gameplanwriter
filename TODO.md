# TODO

## Pipeline support: read play list from stdin

Allow `-` in place of the `plays` positional so output from `pnfl read-gameplan` can be piped directly in.

How:
- When `args.plays == "-"`, read from `sys.stdin` instead of `Path(plays).read_text()` in `write_from_play_list()`.

## Special-teams update mode

Today the writer preserves special-teams slots (64–83) untouched. Add the ability to update them from a play list, so a coach can refresh just special teams without touching normal plays.

How:
- New flag (e.g. `--special-plays FILE` or a separate subcommand like `pnfl write-special-teams`) that takes a play list targeting the 20 special-teams slots.
- Reuse the existing play-list parsing; route entries to the special-teams slot range instead of the normal-plays range.
- Keep the current default behavior (normal plays only) unchanged.
