@ECHO OFF
cd /d "%~dp0"

:: ===================================================================
:: Edit the paths below to match your setup, then double-click to run.
:: This updates a game plan (.pln) using a play list text file.
:: The play list is one play name per line; blank lines = empty slots.
:: ===================================================================

SET GAMEPLAN_FILE=C:\PATH\TO\GAMEPLAN.pln
SET PLAYS_FILE=C:\PATH\TO\PLAYS.txt

pnfl write-gameplan "%GAMEPLAN_FILE%" "%PLAYS_FILE%"

pause
