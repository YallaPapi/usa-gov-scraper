@echo off
echo ============================================================
echo         USA.gov Agency Index Scraper - Desktop App
echo              Botasaurus + Agency Swarm Edition
echo ============================================================
echo.
echo Starting desktop application...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if dependencies are installed
echo Checking dependencies...
pip show botasaurus >nul 2>&1
if errorlevel 1 (
    echo Installing botasaurus...
    pip install botasaurus
)

pip show agency-swarm >nul 2>&1
if errorlevel 1 (
    echo Installing agency-swarm...
    pip install agency-swarm
)

pip show pandas >nul 2>&1
if errorlevel 1 (
    echo Installing pandas...
    pip install pandas
)

echo.
echo Launching USA.gov Agency Scraper Desktop Application...
echo --------------------------------------------------------
echo.

REM Run the desktop app
python desktop_app.py

echo.
echo ============================================================
echo Application closed. Press any key to exit...
pause >nul