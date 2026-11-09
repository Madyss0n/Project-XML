@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0" || exit /b 1
title XML Validator
:menu
cls
echo(
echo  ^|   ^|   ^|     ^|^|       ^|^|^|^|^|  ^|^|^|^|^|     ^|     ^|^|^|^|^|^| ^|^|^|^|^|^|  ^|^|^|^|^|^|
echo  ^|   ^|  ^| ^|    ^|^|         ^|    ^|^|  ^|    ^| ^|      ^|^|   ^|^|  ^|^|  ^|^|  ^|^|
echo   ^| ^|  ^|^|^|^|^|   ^|^|         ^|    ^|^|  ^|   ^|^|^|^|^|     ^|^|   ^|^|  ^|^|  ^|^|^|^|^|
echo    ^|  ^|     ^|  ^|^|^|^|^|^|   ^|^|^|^|^|  ^|^|^|^|^|  ^|     ^|    ^|^|   ^|^|^|^|^|^|  ^|^|   ^|^|
echo(
echo  1. Start web validator
echo  2. Open project folder
echo  3. Install requirements
echo  4. Stop processes listening on port 5000
echo  0. Exit
:select
set "menu_input="
set /p "menu_input=Select: "
if "!menu_input!"=="0" exit /b 0
if "!menu_input!"=="1" goto launch
if "!menu_input!"=="2" goto folder
if "!menu_input!"=="3" goto install
if "!menu_input!"=="4" goto stop_port
echo Invalid choice. Enter 0, 1, 2, 3 or 4.
goto select

:stop_port
setlocal
set "listeners="
for /f "tokens=2,4,5" %%A in ('netstat -ano -p tcp') do (
    set "endpoint=%%A"
    if "!endpoint:~-5!"==":5000" if "%%B"=="LISTENING" (
        if %%C GTR 4 if not defined seen_%%C (
            set "seen_%%C=1"
            set "listeners=!listeners! %%C"
            tasklist /fi "PID eq %%C" /nh
        )
    )
)
if not defined listeners (
    echo No stoppable process is listening on port 5000.
    goto stop_port_done
)
echo This will forcibly stop the listed processes.
set "confirm_stop="
set /p "confirm_stop=Type Y and press Enter to continue: "
if /i not "!confirm_stop!"=="Y" goto stop_port_done
for %%P in (!listeners!) do (
    set "still_listening="
    for /f "tokens=2,4,5" %%A in ('netstat -ano -p tcp') do (
        set "endpoint=%%A"
        if "!endpoint:~-5!"==":5000" if "%%B"=="LISTENING" if "%%C"=="%%P" set "still_listening=1"
    )
    if defined still_listening taskkill /PID %%P /F
)
:stop_port_done
endlocal
pause
goto menu

:folder
start "" explorer.exe "%CD%"
goto menu

:launch
call :environment
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import flask, lxml.etree" >nul 2>&1
if errorlevel 1 (
    call :requirements
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" main.py --browser
pause
goto menu

:install
call :environment
if errorlevel 1 goto failed
call :requirements
if errorlevel 1 goto failed
pause
goto menu

:environment
if exist ".venv\Scripts\python.exe" exit /b 0
where py.exe >nul 2>&1
if errorlevel 1 (
    python -m venv .venv
) else (
    py -3 -m venv .venv
)
exit /b %errorlevel%

:requirements
".venv\Scripts\python.exe" -m pip install -r requirements.txt
exit /b %errorlevel%

:failed
echo Setup failed. See the message above.
pause
goto menu
