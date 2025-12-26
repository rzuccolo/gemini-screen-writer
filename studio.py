"""
Gemini Screenplay Studio - Web Dashboard

A Flask-based web interface for:
- Managing screenplay projects
- Visualizing Markdown files with live rendering
- Publishing professional PDFs with automatic wrapping
- Exporting to Final Draft (.fdx)
- Opening generated files directly

Usage:
    python studio.py
    Then open http://localhost:5000
"""
import os
import sys
import threading
import queue
import re
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from tools import export_fdx, export_fountain
from publish import publish_screenplay
import webbrowser
from dotenv import load_dotenv, set_key

# --- CONFIGURATION ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# .env and output should be in the SAME FOLDER as the executable, not inside the bundle
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

app = Flask(__name__, 
            template_folder=resource_path("templates"))
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")


def check_has_api_key():
    val = os.getenv("GEMINI_API_KEY")
    if not val:
        return False
    return len(val.strip("'\" ").strip()) > 0


# --- GLOBAL STATE ---
input_queue = queue.Queue()
writer_thread = None

# --- MONKEY PATCHING ---
# We need to capture stdout to stream to the web UI
# And capture input() to get response from the web UI

class SocketStream:
    def write(self, text):
        sys.__stdout__.write(text) # Also print to real terminal
        socketio.emit('log', {'data': text})

    def flush(self):
        sys.__stdout__.flush()

# Replace stdout
sys.stdout = SocketStream()

# We also need to patch the `ask_user_impl` in tools.interaction
# Because simply patching `input()` is tricky with threads and buffering.
# Instead, we will import the module and swap the function.
import tools.interaction

def web_input(prompt):
    print(f"\n❓ {prompt}")
    # Notify frontend to show input box
    socketio.emit('request_input', {'prompt': prompt})
    
    # Wait for input from queue
    response = input_queue.get()
    print(f"> {response}\n")
    return response

# Apply patch
tools.interaction.ask_user_impl = web_input

# --- WRITER WRAPPER ---
def run_writer_task(prompt=None, author=None):
    import writer
    
    try:
        # Directly call main logic, bypassing argparse parsing in main if possible,
        # but writer.main() parses args. Let's patch sys.argv instead.
        old_argv = sys.argv
        sys.argv = ["writer.py"]
        if prompt:
            sys.argv.append(prompt)
        if author:
            sys.argv.extend(["--author", author])
            
        writer.main()

        
    except SystemExit:
        pass
    except Exception as e:
        print(f"Error running writer: {e}")
    finally:
        sys.argv = old_argv
        print("--- WRITER FINISHED ---")
        socketio.emit('writer_finished', {})

# --- ROUTES ---

import subprocess

# ... (Imports remain same)

