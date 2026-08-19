import os
import sys
import socket
import threading
import subprocess
import time
import json
import platform
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
import webbrowser
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

APP_PORT = int(os.getenv("APP_PORT", 6969))
BROADCAST_PORT = int(os.getenv("BROADCAST_PORT", 7979))
COMMAND_PORT = int(os.getenv("COMMAND_PORT", 9000))
APP_NAME = "MiniDesk"

QT = True

minidesk_devices = {}
devices_lock = threading.Lock()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return '127.0.0.1'

def verify_minidesk_device(ip, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, COMMAND_PORT))
        sock.close()
        return result == 0
    except:
        return False

def get_broadcast_addresses():
    local_ip = get_local_ip()
    network_base = '.'.join(local_ip.split('.')[:-1]) + '.'
    
    return [
        '255.255.255.255', 
        network_base + '255' 
    ]
def broadcaster():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    hostname = socket.gethostname()
    ip = get_local_ip()
    broadcast_addrs = get_broadcast_addresses()
    
    while True:
        try:
            msg = json.dumps({
                "name": hostname, 
                "ip": ip, 
                "timestamp": time.time(),
                "port": COMMAND_PORT,
                "app": "MiniDesk" 
            }).encode()
            
            for broadcast_addr in broadcast_addrs:
                try:
                    sock.sendto(msg, (broadcast_addr, BROADCAST_PORT))
                except Exception as e:
                    print(f"[DEBUG] Broadcast failed to {broadcast_addr}: {e}")
            
        except Exception as e:
            print(f"[Broadcast Error] {e}")
        
        time.sleep(10)

def listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('', BROADCAST_PORT))
        print(f"[DEBUG] Listening for MiniDesk broadcasts on port {BROADCAST_PORT}")
    except Exception as e:
        print(f"[ERROR] Listener bind failed: {e}")
        return

    local_ip = get_local_ip()

    while True:
        try:
            sock.settimeout(2.0)
            data, addr = sock.recvfrom(1024)
            info = json.loads(data.decode())
            
            if info.get('app') == 'MiniDesk' and info['ip'] != local_ip:
                if verify_minidesk_device(info['ip'], timeout=1):
                    with devices_lock:
                        minidesk_devices[info['ip']] = {
                            "name": info['name'],
                            "ip": info['ip'],
                            "last_seen": time.time(),
                            "verified": True,
                            "discovered_by": "broadcast"
                        }
                    print(f"[VERIFIED] MiniDesk device: {info['name']} @ {info['ip']}")
                else:
                    print(f"[IGNORED] Device {info['ip']} broadcast MiniDesk but port {COMMAND_PORT} not responding")
            
        except socket.timeout:
            continue
        except Exception as e:
            continue

def smart_scanner():
    def check_minidesk_device(ip):
        try:
            if verify_minidesk_device(ip, timeout=1):
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except:
                    hostname = f"MiniDesk-{ip.split('.')[-1]}"
                
                local_ip = get_local_ip()
                with devices_lock:
                    if ip not in minidesk_devices and ip != local_ip:
                        minidesk_devices[ip] = {
                            "name": hostname,
                            "ip": ip,
                            "last_seen": time.time(),
                            "verified": True,
                            "discovered_by": "scan"
                        }
                        print(f"[SCAN] Found MiniDesk device: {hostname} @ {ip}")
        except:
            pass
    while True:
        try:
            local_ip = get_local_ip()
            network_base = '.'.join(local_ip.split('.')[:-1]) + '.'
            
            print(f"[DEBUG] Scanning for MiniDesk devices on {network_base}0/24...")

            threads = []
            for i in range(1, 255):
                ip = network_base + str(i)
                thread = threading.Thread(target=check_minidesk_device, args=(ip,), daemon=True)
                threads.append(thread)
                thread.start()
                
                if len(threads) >= 20: 
                    for t in threads:
                        t.join()
                    threads = []
                    time.sleep(0.1)
        
            for thread in threads:
                thread.join()
            
            with devices_lock:
                device_count = len(minidesk_devices)
            print(f"[DEBUG] Scan complete. MiniDesk devices found: {device_count}")
            
        except Exception as e:
            print(f"[SCANNER ERROR] {e}")
        
        time.sleep(60) 

def device_cleanup():
    """Remove devices that haven't been seen recently"""
    while True:
        time.sleep(30)
        current_time = time.time()
        with devices_lock:
            expired_devices = []
            for ip, device in minidesk_devices.items():
                if current_time - device.get('last_seen', 0) > 30:
                    expired_devices.append(ip)
            
            for ip in expired_devices:
                print(f"[CLEANUP] Removing inactive device: {minidesk_devices[ip]['name']} @ {ip}")
                del minidesk_devices[ip]

def device_verifier():
    """Periodically verify existing devices are still running MiniDesk"""
    while True:
        time.sleep(45)
        with devices_lock:
            devices_to_check = list(minidesk_devices.items())
        
        for ip, device in devices_to_check:
            if not verify_minidesk_device(ip, timeout=2):
                with devices_lock:
                    if ip in minidesk_devices:
                        print(f"[VERIFY] Device {device['name']} @ {ip} no longer responding - removing")
                        del minidesk_devices[ip]
            else:
                with devices_lock:
                    if ip in minidesk_devices:
                        minidesk_devices[ip]['last_seen'] = time.time()

