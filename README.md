# Gemini Writing Agent

An autonomous agent powered by **Google's Gemini 3 Flash** model for creating novels, books, and short story collections.

## Features

- 🤖 **Autonomous Writing**: The agent plans and executes creative writing tasks independently
- 📚 **Multiple Formats**: Create novels, books, or short story collections
- ⚡ **Real-Time Streaming**: See the agent's thinking and writing appear as it's generated
- 💾 **Smart Context Management**: Automatically compresses context when approaching token limits
- 🔄 **Recovery Mode**: Resume interrupted work from saved context summaries
- 📊 **Token Monitoring**: Real-time tracking of token usage with automatic optimization
- 🛠️ **Tool Use**: Agent can create projects, write files, and manage its workspace
- 🧠 **Advanced Thinking**: Uses Gemini's thinking mode for better reasoning

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

### Fresh Start

Run with an inline prompt:
```bash
# Using uv (recommended)
uv run writer.py "Create a collection of 5 sci-fi short stories about AI"

# Or using python directly
python writer.py "Create a collection of 5 sci-fi short stories about AI"
```

Or run interactively:
```bash
uv run writer.py
# or: python writer.py
```
Then enter your prompt when asked.

### Recovery Mode

If the agent is interrupted or you want to continue previous work:
```bash
uv run writer.py --recover output/my_project/.context_summary_20250107_143022.md
# or: python writer.py --recover output/my_project/.context_summary_20250107_143022.md
```

## How It Works

### The Agent's Tools

The agent has access to three tools:

1. **create_project**: Creates a project folder to organize the writing
2. **write_file**: Writes markdown files with three modes:
   - `create`: Creates a new file (fails if exists)
   - `append`: Adds content to an existing file
   - `overwrite`: Replaces the entire file content
3. **compress_context**: Automatically triggered to manage context size

### The Agentic Loop

1. The agent receives your prompt
2. It reasons about the task using Gemini's thinking mode
3. It decides which tools to call and executes them
4. It reviews the results and continues until the task is complete
5. Maximum 300 iterations with automatic context compression

### Context Management

- **Token Limit**: 1,000,000 tokens (Gemini's large context window)
- **Auto-Compression**: Triggers at 900,000 tokens (90% of limit)
- **Backups**: Automatic context summaries every 50 iterations
- **Recovery**: All summaries saved with timestamps for resumption

## Project Structure

```
kimi-writer/
├── writer.py        # Main agent
├── tools/
│   ├── __init__.py       # Tool registry
│   ├── writer.py         # File writing tool
│   ├── project.py        # Project management tool
│   └── compression.py    # Context compression tool
├── utils.py              # Utilities (token counting, etc.)
├── requirements.txt      # Python dependencies
├── env.example           # Example configuration
├── .gitignore            # Git ignore rules
└── README.md             # This file

# Generated during use:
output/                   # All AI-generated projects go here
├── your_project_name/    # Created by the agent
│   ├── chapter_01.md     # Written by the agent
│   ├── chapter_02.md
│   └── .context_summary_*.md  # Auto-saved context summaries
└── another_project/
    └── ...
```

## Examples

### Example 1: Novel
```bash
uv run writer.py "Write a mystery novel set in Victorian London with 10 chapters"
```

### Example 2: Short Story Collection
```bash
uv run writer.py "Create 7 interconnected sci-fi short stories exploring the theme of memory"
```

### Example 3: Book
```bash
uv run writer.py "Write a comprehensive guide to Python programming with 15 chapters"
```

## Advanced Features

### Real-Time Streaming
Watch the agent think and write in real-time:
- 🧠 **Thinking Stream**: See the agent's thought process as it plans (Gemini's thinking mode)
- 💬 **Content Stream**: Watch stories being written character by character
- 🔧 **Tool Call Progress**: Live updates when generating large content
- ⚡ **No Waiting**: Immediate feedback - no more staring at a blank screen

### Iteration Counter
The agent displays its progress: `Iteration X/300`

### Token Monitoring
Real-time token usage: `Current tokens: 45,234/1,000,000 (4.5%)`

### Graceful Interruption
Press `Ctrl+C` to interrupt. The agent will save the current context for recovery.

## Tips for Best Results

1. **Be Specific**: Clear prompts get better results
   - Good: "Create a 5-chapter romance novel set in modern Tokyo"
   - Less good: "Write something interesting"

2. **Let It Work**: The agent works autonomously - it will plan and execute the full task

3. **Recovery is Easy**: If interrupted, just use the `--recover` flag with the latest context summary

4. **Check Progress**: Generated files appear in real-time in the project folder

## Troubleshooting

### "GEMINI_API_KEY environment variable not set"
Make sure you have created a `.env` file in the project root with your API key:
```bash
GEMINI_API_KEY=your-actual-api-key-here
```

### "401 Unauthorized" or Authentication errors
- Verify your API key is correct in the `.env` file
- Get your API key from: https://aistudio.google.com/app/apikey

### "Error creating project folder"
Check write permissions in the current directory

### Agent seems stuck
The agent can run up to 300 iterations. For very complex tasks, this is normal. Check the project folder to see progress.

### Token limit issues
The agent automatically compresses context at 900K tokens. If you see compression messages, the system is working correctly.

## Technical Details

- **Model**: gemini-3-flash-preview
- **Thinking Level**: HIGH (for better reasoning)
- **Temperature**: 1.0
- **Context Window**: 1,000,000 tokens
- **Max Iterations**: 300
- **Compression Threshold**: 900,000 tokens

You can customize these settings in `writer.py`.

## License

MIT License with Attribution Requirement - see [LICENSE](LICENSE) file for details.

**Commercial Use**: If you use this software in a commercial product, you must provide clear attribution to Pietro Schirano (@Doriandarko).

**API Usage**: This project uses the Google Gemini API. Please refer to Google's terms of service for API usage guidelines.

## Credits

- **Originally Created by**: Pietro Schirano ([@Doriandarko](https://github.com/Doriandarko))
- **Enhanced Version by**: [@rzuccolo](https://github.com/rzuccolo) ([rzuccolo/gemini-book-writer](https://github.com/rzuccolo/gemini-book-writer))
- **Powered by**: Google's Gemini 3 Flash model
- **Original Repository**: https://github.com/Doriandarko/gemini-writer