# ... (SocketStream/MonkeyPatching remain same)

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/projects')
def list_projects():
    projects = []
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    for name in os.listdir(OUTPUT_DIR):
        path = os.path.join(OUTPUT_DIR, name)
        if os.path.isdir(path):
            cover_path = os.path.join(path, "cover.md")
            title = name.replace('_', ' ').title()
            logline = "No logline available. (Check cover.md)"
            page_count = "?"
            
            if os.path.exists(cover_path):
                with open(cover_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                # Parsing loop
                for i, line in enumerate(lines):
                    line = line.strip()
                    # Title
                    if line.startswith('# '):
                        title = line[2:].strip().replace('**', '')
                    
                    # Logline simple
                    if line.lower().startswith('**logline**:') or line.lower().startswith('logline:'):
                        val = line.split(':', 1)[1].strip()
                        if val:
                            logline = val
                        elif i + 1 < len(lines):
                            # Check next line
                            next_line = lines[i+1].strip()
                            if next_line: logline = next_line
                    
                    # Logline header only (like **Logline**)
                    if line.lower() == '**logline**' or line.lower() == 'logline':
                         if i + 1 < len(lines):
                            next_line = lines[i+1].strip()
                            if next_line: logline = next_line
                    
                    # Pages
                    if 'pages:' in line.lower() or 'páginas:' in line.lower():
                        parts = line.split(':')
                        if len(parts) > 1:
                            page_count = parts[1].strip()

            projects.append({
                "id": name,
                "title": title,
                "logline": logline,
                "pages": page_count,
                "path": path,
                "has_pdf": os.path.exists(os.path.join(path, f"{name}_script.pdf")),
                "has_fdx": os.path.exists(os.path.join(path, f"{name}.fdx")),
                "has_fountain": os.path.exists(os.path.join(path, f"{name}.fountain"))
            })
            
    return jsonify(projects)

@app.route('/files/<project_id>')
def list_files(project_id):
    path = os.path.join(OUTPUT_DIR, project_id)
    if not os.path.exists(path):
        return jsonify([])
    
    files = []
    for f in sorted(os.listdir(path)):
        if not f.startswith('.'): # Skip hidden files
            files.append(f)
    return jsonify(files)

@app.route('/read', methods=['POST'])
def read_file_content():
    data = request.json
    path = data.get('path')
    if OUTPUT_DIR not in path:
        return jsonify({"success": False, "error": "Access denied"})
        
    try:
        if path.endswith('.pdf') or path.endswith('.fdx'):
             return jsonify({"success": False, "error": "Cannot read binary files. Use Open button."})
             
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"success": True, "content": content})
    except Exception as e:
         return jsonify({"success": False, "error": str(e)})

@app.route('/save_key', methods=['POST'])
def save_api_key():
    data = request.json
    key = data.get('key')
    if not key:
        return jsonify({"success": False, "error": "No key provided"})
    
    # Sanitize: strip quotes and whitespace
    key = key.strip("'\" ").strip()

    
    try:
        # Save to .env
        set_key(DOTENV_PATH, "GEMINI_API_KEY", key)
        # Reload environment
        load_dotenv(DOTENV_PATH, override=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/status')
def get_status():
    return jsonify({
        "has_api_key": check_has_api_key()
    })

@app.route('/open', methods=['POST'])
def open_file():
    data = request.json
    path = data.get('path')
    # Limit to opening inside output dir for safety (basic check)
    if OUTPUT_DIR not in path:
        return jsonify({"success": False, "error": "Access denied"})
        
    try:
        # Mac 'open' command
        subprocess.run(['open', path]) 
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/publish', methods=['POST'])
def run_publish():
    data = request.json
    project_id = data.get('id')
    path = os.path.join(OUTPUT_DIR, project_id)
    try:
        publish_screenplay(path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/export', methods=['POST'])
def run_export():
    data = request.json
    project_id = data.get('id')
    path = os.path.join(OUTPUT_DIR, project_id)
    try:
        export_fdx.export_to_fdx(path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/export_fountain', methods=['POST'])
def run_export_fountain():
    data = request.json
    project_id = data.get('id')
    path = os.path.join(OUTPUT_DIR, project_id)
    try:
        export_fountain.export_to_fountain(path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- SOCKET EVENTS ---

@socketio.on('start_writer')
def handle_start_writer(data):
    prompt = data.get('prompt')
    author = data.get('author')
    global writer_thread
    if writer_thread and writer_thread.is_alive():
        return # Already running
        
    writer_thread = threading.Thread(target=run_writer_task, args=(prompt, author))
    writer_thread.daemon = True
    writer_thread.start()

@socketio.on('provide_input')
def handle_input(data):
    response = data.get('value')
    input_queue.put(response)

if __name__ == '__main__':
    print("🎬 Gemini Screenplay Studio running on http://localhost:5000")
    
    # Auto-open browser in a separate thread to avoid blocking
    def open_browser():
        webbrowser.open("http://localhost:5001")
    
    threading.Timer(1.5, open_browser).start()
    
    socketio.run(app, debug=True, port=5001)
