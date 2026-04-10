#!/bin/bash
# Linux/Mac离线模式启动脚本

echo "============================================================"
echo "启动离线模式"
echo "============================================================"

# 设置离线模式环境变量
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export HF_HUB_OFFLINE=1
export CURL_CA_BUNDLE=""
export REQUESTS_CA_BUNDLE=""
export HTTP_PROXY=""
export HTTPS_PROXY=""
export http_proxy=""
export https_proxy=""

echo "✓ 离线模式环境变量已设置"
echo "============================================================"

# 启动服务
python app_full.py
