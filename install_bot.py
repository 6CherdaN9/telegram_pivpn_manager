import os
import sys
import time
import subprocess
import re

def print_fixed_bar(percent, description):
    width = 40
    filled = int(width * percent // 100)
    bar = '#' * filled + '.' * (width - filled)
    sys.stdout.write(f'\033[s\033[999H\033[KProgress: [{percent:>3}%] [{bar}] {description}\033[u')
    sys.stdout.flush()

def run_step_system(command, description, start_pct, end_pct):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    current_pct = start_pct
    for line in process.stdout:
        if current_pct < end_pct - 1:
            current_pct += 0.5
            print_fixed_bar(int(current_pct), description)
    process.wait()
    print_fixed_bar(end_pct, description)

def main():
    if os.getuid() != 0:
        print("E: Root privileges required (sudo).")
        sys.exit(1)

    os.system('clear')
    print("-" * 60)
    print("SERVER BOT CONFIGURATION")
    print("-" * 60)

    token = input("¬ведите Telegram Token: ").strip()
    user_id = input("¬ведите ваш User ID: ").strip()
    
    print("\nStarting installation...")
    time.sleep(1)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    bot_path = os.path.join(current_dir, "bot.py")
    new_config_path = os.path.join(current_dir, "configs") + "/"

    steps = [
        ("apt update -y", "apt_update", 0, 20),
        ("apt install -y python3-pip qrencode python3-matplotlib curl", "pkg_install", 20, 50),
        ("pip3 install aiogram apscheduler psutil matplotlib --break-system-packages", "pip_libs", 50, 80),
    ]

    for cmd, desc, start, end in steps:
        run_step_system(cmd, desc, start, end)

    print_fixed_bar(85, "patching_bot_data")
    try:
        with open(bot_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = re.sub(r'API_TOKEN = [\'"].*?[\'"]', f"API_TOKEN = '{token}'", content)
        content = re.sub(r'YOUR_CHAT_ID = \d+', f"YOUR_CHAT_ID = {user_id}", content)
        content = re.sub(r'CONFIG_PATH = [\'"].*?[\'"]', f'CONFIG_PATH = "{new_config_path}"', content)
        
        with open(bot_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        if not os.path.exists(new_config_path):
            os.makedirs(new_config_path)
    except Exception as e:
        print(f"\n[ERROR] Failed to patch bot.py: {e}")
        sys.exit(1)

    print_fixed_bar(95, "service_setup")
    service_content = f"""[Unit]
Description=Telegram VPN Manager Bot
After=network.target

[Service]
WorkingDirectory={current_dir}
ExecStart={sys.executable} {bot_path}
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/vpn-bot.service", "w") as f:
        f.write(service_content)

    os.system("systemctl daemon-reload && systemctl enable vpn-bot.service && systemctl restart vpn-bot.service")
    
    print_fixed_bar(100, "ready")
    time.sleep(1)
    sys.stdout.write('\033[999H\033[K') 
    print("\n" + "-" * 60)
    print("SUCCESS: Bot is configured and running!")
    print(f"Path: {current_dir}")
    print("-" * 60)

if __name__ == "__main__":
    main()