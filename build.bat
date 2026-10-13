@echo off
setlocal
pushd "%~dp0" || exit /b 1
echo ===================================================
echo   File Organizer Pro - verified native build
echo ===================================================
if defined FILE_ORGANIZER_PYTHON goto custom_python
if exist ".venv\Scripts\python.exe" goto project_python
where py >nul 2>nul
if not errorlevel 1 goto python_launcher
where python >nul 2>nul
if not errorlevel 1 goto path_python
echo ERROR: Install Python 3.10 or newer with Tcl/Tk and pip, then run this file again.
set "BUILD_EXIT=1"
goto finish
:custom_python
"%FILE_ORGANIZER_PYTHON%" scripts\bootstrap_build.py %*
goto result
:project_python
".venv\Scripts\python.exe" scripts\bootstrap_build.py %*
goto result
:python_launcher
py -3 scripts\bootstrap_build.py %*
goto result
:path_python
python scripts\bootstrap_build.py %*
:result
set "BUILD_EXIT=%ERRORLEVEL%"
if not "%BUILD_EXIT%"=="0" echo Build failed. Read the error above; no success was reported.
:finish
popd
if not defined CI if not defined FILE_ORGANIZER_NO_PAUSE pause
exit /b %BUILD_EXIT%
