"""
Utility functions for the Gemini Writing Agent.
"""

from typing import List, Dict, Any, Callable
from google import genai
from google.genai import types


def estimate_token_count(client: genai.Client, model: str, contents: List[types.Content]) -> int:
    """
    Estimate the token count for the given contents using the Gemini API.
    
    Args:
        client: The Gemini client instance
        model: The model name
        contents: List of Content objects
        
    Returns:
        Total token count
    """
    try:
        response = client.models.count_tokens(
            model=model,
            contents=contents
        )
        return response.total_tokens
    except Exception as e:
        # Fallback: rough estimate based on character count
        total_chars = 0
        for content in contents:
            for part in content.parts:
                if hasattr(part, 'text') and part.text:
                    total_chars += len(part.text)
        # Rough estimate: 4 chars per token
        return total_chars // 4


def get_tool_definitions() -> types.Tool:
    """
    Returns the tool definitions in the format expected by Gemini.
    
    Returns:
        Tool object containing all function declarations
    """
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="create_project",
                description="Creates a new project folder in the 'output' directory with a sanitized name. This should be called first before writing any files. Only one project can be active at a time.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "project_name": types.Schema(
                            type=types.Type.STRING,
                            description="The name for the project folder (will be sanitized for filesystem compatibility)"
                        )
                    },
                    required=["project_name"]
                )
            ),
            types.FunctionDeclaration(
                name="write_file",
                description="Writes content to a markdown file in the active project folder. Supports three modes: 'create' (creates new file, fails if exists), 'append' (adds content to end of existing file), 'overwrite' (replaces entire file content).",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "filename": types.Schema(
                            type=types.Type.STRING,
                            description="The name of the markdown file to write (should end in .md)"
                        ),
                        "content": types.Schema(
                            type=types.Type.STRING,
                            description="The content to write to the file"
                        ),
                        "mode": types.Schema(
                            type=types.Type.STRING,
                            enum=["create", "append", "overwrite"],
                            description="The write mode: 'create' for new files, 'append' to add to existing, 'overwrite' to replace"
                        )
                    },
                    required=["filename", "content", "mode"]
                )
            ),
            types.FunctionDeclaration(
                name="compress_context",
                description="INTERNAL TOOL - This is automatically called by the system when token limit is approached. You should not call this manually. It compresses the conversation history to save tokens.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={},
                    required=[]
                )
            ),
            types.FunctionDeclaration(
                name="ask_user",
                description="Ask the user a question to get clarification or additional information. Use this when the request is ambiguous (e.g., missing genre or format).",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                         "question": types.Schema(
                            type=types.Type.STRING,
                            description="The question to ask the user."
                        )
                    },
                    required=["question"]
                )
            )
        ]
    )


def get_tool_map() -> Dict[str, Callable]:
    """
    Returns a mapping of tool names to their implementation functions.
    
    Returns:
        Dictionary mapping tool name strings to callable functions
    """
    from tools import write_file_impl, create_project_impl, compress_context_impl, ask_user_impl
    
    return {
        "create_project": create_project_impl,
        "write_file": write_file_impl,
        "compress_context": compress_context_impl,
        "ask_user": ask_user_impl
    }


def get_system_prompt() -> str:
    """
    Returns the system prompt for the writing agent.
    
    Returns:
        System prompt string
    """
    return """You are an expert Screenwriter and Showrunner. Your goal is to write award-winning screenplays, from structure to final script.

YOUR CAPABILITIES:
1.  **Create Projects**: Organize work in project folders.
2.  **Write Files**: Create/update markdown files.
3.  **Ask Questions**: INTERACTIVE MODE. If you lack critical info (Genre, Format, Tone), use `ask_user` to clarify.
4.  **Auto-Compression**: Handles context limits automatically.

SCREENPLAY PROTOCOLS:

1.  **INTERACTIVE CLARIFICATION (CRITICAL)**
    *   If the user says "Write a movie" or "Idea for a show", YOU MUST CLARIFY:
        *   **Format**: Feature (90-120p), TV Pilot (30-60p), TV Episode (22-60p), Short (5-40p), Web Series (5-15p)?
        *   **Genre**: Sci-fi, Horror, Rom-Com, Thriller, etc.?
    *   Use `ask_user` tool for this.

2.  **DELIVERABLES & STRUCTURE**
    Always produce these files in order:
    
    A.  `cover.md`:
        *   **Title**
        *   **Format** (e.g., Feature Film)
        *   **Genre**
        *   **Logline**: [Protagonist] faces [Inciting Incident], must [Objective] or else [Stakes].
        *   **Synopsis**: A compelling overview.
        *   **Estimated Stats**: Page count / Word count.

    B.  `beat_sheet.md`:
        *   Full structural breakdown (Save the Cat or similar).
        *   **Act I** (Setup, Catalyst, Debate, Break into Two)
        *   **Act II** (Fun & Games, Midpoint, Bad Guys Close In, All is Lost)
        *   **Act III** (Finale, Final Image)

    C.  `characters.md`:
        *   List of characters.
        *   **Name, Role, Description, Arc, Traits**.

    D.  `script.md` (or `act_1.md`, `act_2.md`... for long works):
        *   The actual screenplay.

3.  **FORMATTING STANDARDS (MARKDOWN)**
    *   **Scene Headings**: `**INT. HOUSE - DAY**` (Bold, Uppercase)
    *   **Action**: Standard text. Descriptive, visual, present tense.
    *   **Character Cues**: `**JOHN**` (Centered appearance not possible in pure MD, but use Bold Caps).
    *   **Dialogue**: Standard text under Character.
    *   **Parentheticals**: `(sarcastically)`
    *   **Transitions**: `> CUT TO:` (Blockquote or align right if possible, but consistnecy is key).

    *Example*:
    
    **INT. SPACESHIP COCKPIT - NIGHT**

    Sparks fly. ALIEN SLIME covers the dashboard.
    
    **RIPLEY**
    (breathless)
    Get to the airlock!

4.  **QUALITY GUIDELINES**
    *   **Show, Don't Tell**: Visual storytelling.
    *   **Dialogue**: Subtext, conflict, distinctive voices.
    *   **Pacing**: Match the genre/format constraints.

Your Workflow:
1.  Analyze Request -> `ask_user` if vague.
2.  `create_project`.
3.  Write `cover.md` & `characters.md`.
4.  Write `beat_sheet.md`.
5.  Write the Script (`script.md`).
6.  Review and Refine.
"""
