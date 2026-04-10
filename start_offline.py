#!/usr/bin/env python
"""
离线模式启动脚本

在启动主程序前设置所有必要的环境变量，确保完全离线运行
"""

import os
import sys

# ✅ 设置离线模式环境变量（在导入任何其他模块之前）
print("=" * 60)
print("启动离线模式")
print("=" * 60)

# Hugging Face离线模式
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

# 禁用SSL验证（避免网络检查）
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# 设置缓存目录（可选）
cache_dir = os.path.expanduser('~/.cache/huggingface/')
if os.path.exists(cache_dir):
    print(f"✓ 检测到本地缓存: {cache_dir}")
else:
    print(f"⚠️  警告: 本地缓存不存在: {cache_dir}")
    print("   请先在联网环境下运行一次以下载模型")

print("✓ 离线模式环境变量已设置")
print("=" * 60)

# 导入并启动主程序
if __name__ == "__main__":
    # 导入主程序
    import app_full
    
    # 启动服务
    app_full.main()
