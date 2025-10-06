@echo off
setlocal
set ASTROENGINE_API=http://127.0.0.1:8000
set STREAMLIT_SERVER_HEADLESS=true
set STREAMLIT_BROWSER_GATHERUSAGESTATS=false

REM Optional: set ephemeris path if known
REM set SE_EPHE_PATH=D:\Ephemeris

start "AstroEngine API+UI" "AstroEngine.exe"
