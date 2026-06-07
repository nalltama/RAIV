@echo off
setlocal

echo Installing RAIV Python support packages...
echo.

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -m pip install --upgrade pip
    if %errorlevel% neq 0 exit /b %errorlevel%
    py -m pip install PySide6 Pillow py7zr rarfile novelai-sdk==0.9.1
    if %errorlevel% neq 0 exit /b %errorlevel%
    py -m pip install opencv-python-headless
    if %errorlevel% neq 0 echo Optional OpenCV install failed. Lanczos4 will fall back to Lanczos3.
    goto :notice
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python -m pip install --upgrade pip
    if %errorlevel% neq 0 exit /b %errorlevel%
    python -m pip install PySide6 Pillow py7zr rarfile novelai-sdk==0.9.1
    if %errorlevel% neq 0 exit /b %errorlevel%
    python -m pip install opencv-python-headless
    if %errorlevel% neq 0 echo Optional OpenCV install failed. Lanczos4 will fall back to Lanczos3.
    goto :notice
)

echo Python was not found. Install Python first, then run this file again.
pause
exit /b 1

:notice
echo.
echo RAIV support packages were installed.
echo.
echo Installed Python packages:
echo   - PySide6  : application UI
echo   - Pillow   : high quality CPU image resampling
echo   - OpenCV   : optional Lanczos4 resampling support
echo   - py7zr    : 7z/CB7 archive support
echo   - rarfile  : RAR/CBR archive support helper
echo   - novelai-sdk : NovelAI image generation API support
echo.
echo RAR/CBR may also require an external extractor.
echo If RAR files do not open, install one of these separately:
echo   - 7-Zip command line tool: 7z.exe
echo   - UnRAR
echo   - bsdtar
echo.
pause
