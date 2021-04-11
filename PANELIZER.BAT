@echo OFF
REM
REM WRAPPER FOR WINDOWS INCLUDING THE PYTHON PATH FROM KICAD ITSELF
REM
PATH="c:\Program Files\KiCad\bin";%PATH%
echo %~dp0

python %~dp0\panelizer.py %*
