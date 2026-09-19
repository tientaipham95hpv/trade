import os
import sys
import tarfile
import paramiko
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def deploy_to_vps(host, port, user, password=None, key_filename=None, remote_dir="/root/bot-binance"):
    print(f"[*] Đang kết nối SSH tới {user}@{host}:{port}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    if key_filename is None:
        default_key = os.path.expanduser("~/.ssh/id_ed25519")
        if os.path.exists(default_key):
            key_filename = default_key

    try:
        if key_filename and os.path.exists(key_filename):
            print(f"[*] Sử dụng SSH Key: {key_filename}")
            ssh.connect(host, port=port, username=user, key_filename=key_filename, timeout=15)
        else:
            ssh.connect(host, port=port, username=user, password=password, timeout=15)
        print("[✓] Kết nối SSH thành công!")
    except paramiko.AuthenticationException:
        print("[!] Lỗi: Xác thực thất bại! Mật khẩu hoặc SSH key không chính xác.")
        return False
    except Exception as e:
        print(f"[!] Lỗi kết nối: {e}")
        return False

    # 1. Đóng gói mã nguồn (loại trừ venv, cache, log)
    archive_path = "bot_deploy.tar.gz"
    print("[*] Đang đóng gói mã nguồn dự án...")
    
    def tar_filter(tarinfo):
        exclude_names = ["venv", ".git", "__pycache__", "bot.log", "scratch", ".system_generated", "bot_deploy.tar.gz"]
        for exc in exclude_names:
            if exc in tarinfo.name:
                return None
        return tarinfo

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(".", arcname=".", filter=tar_filter)

    print(f"[✓] Đã tạo gói {archive_path} ({os.path.getsize(archive_path) / 1024:.1f} KB)")

    # 2. Upload file qua SFTP
    print(f"[*] Đang tải tệp lên VPS ({remote_dir})...")
    sftp = ssh.open_sftp()
    
    try:
        sftp.mkdir(remote_dir)
    except Exception:
        pass

    remote_archive = f"{remote_dir}/bot_deploy.tar.gz"
    sftp.put(archive_path, remote_archive)
    sftp.close()
    os.remove(archive_path)
    print("[✓] Đã tải lên gói triển khai thành công!")

    # 3. Giải nén và phân quyền
    print("[*] Đang giải nén và cấu hình môi trường VPS...")
    commands = [
        f"cd {remote_dir} && tar -xzf bot_deploy.tar.gz && rm bot_deploy.tar.gz",
        f"cd {remote_dir} && chmod +x deploy/setup_vps.sh",
        f"cd {remote_dir} && bash deploy/setup_vps.sh"
    ]

    for cmd in commands:
        print(f"--> Thực thi: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        for line in iter(stdout.readline, ""):
            print(line, end="")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"[!] Lỗi khi chạy lệnh: exit code {exit_status}")
            err_output = stderr.read().decode('utf-8')
            if err_output:
                print(err_output)
            return False

    # 4. Kiểm tra trạng thái
    stdin, stdout, stderr = ssh.exec_command("systemctl status binance-bot.service --no-pager")
    status_out = stdout.read().decode('utf-8')
    print("\nTrạng thái Systemd:")
    print(status_out)

    ssh.close()
    print(f"\n[🎉] TRIỂN KHAI HOÀN TẤT! Dashboard truy cập tại: http://{host}:8088")
    return True

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "185.185.80.197"
    pwd = sys.argv[2] if len(sys.argv) > 2 else "..."
    deploy_to_vps(host, 22, "root", pwd)
