"""
Gemini Writing Agent - An autonomous agent for creative writing tasks.

Originally created by: Pietro Schirano (@Doriandarko)
Enhanced version by: @rzuccolo

This agent uses the Gemini 3 Flash model to create novels, books, 
and short story collections based on user prompts.
"""

import os
import sys
import json
import argparse
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from typing import List, Dict, Any, Union

# Load environment variables from .env file
load_dotenv()

from utils import (
    estimate_token_count, 
    get_tool_definitions, 
    get_tool_map,
    get_system_prompt,
)
from tools.compression import compress_context_impl


# Constants
MAX_ITERATIONS = 300
TOKEN_LIMIT = 1000000  # Gemini has 1M context window
COMPRESSION_THRESHOLD = 900000  # Trigger compression at 90% of limit
MODEL_NAME = "gemini-3-flash-preview"
BACKUP_INTERVAL = 50  # Save backup summary every N iterations


def load_context_from_file(file_path: str) -> str:
    """
    Loads context from a summary file for recovery.
    
    Args:
        file_path: Path to the context summary file
        
    Returns:
        Content of the file as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✓ Loaded context from: {file_path}\n")
        return content
    except Exception as e:
        print(f"✗ Error loading context file: {e}")
        sys.exit(1)


def get_user_input() -> tuple[str, bool]:
    """
    Gets user input from command line, either as a prompt or recovery file.
    
    Returns:
        Tuple of (prompt/context, is_recovery_mode)
    """
    parser = argparse.ArgumentParser(
        description="Gemini Screenplay Writer - Create feature films, TV pilots, and shorts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fresh start with inline prompt
  python writer.py "Write a sci-fi feature film about time travel"
  
  # Interactive mode
  python writer.py
  
  # After generating, publish to PDF:
  python publish.py output/your_project
  
  # Or export to Final Draft:
  python tools/export_fdx.py output/your_project
        """
    )
    
    parser.add_argument(
        'prompt',
        nargs='?',
        help='Your writing request (e.g., "Create a mystery novel")'
    )
    parser.add_argument(
        '--recover',
        type=str,
        help='Path to a context summary file to continue from'
    )
    parser.add_argument(
        '--author',
        type=str,
        default="Gemini Screen Writer by RZ",
        help='The author name to display in the screenplay'
    )
    
    args = parser.parse_args()
    
    # Check if recovery mode
    if args.recover:
        context = load_context_from_file(args.recover)
        return context, True, args.author
    
    # Check if prompt provided as argument
    if args.prompt:
        return args.prompt, False, args.author
    
    # Interactive prompt
    print("=" * 60)
    print("Gemini Screenplay Writer")
    print("=" * 60)
    print("\nEnter your writing request (or 'quit' to exit):")
    print("Example: Write a horror movie set on a submarine\n")
    
    prompt = input("> ").strip()
    
    if prompt.lower() in ['quit', 'exit', 'q']:
        print("Goodbye!")
        sys.exit(0)
    
    if not prompt:
        print("Error: Empty prompt. Please provide a writing request.")
        sys.exit(1)
    
    return prompt, False, args.author


