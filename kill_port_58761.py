"""
停止占用58761端口的进程
"""
import subprocess
import sys

def kill_port_process(port=58761):
    """停止占用指定端口的进程"""
    try:
        # 查找占用端口的进程
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            print(f"✓ 端口 {port} 未被占用")
            return True
        
        # 解析PID
        lines = result.stdout.strip().split('\n')
        pids = set()
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(pid)
        
        if not pids:
            print(f"✓ 端口 {port} 未被占用")
            return True
        
        print(f"发现 {len(pids)} 个进程占用端口 {port}")
        
        # 停止进程
        for pid in pids:
            print(f"正在停止进程 PID={pid}...")
            try:
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
                print(f"✓ 进程 {pid} 已停止")
            except subprocess.CalledProcessError:
                print(f"✗ 无法停止进程 {pid}")
        
        print(f"\n✓ 端口 {port} 已释放")
        return True
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("停止占用58761端口的进程")
    print("=" * 60)
    print()
    
    if kill_port_process(58761):
        print("\n可以重新启动服务器了")
    else:
        print("\n请手动检查端口占用情况")
        sys.exit(1)
