# fbpro98-gameplanwriter
`fbpro98-gameplanwriter` updates the 64 normal-play slots in a Front Page Sports
Football Pro '98 gameplan (`.pln`) file from a text file of play names.
It uses `pnfl-playpool` to resolve play names to file paths and `fbpro98-gameplan`
to read and write the binary `.pln` format. Special and stock-special plays are
preserved untouched. Offensive/defensive play types are validated against the
gameplan's profile type.
## Setup
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ..\fbpro98-play
pip install -e ..\fbpro98-gameplan
pip install -e ..\pnfl-playpool
pip install -e ".[dev]"
```
## Usage
```bash
fbpro98-gameplanwriter offense.pln plays.txt --pnfl-path E:\SIERRA\FbPro98\PNFL
```
Or via module:
```bash
python -m fbpro98_gameplanwriter offense.pln plays.txt --pnfl-path E:\SIERRA\FbPro98\PNFL
```
`--pnfl-path` overrides the config file. Without it, the PNFL path is read from
`config/gameplan_writer.ini` or falls back to `C:\SIERRA\FbPro98\PNFL`.
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
- special/stock-special plays preserved after write
- case-insensitive play name resolution
- defensive play in offensive gameplan skipped with warning
- offensive play in defensive gameplan skipped with warning
- defensive plays write correctly to defensive gameplan
