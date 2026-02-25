@echo off
REM Complete re-run of all 4 schemes with extended load range
REM Load: 0-1000 (step 100), 5 runs per point = 55 runs per scheme

echo ============================================================
echo Complete Re-run: All 4 Schemes (Extended Load Range)
echo ============================================================
echo Load range: 0-1000 (step 100)
echo Runs per load: 5
echo Total runs per scheme: 55
echo Total runs: 220
echo ============================================================
echo.

REM UCM
echo [1/4] Running UCM...
python scripts/runner_ucm.py --min_load 0 --max_load 1000 --step 100 --runs 5 --output results/ucm_logs_extended.csv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: UCM failed
    exit /b 1
)

REM RCM
echo.
echo [2/4] Running RCM...
python scripts/runner_rcm.py --min_load 0 --max_load 1000 --step 100 --runs 5 --output results/rcm_logs_extended.csv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: RCM failed
    exit /b 1
)

REM SCM
echo.
echo [3/4] Running SCM...
python scripts/runner_scm.py --min_load 0 --max_load 1000 --step 100 --runs 5 --output results/scm_logs_extended.csv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: SCM failed
    exit /b 1
)

REM PCM
echo.
echo [4/4] Running PCM...
python scripts/runner_pcm.py --min_load 0 --max_load 1000 --step 100 --runs 5 --output results/pcm_logs_extended.csv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PCM failed
    exit /b 1
)

echo.
echo ============================================================
echo All experiments completed!
echo ============================================================
echo Output files:
echo   - results/ucm_logs_extended.csv
echo   - results/rcm_logs_extended.csv
echo   - results/scm_logs_extended.csv
echo   - results/pcm_logs_extended.csv
echo ============================================================
pause
