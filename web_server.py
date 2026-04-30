from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys

# Add parent directory to path so we can import jarvis modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.command_handler import CommandHandler

# Dummy classes for CommandHandler
class DummyVoice:
    def speak(self, text):
        print(f"Voice: {text}")
    def speak_async(self, text):
        print(f"Voice Async: {text}")
    def wait_until_done(self):
        pass

class DummyAI:
    def chat(self, text, voice_callback=None):
        if voice_callback:
            voice_callback("AI response")
        return "AI response"

# Create a command handler to execute the commands
cmd_handler = CommandHandler(DummyVoice(), DummyAI())

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/api/'):
            if self.path == '/api/tasks':
                try:
                    import psutil
                    import ctypes

                    EnumWindows = ctypes.windll.user32.EnumWindows
                    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
                    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
                    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
                    GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId

                    visible_pids = set()
                    def foreach_window(hwnd, lParam):
                        if IsWindowVisible(hwnd):
                            length = GetWindowTextLength(hwnd)
                            if length > 0:
                                pid = ctypes.c_uint(0)
                                GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                                visible_pids.add(pid.value)
                        return True
                    
                    EnumWindows(EnumWindowsProc(foreach_window), 0)

                    tasks = []
                    unique_names = set()
                    
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            pid = proc.info['pid']
                            name = proc.info['name']
                            
                            sys_procs = ['explorer.exe', 'searchapp.exe', 'textinputhost.exe', 'applicationframehost.exe', 'startmenuexperiencehost.exe', 'systemsettings.exe']
                            
                            if pid in visible_pids and name and name.endswith('.exe') and name.lower() not in sys_procs:
                                if name not in unique_names:
                                    unique_names.add(name)
                                    clean_name = name[:-4].title()
                                    if clean_name.lower() == "Code": clean_name = "Antigravity (VS Code)"
                                    if clean_name.lower() == "Chrome": clean_name = "Google Chrome"
                                    if clean_name.lower() == "Msedge": clean_name = "Microsoft Edge"
                                    
                                    tasks.append({"pid": pid, "name": clean_name})
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            pass
                    
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"tasks": tasks}).encode('utf-8'))
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        else:
            # Serve static files
            file_path = self.path
            if file_path == '/':
                file_path = '/index.html'
            
            # Prevent directory traversal
            safe_path = os.path.basename(file_path.strip('/'))
            if not safe_path:
                safe_path = 'index.html'
                
            full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), safe_path)
            
            if os.path.exists(full_path):
                content_type = 'text/plain'
                if safe_path.endswith('.html'): content_type = 'text/html'
                elif safe_path.endswith('.css'): content_type = 'text/css'
                elif safe_path.endswith('.js'): content_type = 'application/javascript'
                elif safe_path.endswith('.json'): content_type = 'application/json'
                elif safe_path.endswith('.svg'): content_type = 'image/svg+xml'
                elif safe_path.endswith('.png'): content_type = 'image/png'
                
                try:
                    with open(full_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', content_type)
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        if self.path == '/api/execute':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except:
                self.send_response(400)
                self.end_headers()
                return

            password = data.get('password')
            command = data.get('command')

            if password != '4171':
                self.send_response(401)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Unauthorized")
                return

            print(f"Executing command from web: {command}")
            
            # Map simple commands to Jarvis commands
            jarvis_cmd = ""
            if command == "disconnect_server":
                print("Disconnect requested. Shutting down Web Server.")
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "success", "message": "Server disconnected and closed."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
                # Wait 1 second so response can be sent, then kill the script
                import threading
                threading.Timer(1.0, lambda: os._exit(0)).start()
                return
            elif command == "shutdown":
                jarvis_cmd = "shutdown system"
            elif command == "terminate_all":
                jarvis_cmd = "terminate all tasks"
            elif command == "kill_task":
                pid = data.get('pid')
                try:
                    import os
                    os.system(f"taskkill /F /PID {pid}")
                    print(f"Task {pid} forcefully terminated.")
                except Exception as e:
                    print(f"Failed to kill task {pid}: {e}")
            elif command == "mute_toggle":
                import pyautogui
                pyautogui.press("volumemute")
            elif command == "volume_up":
                import pyautogui
                for _ in range(5):
                    pyautogui.press("volumeup")
            elif command == "volume_down":
                import pyautogui
                for _ in range(5):
                    pyautogui.press("volumedown")
            elif command == "lock_pc":
                os.system("rundll32.exe user32.dll,LockWorkStation")
            elif command == "unlock_pc":
                import pyautogui
                import time
                print("Initiating Unlock PC sequence...")
                pyautogui.press("space")
                time.sleep(0.5)
                pyautogui.press("space") # Second press to ensure wake
                time.sleep(1.5)
                pyautogui.write("4171", interval=0.1)
                pyautogui.press("enter")
                print("Unlock PC sequence completed.")
            elif command == "system_sleep":
                print("Initiating OS Sleep...")
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif command == "open_dashboard":
                jarvis_cmd = "open antigravity premium pro"
            elif command == "listen_command":
                print("Web requested listening. Voice commands can also be typed and sent directly!")
            elif command == "set_volume":
                val = data.get('value', 50)
                print(f"Volume set to {val} on web UI.")
            elif command == "sleep":
                jarvis_cmd = "sleep"
            elif command == "wake":
                jarvis_cmd = "wake up" # assuming jarvis has a wake up phrase
            else:
                # Passes sleep, workstation 1/2/3, chill mode, and voice text directly to Jarvis
                jarvis_cmd = command

            if jarvis_cmd:
                cmd_handler.process(jarvis_cmd)

            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "success", "message": f"Task '{command}' successful."}
            self.wfile.write(json.dumps(response).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=5000):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    
    # Get local IP
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
        
    print(f"==================================================")
    print(f"🌐 Jarvis Web Server is RUNNING!")
    print(f"📱 Enter this IP on your phone: http://{IP}:{port}")
    print(f"🔑 Password: 4171")
    print(f"==================================================")
    
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(f"{IP}:{port}|4171")
        qr.make(fit=True)
        print("Scan this QR code to connect instantly:")
        qr.print_ascii(invert=True)
    except ImportError:
        print("Tip: Install 'qrcode' (pip install qrcode) to see a connection QR code here.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == '__main__':
    run()
