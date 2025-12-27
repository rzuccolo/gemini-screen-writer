"""
Gemini Screenplay Studio - Web Dashboard
"""
import os
import sys
import logging
import traceback
import time

# Setup robust logging immediately

# Setup production logging
# We keep logging enabled to help diagnosis, but use a cleaner file name and less verbose level
LOG_FILE = os.path.join(os.path.expanduser("~"), "gemini_screenplay_studio.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s %(levelname)s: %(message)s')

try:
    logging.info("Importing threading/queue...")
    import threading
    import queue
    import re
    
    logging.info("Importing Flask...")
    from flask import Flask, render_template, request, jsonify
    
    logging.info("Importing SocketIO...")
    from flask_socketio import SocketIO, emit
    
    logging.info("Importing Tools...")
    from tools import export_fdx, export_fountain
    
    logging.info("Importing Publish...")
    from publish import publish_screenplay
    import webbrowser
    from dotenv import load_dotenv, set_key
    
    logging.info("Imports complete. Initializing app...")
except Exception as e:
    logging.critical(f"FATAL: Import failed: {e}")
    logging.critical(traceback.format_exc())
    sys.exit(1)

# --- CONFIGURATION ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# .env and output should be in a user-accessible folder, not inside the bundle
if getattr(sys, 'frozen', False):
    # For the shared app, we'll store data in the user's home folder
    # This avoids all permission/read-only issues
    BASE_DATA_DIR = os.path.join(os.path.expanduser("~"), "Documents", "GeminiScreenplayStudio")
else:
    BASE_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DATA_DIR, '.env')
OUTPUT_DIR = os.path.join(BASE_DATA_DIR, "output")

# Ensure the directories and .env file exist
if not os.path.exists(BASE_DATA_DIR):
    os.makedirs(BASE_DATA_DIR, exist_ok=True)
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
if not os.path.exists(DOTENV_PATH):
    with open(DOTENV_PATH, 'w') as f:
        f.write("# Gemini API Key Store\n")

# CRITICAL: Load the environment from the persistent location at startup
logging.info(f"Loading environment from: {DOTENV_PATH}")
load_dotenv(DOTENV_PATH, override=True)

logging.info("--- Gemini Screenplay Studio Starting ---")
logging.info(f"Data Directory: {BASE_DATA_DIR}")


# DEBUG: Check resource paths before init
TEMPLATE_DIR = resource_path("templates")
logging.info(f"TEMPLATE_DIR (Calculated): {TEMPLATE_DIR}")
if not os.path.exists(TEMPLATE_DIR):
    logging.critical(f"CRITICAL: Template directory does not exist at {TEMPLATE_DIR}")

logging.info("Initializing Flask App...")
try:
    app = Flask(__name__, 
                template_folder=TEMPLATE_DIR,
                static_folder=TEMPLATE_DIR)
    logging.info("Flask App Initialized successfully.")
except Exception as e:
    logging.critical(f"FATAL: Failed to create Flask App: {e}")
    raise e

app.config['SECRET_KEY'] = 'gemini-studio-secret'

# Initialize SocketIO with threading mode for stability in frozen app
logging.info("Initializing SocketIO (threading mode)...")


try:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    logging.info("SocketIO initialized successfully.")
except Exception as e:
    logging.critical(f"Failed to init SocketIO: {e}")
    raise e



