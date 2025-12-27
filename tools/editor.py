"""
Editorial Tool for Gemini Screenplay Writer.
Acts as a virtual "Executive Producer" to review drafts.
"""
import os
import json
from google import genai
from google.genai import types

# Use the same model as the main writer for consistency and high quality
MODEL_NAME = "gemini-3-flash-preview"

def perform_editorial_review(project_folder: str) -> str:
    """
    Reads the project files (story bible + script) and performs a deep critique
    using a fresh Gemini context with a 'Senior Executive Producer' persona.
    
    Args:
        project_folder: Name of the project folder in 'output/' (e.g., 'my_movie')
        
    Returns:
        A string containing the detailed critique and required fixes.
    """
    
    # 1. Resolve Path
    # Handle both full paths and relative folder names
    if os.path.isabs(project_folder):
        base_path = project_folder
    else:
        # Default to output/ folder
        base_path = os.path.join("output", project_folder)
    
    if not os.path.exists(base_path):
        return f"Error: Project folder not found at {base_path}"

    # 2. Gather Documents
    files_to_read = {
        "cover.md": "METADATA & LOGLINE",
        "characters.md": "CHARACTER BIBLE",
        "beat_sheet.md": "STRUCTURE MAP",
        "script.md": "CURRENT DRAFT"
    }
    
    context_data = ""
    
    # Check if script.md exists, if not look for act files
    script_path = os.path.join(base_path, "script.md")
    if not os.path.exists(script_path):
        # Look for act files
        act_files = sorted([f for f in os.listdir(base_path) if f.startswith("act_") and f.endswith(".md")])
        if act_files:
             files_to_read.pop("script.md")
             for af in act_files:
                 files_to_read[af] = f"SCRIPT SEGMENT ({af})"
        else:
            return "Error: No script.md or act_*.md files found to review."

    for filename, label in files_to_read.items():
        fpath = os.path.join(base_path, filename)
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                context_data += f"\n\n=== {label} ===\n{content}\n"
            except Exception as e:
                context_data += f"\n\n=== {label} ===\n[Error reading file: {e}]\n"
        else:
             context_data += f"\n\n=== {label} ===\n[File not found]\n"
             
    # 3. Construct the Editor Persona
    system_prompt = """You are a huge Hollywood Studio Executive Producer and heavy-hitting Script Editor. 
    Your name is "The Fixer".
    
    YOUR JOB:
    Review the provided script materials (Logline, Characters, Beat Sheet, and the Actual Script Draft).
    You must find flaws. You are not here to praise; you are here to perfect.
    
    CHECKLIST:
    1.  **Consistency**: Does the script match the Beat Sheet? Did they skip a beat?
    2.  **Character Voice**: Do characters sound distinct? Does the description in `characters.md` match their dialogue?
    3.  **Loose Ends**: Are there characters introduced who disappear?
    4.  **Formatting**: Is standard courier screenplay format used properly?
    5.  **Language**: If the script is in a specific language (e.g. Portuguese), is it natural?
    6.  **SPELLING & GRAMMAR (CRITICAL)**: Scan for typos like "teh" instead of "the". 
        *   **Action Lines**: Must be perfect English/Portuguese. NO TYPOS ALLOWED.
        *   **Dialogue**: Allow slang/errors ONLY if it fits the character's voice. If it looks like a typo (e.g., "I went to teh store"), FLAG IT.

    OUTPUT FORMAT:
    Provide a rigid, bulleted list of "CRITICAL NOTES". 
    If the script is good, find nitpicks to make it GREAT.
    If the script is failing, be harsh but constructive.
    End with a "VERDICT" (PASS, REWRITE, POLISH).
    
    IMPORTANT:
    If you see placeholders like [INSERT SCENE HERE], scream about it.
    If you see typos in Action Lines, you MUST list them for correction.
    """
    
    # 4. Call Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: API Key not found in environment."
        
    client = genai.Client(api_key=api_key)
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"Here is the project data:\n{context_data}\n\nGive me your editorial feedback.")
                ])
            ],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7, # Slightly creative but focused
            )
        )
        
        if response.text:
            return f"--- EDITORIAL FEEDBACK ---\n{response.text}\n--------------------------"
        else:
            return "Error: Editor stayed silent (Empty response from AI)."
            
    except Exception as e:
        return f"Error running Editorial Review: {e}"
