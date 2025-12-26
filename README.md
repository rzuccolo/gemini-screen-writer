# Gemini Screenplay Writer

An autonomous agent powered by **Google's Gemini 3 Flash** model for creating industry-standard screenplays, including Feature Films, TV Pilots, and Shorts.

## Features

- 🤖 **Autonomous Screenwriting**: The agent plans and executes screenplay writing tasks independently.
- 🎬 **Industry Standards**: Generates professional deliverables including Beat Sheets, Character Breakdowns, and formatted Scripts.
- 💬 **Interactive Mode**: Intelligent clarification system - calls `ask_user` when formats or genres are ambiguous (e.g., "Feature or Short?").
- ⚡ **Real-Time Streaming**: See the agent's thinking and writing appear as it's generated.
- 💾 **Smart Context Management**: Automatically compresses context when approaching token limits (1M window).
- 🔄 **Recovery Mode**: Resume interrupted work from saved context summaries.
- 📊 **Token Monitoring**: Real-time tracking of token usage with automatic optimization.

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

## Usage

### Interactive Mode (Recommended)

Run without arguments to start the interactive writer:
```bash
uv run writer.py
# or: python writer.py
```
*The agent will greet you and ask for your request. If you are vague (e.g., "Write a sci-fi movie"), it will ask clarifying questions about format, stats, etc.*

### One-Shot Prompt

Run with an inline prompt if you know exactly what you want:
```bash
uv run writer.py "Write a 90-page Horror Feature Film called 'The Deep'. Include a beat sheet."
```

### Recovery Mode

If the agent is interrupted or you want to continue previous work:
```bash
uv run writer.py --recover output/my_project/.context_summary_20250107_143022.md
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
output/
├── The_Deep_Project/     # Created by the agent
│   ├── cover.md          # Title, Logline, Stats
│   ├── characters.md     # Character Arcs
│   ├── beat_sheet.md     # Structural Breakdown (Save the Cat)
│   ├── script.md         # The Screenplay
│   └── .context_summary_*.md
└── ...
```

## Supported Formats

The agent understands and formats for:
*   **Feature Film** (90-120 pages)
*   **TV Pilot** (30-60 pages)
*   **TV Episode** (22-60 pages)
*   **Short Film** (5-40 pages)
*   **Web Series** (5-15 pages)

## Artifacts Generated

1.  **Cover Page** (`cover.md`): Logline, synopsis, genre, title, and estimated stats.
2.  **Beat Sheet** (`beat_sheet.md`): Full structural breakdown (Acts I, II, III).
3.  **Character List** (`characters.md`): Descriptions, arcs, and traits.
4.  **Script** (`script.md`): The actual screenplay in Markdown format (Scene Headings, Dialogue, Action).

## Technical Details

- **Model**: gemini-3-flash-preview
- **Thinking Level**: HIGH (for better reasoning)
- **Context Window**: 1,000,000 tokens
- **Max Iterations**: 300

## License

MIT License with Attribution Requirement - see [LICENSE](LICENSE) file for details.

**Commercial Use**: If you use this software in a commercial product, you must provide clear attribution to Pietro Schirano (@Doriandarko).
