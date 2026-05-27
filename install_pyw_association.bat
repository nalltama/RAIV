@echo off
setlocal

for /f "delims=" %%P in ('where pyw 2^>nul') do (
    set "PYW_EXE=%%P"
    goto :found_pyw
)

echo pyw.exe was not found.
echo Install Python or enable Python Install Manager / Python Launcher, then run this file again.
pause
exit /b 1

:found_pyw
echo Found pyw.exe:
echo %PYW_EXE%
echo.
echo This will associate .pyw files with pyw.exe for the current Windows user.
echo Administrator permission is not required.
echo.

set "OPEN_COMMAND="%PYW_EXE%" "%%1" %%*"

if /i "%~1"=="--dry-run" (
    echo Registry open command:
    echo %OPEN_COMMAND%
    exit /b 0
)

reg add "HKCU\Software\Classes\.pyw" /ve /d "RAIV.Python.NoConsole" /f >nul
if errorlevel 1 goto :failed

reg add "HKCU\Software\Classes\RAIV.Python.NoConsole" /ve /d "Python GUI script" /f >nul
if errorlevel 1 goto :failed

reg add "HKCU\Software\Classes\RAIV.Python.NoConsole\shell\open\command" /ve /d "%OPEN_COMMAND%" /f >nul
if errorlevel 1 goto :failed

echo.
echo .pyw association has been configured successfully.
echo You can now double-click run_raiv.pyw to launch RAIV without a command window.
pause
exit /b 0

:failed
echo.
echo Failed to configure .pyw association.
pause
exit /b 1
