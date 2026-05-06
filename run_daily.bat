@echo off
cd /d D:\PythonProject
call .venv\Scripts\activate
python pipeline/run_pipeline.py --days 1 >> logs\scheduler.log 2>&1