def main():
    """Main agent loop."""
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        api_key = api_key.strip("'\"")
    
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please set your API key in the .env file or Studio settings.")
        sys.exit(1)
    
    # Debug: Show that key is loaded (masked for security)
    if len(api_key) > 8:
        print(f"✓ API Key loaded: {api_key[:4]}...{api_key[-4:]}")
    else:
        print(f"⚠️  Warning: API key seems too short ({len(api_key)} chars)")
    
    # Initialize Gemini client
    client = genai.Client(api_key=api_key)
    
    print(f"✓ Gemini client initialized\n")
    
    # Get user input
    user_prompt, is_recovery, author_name = get_user_input()
    
    # Initialize contents list with raw Content objects
    # This preserves thought_signature and other metadata
    contents: List[types.Content] = []
    
    # Add initial user message
    if is_recovery:
        initial_message = f"[RECOVERED CONTEXT]\n\n{user_prompt}\n\n[END RECOVERED CONTEXT]\n\nPlease continue the work from where we left off."
        print("🔄 Recovery mode: Continuing from previous context\n")
    else:
        # Inject author intent
        initial_message = f"[AUTHOR: {author_name}]\n\n{user_prompt}"
        print(f"\n📝 Task: {user_prompt}")
        print(f"✍️  Author: {author_name}\n")
        
        # Save prompt to memory for the agent to write later
        # Actually, let's just make it a rule in the system prompt.
    
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=initial_message)]
    ))
    
    # Get tool definitions and mapping
    tools = get_tool_definitions()
    tool_map = get_tool_map()
    
    # Get system prompt for config
    system_instruction = get_system_prompt()
    
    print("=" * 60)
    print("Starting Gemini Writing Agent")
    print("=" * 60)
    print(f"Model: {MODEL_NAME}")
    print(f"Max iterations: {MAX_ITERATIONS}")
    print(f"Context limit: {TOKEN_LIMIT:,} tokens")
    print(f"Auto-compression at: {COMPRESSION_THRESHOLD:,} tokens")
    print("=" * 60 + "\n")
    
    # Main agent loop
    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'─' * 60}")
        print(f"Iteration {iteration}/{MAX_ITERATIONS}")
        print(f"{'─' * 60}")
        
        # Check token count before making API call
        try:
            token_count = estimate_token_count(client, MODEL_NAME, contents)
            print(f"📊 Current tokens: {token_count:,}/{TOKEN_LIMIT:,} ({token_count/TOKEN_LIMIT*100:.1f}%)")
            
            # Trigger compression if approaching limit
            if token_count >= COMPRESSION_THRESHOLD:
                print(f"\n⚠️  Approaching token limit! Compressing context...")
                # For compression, convert to simple format
                simple_messages = []
                for content in contents:
                    role = content.role
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        simple_messages.append({"role": role, "content": " ".join(text_parts)})
                
                compression_result = compress_context_impl(
                    messages=[{"role": "system", "content": system_instruction}] + simple_messages,
                    client=client,
                    model=MODEL_NAME,
                    keep_recent=10
                )
                
                if "compressed_messages" in compression_result:
                    # Rebuild contents from compressed messages
                    new_contents = []
                    for msg in compression_result["compressed_messages"]:
                        if msg.get("role") == "system":
                            continue
                        role = "model" if msg.get("role") in ["assistant", "model"] else "user"
                        if msg.get("content"):
                            new_contents.append(types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=msg["content"])]
                            ))
                    contents = new_contents
                    print(f"✓ {compression_result['message']}")
                    print(f"✓ Estimated tokens saved: ~{compression_result.get('tokens_saved', 0):,}")
                    token_count = estimate_token_count(client, MODEL_NAME, contents)
                    print(f"📊 New token count: {token_count:,}/{TOKEN_LIMIT:,}\n")
        
        except Exception as e:
            print(f"⚠️  Warning: Could not estimate token count: {e}")
            token_count = 0
        
        # Auto-backup every N iterations
        if iteration % BACKUP_INTERVAL == 0:
            print(f"💾 Auto-backup (iteration {iteration})...")
            try:
                simple_messages = [{"role": "system", "content": system_instruction}]
                for content in contents:
                    role = content.role
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        simple_messages.append({"role": role, "content": " ".join(text_parts)})
                
                compression_result = compress_context_impl(
                    messages=simple_messages,
                    client=client,
                    model=MODEL_NAME,
                    keep_recent=len(simple_messages)
                )
                if compression_result.get("summary_file"):
                    print(f"✓ Backup saved: {os.path.basename(compression_result['summary_file'])}\n")
            except Exception as e:
                print(f"⚠️  Warning: Backup failed: {e}\n")
        
        # Configure generation with thinking enabled
        generate_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH",
            ),
            tools=[tools],
            temperature=1.0,
        )
        
        # Call the model
        try:
            print("🤖 Calling Gemini model...\n")
            
            # Use non-streaming to get complete response with thought_signature
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=generate_config,
            )
            
            # Process the response
            thinking_text = ""
            content_text = ""
            function_calls_list = []
            
            # Get the model's response content (includes thought_signature)
            model_content = None
            if response.candidates and response.candidates[0].content:
                model_content = response.candidates[0].content
                
                # Process parts for display
                for part in model_content.parts:
                    # Handle thinking parts
                    if hasattr(part, 'thought') and part.thought:
                        if hasattr(part, 'text') and part.text:
                            thinking_text += part.text
                    # Handle function calls
                    elif hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        function_calls_list.append({
                            "name": fc.name,
                            "args": dict(fc.args) if fc.args else {}
                        })
                    # Handle regular text
                    elif hasattr(part, 'text') and part.text:
                        content_text += part.text
            
            # Display thinking
            if thinking_text:
                print("=" * 60)
                print(f"🧠 Thinking (Iteration {iteration})")
                print("=" * 60)
                print(thinking_text)
                print("=" * 60 + "\n")
            
            # Display content
            if content_text:
                print("💬 Response:")
                print("-" * 60)
                print(content_text)
                print("-" * 60 + "\n")
            
            # Display function calls
            if function_calls_list:
                print("🔧 Function calls detected:")
                print("─" * 60)
                for fc in function_calls_list:
                    print(f"  → {fc['name']}")
            
            # CRITICAL: Append the FULL model response to contents
            # This preserves thought_signature for function calling
            if model_content:
                contents.append(model_content)
            
            # Check if the model called any functions
            if not function_calls_list:
                print("=" * 60)
                print("✅ TASK COMPLETED")
                print("=" * 60)
                print(f"Completed in {iteration} iteration(s)")
                print("=" * 60)
                break
            
            # Handle function calls
            print(f"\n🔧 Model decided to call {len(function_calls_list)} tool(s):")
            
            # Collect all function responses
            function_response_parts = []
            
            for fc in function_calls_list:
                func_name = fc["name"]
                args = fc["args"]
                
                print(f"\n  → {func_name}")
                print(f"    Arguments: {json.dumps(args, ensure_ascii=False, indent=6)}")
                
                # Get the tool implementation
                tool_func = tool_map.get(func_name)
                
                if not tool_func:
                    result = f"Error: Unknown tool '{func_name}'"
                    print(f"    ✗ {result}")
                else:
                    # Special handling for compress_context (needs extra params)
                    if func_name == "compress_context":
                        simple_messages = [{"role": "system", "content": system_instruction}]
                        for content in contents:
                            role = content.role
                            text_parts = []
                            for part in content.parts:
                                if hasattr(part, 'text') and part.text:
                                    text_parts.append(part.text)
                            if text_parts:
                                simple_messages.append({"role": role, "content": " ".join(text_parts)})
                        
                        result_data = compress_context_impl(
                            messages=simple_messages,
                            client=client,
                            model=MODEL_NAME,
                            keep_recent=10
                        )
                        result = result_data.get("message", "Compression completed")
                    else:
                        # Call the tool with its arguments
                        result = tool_func(**args)
                    
                    # Print result (truncate if too long)
                    if len(str(result)) > 200:
                        print(f"    ✓ {str(result)[:200]}...")
                    else:
                        print(f"    ✓ {result}")
                
                # Create function response part
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=func_name,
                        response={"result": str(result)}
                    )
                )
            
            # Add all function responses as a single user turn
            contents.append(types.Content(
                role="user",
                parts=function_response_parts
            ))
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user. Saving context...")
            try:
                simple_messages = [{"role": "system", "content": system_instruction}]
                for content in contents:
                    role = content.role
                    text_parts = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        simple_messages.append({"role": role, "content": " ".join(text_parts)})
                
                compression_result = compress_context_impl(
                    messages=simple_messages,
                    client=client,
                    model=MODEL_NAME,
                    keep_recent=len(simple_messages)
                )
                if compression_result.get("summary_file"):
                    print(f"✓ Context saved to: {compression_result['summary_file']}")
                    print(f"\nTo resume, run:")
                    print(f"  python kimi-writer.py --recover {compression_result['summary_file']}")
            except:
                pass
            sys.exit(0)
        
        except Exception as e:
            print(f"\n✗ Error during iteration {iteration}: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("⚠️  Rate limit hit. Sleeping for 20 seconds...")
                time.sleep(20)
            else:
                print(f"Attempting to continue in 5 seconds...\n")
                time.sleep(5)
            continue
    
    # If we hit max iterations
    if iteration >= MAX_ITERATIONS:
        print("\n" + "=" * 60)
        print("⚠️  MAX ITERATIONS REACHED")
        print("=" * 60)
        print(f"\nReached maximum of {MAX_ITERATIONS} iterations.")
        print("Saving final context...")
        
        try:
            simple_messages = [{"role": "system", "content": system_instruction}]
            for content in contents:
                role = content.role
                text_parts = []
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    simple_messages.append({"role": role, "content": " ".join(text_parts)})
            
            compression_result = compress_context_impl(
                messages=simple_messages,
                client=client,
                model=MODEL_NAME,
                keep_recent=len(simple_messages)
            )
            if compression_result.get("summary_file"):
                print(f"✓ Context saved to: {compression_result['summary_file']}")
                print(f"\nTo resume, run:")
                print(f"  python kimi-writer.py --recover {compression_result['summary_file']}")
        except Exception as e:
            print(f"✗ Error saving context: {e}")


if __name__ == "__main__":
    main()
