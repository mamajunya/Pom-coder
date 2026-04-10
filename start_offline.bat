@echo off
REM Windows离线模式启动脚本

echo ============================================================
echo 启动离线模式
echo ============================================================

REM 设置离线模式环境变量
set TRANSFORMERS_OFFLINE=1
set HF_DATASETS_OFFLINE=1
set HF_HUB_OFFLINE=1
set CURL_CA_BUNDLE=
set REQUESTS_CA_BUNDLE=
set HTTP_PROXY=
set HTTPS_PROXY=

echo 离线模式环境变量已设置
echo ============================================================

REM 启动服务
python app_full.py

pause
