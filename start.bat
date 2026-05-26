@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Endfield Gacha Server Launcher

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PORT=5000"
set "MODE=prod"
set "SYNC=1"
set "RUNNER=auto"
set "CHECK_ONLY=0"

if "%~1"=="" goto args_done

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--help" goto usage
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--dev" (
    set "MODE=dev"
    shift
    goto parse_args
)
if /I "%~1"=="--no-sync" (
    set "SYNC=0"
    shift
    goto parse_args
)
if /I "%~1"=="--check" (
    set "CHECK_ONLY=1"
    shift
    goto parse_args
)
if /I "%~1"=="--python" (
    set "RUNNER=python"
    shift
    goto parse_args
)
if /I "%~1"=="--uv" (
    set "RUNNER=uv"
    shift
    goto parse_args
)
if /I "%~1"=="--port" (
    if "%~2"=="" (
        echo [ERROR] --port requires a value
        goto usage_error
    )
    set "PORT=%~2"
    shift
    shift
    goto parse_args
)
echo [ERROR] Unknown argument: %~1
goto usage_error

:args_done
call :print_banner

if not exist "server.py" (
    echo [ERROR] server.py not found. Run this script from project root.
    exit /b 1
)
if not exist "pyproject.toml" (
    echo [ERROR] pyproject.toml not found. Project layout looks incomplete.
    exit /b 1
)

call :check_command uv HAS_UV
call :check_command python HAS_PY

if /I "%RUNNER%"=="uv" if "%HAS_UV%"=="0" (
    echo [ERROR] --uv is set, but uv command is not available.
    exit /b 1
)
if /I "%RUNNER%"=="python" if "%HAS_PY%"=="0" (
    echo [ERROR] --python is set, but python command is not available.
    exit /b 1
)
if /I "%RUNNER%"=="auto" (
    if "%HAS_UV%"=="1" (
        set "RUNNER=uv"
    ) else (
        if "%HAS_PY%"=="1" (
            set "RUNNER=python"
        ) else (
            echo [ERROR] Neither uv nor python command is available.
            exit /b 1
        )
    )
)

if not "%PORT%"=="" (
    echo %PORT%| findstr /R "^[0-9][0-9]*$" >nul
    if errorlevel 1 (
        echo [ERROR] Port must be a positive integer. Current value: %PORT%
        exit /b 1
    )
)

call :is_port_in_use %PORT%
if "!PORT_IN_USE!"=="1" (
    echo [WARN ] Port %PORT% is in use. Trying to find a free port...
    call :find_free_port %PORT% 20
    if not defined FOUND_PORT (
        echo [ERROR] No free port found in range %PORT% to %PORT%+20. Use --port.
        exit /b 1
    )
    echo [INFO ] Switched to free port !FOUND_PORT!
    set "PORT=!FOUND_PORT!"
)

if /I "%RUNNER%"=="uv" if "%SYNC%"=="1" (
    echo [STEP ] Syncing dependencies: uv sync --frozen
    uv sync --frozen
    if errorlevel 1 (
        echo [WARN ] uv sync --frozen failed. Trying uv sync...
        uv sync
        if errorlevel 1 (
            echo [ERROR] Dependency sync failed. Check network and Python setup.
            exit /b 1
        )
    )
)

if /I "%RUNNER%"=="python" (
    echo [STEP ] Checking Python dependencies: flask and waitress...
    python -c "import flask, waitress" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Missing flask/waitress. Run: uv sync
        exit /b 1
    )
)

set "SERVER_ARGS=--port %PORT%"
if /I "%MODE%"=="prod" set "SERVER_ARGS=--waitress --port %PORT%"
if /I "%MODE%"=="dev" set "SERVER_ARGS=--dev --port %PORT%"

echo [INFO ] Workdir: %ROOT%
echo [INFO ] Runner : %RUNNER%
echo [INFO ] Mode   : %MODE%
echo [INFO ] URL    : http://127.0.0.1:%PORT%
echo.

if "%CHECK_ONLY%"=="1" (
    echo [OK   ] Checks passed for --check. Server was not started.
    exit /b 0
)

echo [STEP ] Starting server. Press Ctrl+C to stop.
if /I "%RUNNER%"=="uv" (
    uv run python server.py %SERVER_ARGS%
    set "EXIT_CODE=!ERRORLEVEL!"
    if not "!EXIT_CODE!"=="0" (
        if "%HAS_PY%"=="1" (
            echo [WARN ] uv launch failed. Trying python directly...
            python server.py %SERVER_ARGS%
            set "EXIT_CODE=!ERRORLEVEL!"
        )
    )
) else (
    python server.py %SERVER_ARGS%
    set "EXIT_CODE=!ERRORLEVEL!"
)

if not "!EXIT_CODE!"=="0" (
    echo [ERROR] Server exited with code: !EXIT_CODE!
    exit /b !EXIT_CODE!
)

echo [OK   ] Server exited.
exit /b 0

:check_command
where %~1 >nul 2>&1
if errorlevel 1 (
    set "%~2=0"
) else (
    set "%~2=1"
)
exit /b 0

:is_port_in_use
set "PORT_IN_USE=0"
for /f "delims=" %%L in ('netstat -ano ^| findstr /R /C:":%~1 .*LISTENING"') do (
    set "PORT_IN_USE=1"
    goto :port_done
)
:port_done
exit /b 0

:find_free_port
set "FOUND_PORT="
set /a "__START=%~1"
set /a "__END=__START+%~2"
for /l %%P in (!__START!,1,!__END!) do (
    call :is_port_in_use %%P
    if "!PORT_IN_USE!"=="0" (
        set "FOUND_PORT=%%P"
        goto :find_done
    )
)
:find_done
exit /b 0

:usage
echo.
echo Usage: start.bat [options]
echo.
echo Options:
echo   --help, -h      Show help
echo   --dev           Dev mode (Flask debug, skip static compression)
echo   --port N        Set port (default: 5000)
echo   --no-sync       Skip uv dependency sync
echo   --uv            Force uv runner
echo   --python        Force python runner
echo   --check         Checks only, do not start server
echo.
echo Examples:
echo   start.bat
echo   start.bat --dev --port 5001
echo   start.bat --check
exit /b 0

:usage_error
call :usage
exit /b 1

:print_banner
echo.
echo ==========================================
echo   Endfield Gacha Server Launcher
echo ==========================================
echo.
exit /b 0
