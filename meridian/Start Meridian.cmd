@echo off
rem Double-click to open Meridian. Uses the project environment in .venv (see README).
start "" "%~dp0.venv\Scripts\pythonw.exe" -m meridian.app
