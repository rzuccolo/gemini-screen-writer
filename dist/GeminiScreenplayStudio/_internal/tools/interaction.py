"""
Interaction tools for the Gemini Writing Agent.
"""

def ask_user_impl(question: str) -> str:
    """
    Asks the user a question and waits for their input.
    
    Args:
        question: The question to ask the user
        
    Returns:
        The user's response
    """
    print("\n" + "=" * 60)
    print("❓ AGENT QUESTION")
    print("=" * 60)
    print(f"{question}")
    print("-" * 60)
    
    try:
        response = input("> ").strip()
        print("\n")
        return response
    except EOFError:
        print("\n⚠️  Input stream closed. Exiting...")
        import sys
        sys.exit(0)
    except Exception as e:
        print(f"\n⚠️  Error reading input: {e}")
        # Critical failure: Cannot get user input, so we must stop.
        import sys
        sys.exit(1)
