"""
快速重启服务器
"""
import subprocess
import time
import sys

def restart_server():
    """重启服务器"""
    print("=" * 60)
    print("重启pomCoder服务器")
    print("=" * 60)
    
    # 1. 停止占用端口的进程
    print("\n1. 停止旧进程...")
    try:
        result = subprocess.run(
            'netstat -ano | findstr :58761',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            pids = set()
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.add(pid)
            
            for pid in pids:
                print(f"   停止进程 PID={pid}...")
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
            
            print("   ✓ 旧进程已停止")
            time.sleep(2)
        else:
            print("   ✓ 端口空闲")
    except Exception as e:
        print(f"   警告: {e}")
    
    # 2. 启动新服务器
    print("\n2. 启动服务器...")
    print("   请在新终端运行: python start_full.py")
    print("\n" + "=" * 60)
    print("提示: 服务器将在后台启动，请等待20秒")
    print("=" * 60)

if __name__ == "__main__":
    restart_server()
