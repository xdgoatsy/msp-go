@echo off
chcp 65001 >nul
title MathStudyPlatform - 一键启动

echo ========================================
echo   高等数学智能学习平台 - 一键启动
echo ========================================
echo.

:: 启动后端 (新窗口)
echo [1/2] 启动后端服务...
start "Backend - FastAPI" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 等待一秒让后端先启动
timeout /t 2 /nobreak >nul

:: 启动前端 (新窗口)
echo [2/2] 启动前端服务...
start "Frontend - Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   启动完成!
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   API:  http://localhost:8000/api/v1/docs
echo ========================================
echo.
echo 关闭此窗口不会影响已启动的服务。
echo 要停止服务，请关闭对应的命令行窗口。
pause