def start_command_server():
    def handle_client(conn, addr):
        try:
            data = conn.recv(4096).decode()
            print(f"[CMD] Received from {addr}: {data}")
            try:
                output = subprocess.check_output(data, shell=True, stderr=subprocess.STDOUT, text=True)
            except subprocess.CalledProcessError as e:
                output = e.output
            conn.sendall(output.encode())
        except Exception as e:
            conn.sendall(f"[ERROR] {e}".encode())
        finally:
            conn.close()

    def server_thread():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('', COMMAND_PORT))
            server.listen(5)
            print(f"[CMD SERVER] Listening on port {COMMAND_PORT}...")
        except Exception as e:
            print(f"[CMD SERVER] Failed to bind to port {COMMAND_PORT}: {e}")
            return
            
        while True:
            try:
                conn, addr = server.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                print(f"[CMD SERVER ERROR] {e}")

    threading.Thread(target=server_thread, daemon=True).start()

app = Flask(__name__, template_folder=resource_path("templates"))

@app.route("/")
def index():
    with devices_lock:
        device_list = list(minidesk_devices.values())
    print(f"[DEBUG] Serving index with {len(device_list)} verified MiniDesk devices")
    return render_template("index.html", devices=device_list)

@app.route("/api/devices")
def api_devices():
    with devices_lock:
        return jsonify(list(minidesk_devices.values()))

@app.route("/connect/<ip>")
def connect(ip):
    with devices_lock:
        if ip not in minidesk_devices:
            return f"MiniDesk device {ip} not found or not responding", 404
    return render_template("terminal.html", ip=ip)

@app.route("/exec_remote", methods=["POST"])
def exec_remote():
    data = request.json
    ip = data.get("ip")
    cmd = data.get("cmd")
    if not ip or not cmd:
        return jsonify({"error": "Missing ip or cmd"}), 400

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((ip, COMMAND_PORT))
            s.sendall(cmd.encode())
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
        return jsonify({"output": response.decode(errors="ignore")})
    except Exception as e:
        return jsonify({"error": f"Failed to connect to {ip}: {e}"})

@app.route("/debug")
def debug():
    local_ip = get_local_ip()
    network_base = '.'.join(local_ip.split('.')[:-1]) + '.'
    
    with devices_lock:
        device_list = list(minidesk_devices.values())
    
    debug_info = {
        "system": platform.system(),
        "local_ip": local_ip,
        "network_base": network_base,
        "minidesk_devices_count": len(device_list),
        "minidesk_devices": device_list,
        "ports": {
            "app_port": APP_PORT,
            "broadcast_port": BROADCAST_PORT,
            "command_port": COMMAND_PORT
        },
        "network_optimization": {
            "broadcast_interval": "10 seconds",
            "scan_interval": "5 minutes",
            "device_timeout": "60 seconds",
            "concurrent_threads": "20 max"
        }
    }
    
    return f"<pre>{json.dumps(debug_info, indent=2)}</pre>"

def create_tray(app_qt):
    tray_icon = QSystemTrayIcon()
    
    try:
        if os.path.exists(resource_path("icon.png")):
            tray_icon.setIcon(QIcon(resource_path("icon.png")))
        else:
            tray_icon.setIcon(app_qt.style().standardIcon(app_qt.style().SP_ComputerIcon))
    except:
        tray_icon.setIcon(app_qt.style().standardIcon(app_qt.style().SP_ComputerIcon))
    
    tray_icon.setToolTip(f"{APP_NAME} - Right-click for options")
    menu = QMenu()
    open_action = QAction("🌐 Open Web UI", menu)
    open_action.triggered.connect(lambda: webbrowser.open(f"http://localhost:{APP_PORT}"))
    menu.addAction(open_action)
    menu.addSeparator()
    exit_action = QAction("❌ Exit", menu)
    exit_action.triggered.connect(app_qt.quit)
    menu.addAction(exit_action)

    tray_icon.setContextMenu(menu)

    tray_icon.activated.connect(lambda reason: 
        webbrowser.open(f"http://localhost:{APP_PORT}") 
        if reason == QSystemTrayIcon.Trigger else None
    )

    tray_icon.show()

    if tray_icon.supportsMessages():
        tray_icon.showMessage(
            APP_NAME,
            f"MiniDesk is running!\nWeb UI: http://localhost:{APP_PORT}",
            QSystemTrayIcon.Information,
            3000
        )
    
    return tray_icon

if __name__ == "__main__":
    threading.Thread(target=broadcaster, daemon=True).start()
    threading.Thread(target=listener, daemon=True).start()
    threading.Thread(target=device_cleanup, daemon=True).start()
    threading.Thread(target=device_verifier, daemon=True).start()
    threading.Thread(target=smart_scanner, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=APP_PORT, debug=False, use_reloader=False), daemon=True).start()
    
    start_command_server()
    app_qt = QApplication(sys.argv)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("[ERROR] System tray is not available on this system")
        sys.exit(1)
    tray = create_tray(app_qt)
    app_qt.setQuitOnLastWindowClosed(False)
    sys.exit(app_qt.exec_())
