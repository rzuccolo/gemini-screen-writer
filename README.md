# Gemini Screenplay Writer

An autonomous agent powered by **Google's Gemini 3 Flash** model for creating industry-standard screenplays, including Feature Films, TV Pilots, and Shorts.

## Features

- 🤖 **Autonomous Screenwriting**: The agent plans and executes screenplay writing tasks independently.
- 🎬 **Industry Standards**: Generates professional deliverables including Beat Sheets, Character Breakdowns, and formatted Scripts.
- 🌎 **Multi-Language Support**: Specialized support for **Portuguese (Brazil)** screenwriting standards (e.g., `CORTA PARA:`).
- 📄 **Professional PDF Publisher**: Converts Markdown to industry-standard Screenplay PDFs (Courier 12pt, correct margins, auto-localized).
- 💾 **Final Draft Export**: Exports to `.fdx` format for professional editing in Final Draft or Celtx.
- 💬 **Interactive Mode**: Intelligent clarification system - calls `ask_user` when formats or genres are ambiguous (e.g., "Feature or Short?").
- ⚡ **Real-Time Streaming**: See the agent's thinking and writing appear as it's generated.

## Installation

### Prerequisites

We recommend using [uv](https://github.com/astral-sh/uv) for fast Python package management:

```bash
# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup

1. Install dependencies:

**Using uv (recommended):**
```bash
uv pip install -r requirements.txt
```

**Or using pip:**
```bash
pip install -r requirements.txt
```

2. Configure your API key:

Create a `.env` file with your API key:
```bash
# Copy the example file
cp env.example .env

# Edit .env and add your API key
# The file should contain:
GEMINI_API_KEY=your-api-key-here
```

Get your Gemini API key from: https://aistudio.google.com/app/apikey

### 1. Gemini Screenplay Studio (Web UI) **[NEW]**

The easiest way to use the agent. A beautiful dashboard to manage projects, publish PDFs, and export FDX files.

```bash
python studio.py
```
*Then open http://localhost:5000 in your browser.*

**New Studio Features:**
- 👁️ **Visualizer**: Click any `.md` file (like `beat_sheet.md`) to view it instantly with proper Markdown formatting (bold, italics, headers).
- ↗️ **Direct Open**: One-click opening for generated PDFs and FDX files.


### 2. CLI Workflow (Advanced)

#### Write Step
Run the interactive writer (recommended) or provide a prompt:
```bash
python writer.py
# Or with a prompt
python writer.py "Write a 90-page Horror Feature Film..."
```

### 2. Publish Step (Generate Screenplay PDF)

Convert your project into a professional PDF with **Courier 12pt** and industry margins:
```bash
python publish.py output/your_project_name
```
*Note: This step automatically detects the language and adjusts the title page (e.g., "Escrito por" for Portuguese scripts).*

### 3. Export Step (Generate Final Draft .fdx)

Export your script for professional editing:
```bash
python tools/export_fdx.py output/your_project_name
```

## How It Works

### The Agent's Tools

The agent has access to four tools:

1. **create_project**: Creates a project folder to organize the writing.
2. **write_file**: Writes markdown files (create/append/overwrite).
3. **ask_user**: **[NEW]** Pauses execution to ask the user for clarification (e.g., "What is the genre?").
4. **compress_context**: Automatically triggered to manage context size.

### Project Structure

```
gemini-screen-writer/
├── writer.py        # Main agent
├── tools/
│   ├── __init__.py       # Tool registry
│   ├── writer.py         # File writing tool
│   ├── project.py        # Project management tool
│   ├── interaction.py    # [NEW] User interaction tool
│   └── compression.py    # Context compression tool
├── utils.py              # Utilities & System Prompt
├── requirements.txt      # Python dependencies
├── .env                  # API Credentials
└── README.md             # This file

# Generated Output:
### Project Structure (Artifacts)

```
output/your_project/
├── cover.md          # Title, Logline, Synopsis, Stats
├── characters.md     # Detailed Character Breakdowns & Arcs
├── beat_sheet.md     # Structural Breakdown (Acts I, II, III)
├── script.md         # The Screenplay (Markdown)
├── script.pdf        # Professional PDF (Generated via publish.py)
└── script.fdx        # Final Draft Export (Generated via export_fdx.py)
```

## Multi-Language Support

The system is optimized for **English** and **Portuguese (Brazil)**:
*   **PT-BR**: Automatically uses `CORTA PARA:` for transitions and `Escrito por` for PDF title pages.
*   **Accents**: Fully supports characters like `ã`, `ç`, `é` in both Markdown and PDF.
*   **Emoji Safety**: Automatically strips emojis from PDF generation to prevent font crashes.

## Supported Formats

The agent understands and formats for:
*   **Feature Film** (90-120 pages)
*   **TV Pilot** (30-60 pages)
*   **TV Episode** (22-60 pages)
*   **Short Film** (5-40 pages)
*   **Web Series** (5-15 pages)

## Artifacts Details

1.  **Cover Page** (`cover.md`): Logline, synopsis, genre, title, and estimated stats.
2.  **Beat Sheet** (`beat_sheet.md`): Full structural breakdown (Acts I, II, III) using "Save the Cat" or similar conventions.
3.  **Character List** (`characters.md`): Descriptions, arcs, and traits for the entire cast.
4.  **Script** (`script.md`): The actual screenplay formatted for industry recognition.
5.  **PDF Script**: Generated via `publish.py`, uses Courier 12pt with industry-standard margins (Left 1.5", Right 1.0").
6.  **FDX Export**: Generated via `tools/export_fdx.py`, compatible with Final Draft 12.

## Technical Details

- **Model**: gemini-3-flash-preview
- **Thinking Level**: HIGH (for better reasoning)
- **Context Window**: 1,000,000 tokens
- **Max Iterations**: 300

## License

MIT License with Attribution Requirement - see [LICENSE](LICENSE) file for details.

**Commercial Use**: If you use this software in a commercial product, you must provide clear attribution to Pietro Schirano (@Doriandarko).