def check_has_api_key():
    val = os.getenv("GEMINI_API_KEY")
    if not val:
        return False
    val = val.strip("'\" ").strip()
    return len(val) > 0 and val.startswith("AIza")


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
                    
                    # Logline robust parsing
                    if line.lower().startswith('**logline**:') or line.lower().startswith('logline:'):
                        val = line.split(':', 1)[1].strip()
                        if val:
                            logline = val
                        else:
                            # Look ahead for next non-empty line
                            for j in range(i + 1, min(i + 5, len(lines))):
                                next_line = lines[j].strip()
                                if next_line:
                                    logline = next_line
                                    break
                    
                    # Logline header only (like **Logline**)
                    elif line.lower() == '**logline**' or line.lower() == 'logline':
                         # Look ahead for next non-empty line
                         for j in range(i + 1, min(i + 5, len(lines))):
                            next_line = lines[j].strip()
                            if next_line:
                                logline = next_line
                                break
                    
                    # Pages
                    if 'pages:' in line.lower() or 'páginas:' in line.lower():
                        parts = line.split(':')
                        if len(parts) > 1:
                            page_count = parts[1].strip()

            # Read prompt if available
            prompt_path = os.path.join(path, "prompt.md")
            original_prompt = ""
            if os.path.exists(prompt_path):
                try:
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        original_prompt = f.read().strip()
                except:
                    pass

            projects.append({
                "id": name,
                "title": title,
                "logline": logline,
                "pages": page_count,
                "prompt": original_prompt,
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
    rel_path = data.get('path') # Expected as "output/project_id/filename.md" or just "project_id/filename.md"
    
    # Clean it up: remove leading "output/" if present
    if rel_path.startswith('output/'):
        rel_path = rel_path[7:]
    
    # Resolve to absolute path securely
    abs_path = os.path.abspath(os.path.join(OUTPUT_DIR, rel_path))
    
    # Security check: must be inside OUTPUT_DIR
    if not abs_path.startswith(os.path.abspath(OUTPUT_DIR)):
        logging.warning(f"Access denied to path: {abs_path} (OUTPUT_DIR: {OUTPUT_DIR})")
        return jsonify({"success": False, "error": "Access denied"})
        
    try:
        if abs_path.endswith('.pdf') or abs_path.endswith('.fdx'):
             return jsonify({"success": False, "error": "Cannot read binary files. Use Open button."})
             
        with open(abs_path, 'r', encoding='utf-8') as f:
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
    rel_path = data.get('path')
    
    if rel_path.startswith('output/'):
        rel_path = rel_path[7:]
        
    abs_path = os.path.abspath(os.path.join(OUTPUT_DIR, rel_path))
    
    if not abs_path.startswith(os.path.abspath(OUTPUT_DIR)):
        return jsonify({"success": False, "error": "Access denied"})
        
    try:
        # Mac 'open' command
        subprocess.run(['open', abs_path]) 
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/publish', methods=['POST'])
def run_publish():
    data = request.json
    project_id = data.get('id')
    path = os.path.join(OUTPUT_DIR, project_id)
    try:
        # Check if project exists
        if not os.path.exists(path):
            return jsonify({"success": False, "error": "Project not found"})
        
        # Run publish script logic directly
        # We need to simulate the publishing logic. 
        # The writer.py logic calls publish.py as a script.
        # Let's import the function and run it.
        pdf_path = publish_screenplay(path)
        
        return jsonify({"success": True, "pdf_path": pdf_path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/shutdown', methods=['POST'])
def shutdown_app():
    logging.info("Shutdown requested via UI.")
    
    # Schedule shutdown slightly delayed to allow response to return
    def kill():
        logging.info("Goodbye! Killing process...")
        os._exit(0) # Force kill
        
    threading.Timer(1.0, kill).start()
    return jsonify({"success": True, "message": "App is shutting down..."})


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
    
    # Force kill previous thread if it exists to allow reset
    if writer_thread and writer_thread.is_alive():
        logging.warning("Thread busy, but user requested new run. Forcing restart usually risky but allowed here.")
        # In a real app we'd signal termination, but for now we safeguard via UI disabling
        # Just return to avoid crash, but UI should handle "Busy" state
        # socketio.emit('log', {'data': "⚠️ Engine is busy. Please restart app if stuck."})
        # return 
        pass 
        
    # Clear queue
    while not input_queue.empty():
        try: input_queue.get_nowait()
        except: pass

    writer_thread = threading.Thread(target=run_writer_task, args=(prompt, author))
    writer_thread.daemon = True
    writer_thread.start()

@socketio.on('reset_requested')
def handle_reset(data):
    # Only useful if we wanted to clear server state, but client does most clearing.
    # We can ensure queue is empty here.
    while not input_queue.empty():
        try: input_queue.get_nowait()
        except: pass


@socketio.on('provide_input')
def handle_input(data):
    response = data.get('value')
    input_queue.put(response)

if __name__ == '__main__':
    try:
        logging.info("--- Entering Main Loop ---")
        print("🎬 Gemini Screenplay Studio running on http://localhost:5001")
        
        # Auto-open browser in a separate thread to avoid blocking
        def open_browser():
            webbrowser.open("http://localhost:5001")
        
        threading.Timer(1.5, open_browser).start()
        
        # Disable debug mode in production to prevent recursive restarts
        is_frozen = getattr(sys, 'frozen', False)
        
        logging.info(f"Starting SocketIO server (frozen={is_frozen})...")
        
        # Force allow_unsafe_werkzeug=True for Mac app bundles to allow shutdown/restart if needed
        # And ensure it blocks
        socketio.run(app, debug=not is_frozen, port=5001, allow_unsafe_werkzeug=True)
        
        # If socketio.run returns, we keep the process alive manually just in case
        logging.info("Server loop ended. Entering fallback keep-alive...")
        while True:
            time.sleep(1)

    except Exception as e:

        logging.critical("FATAL CRASH:")
        logging.critical(traceback.format_exc())
        sys.exit(1)
