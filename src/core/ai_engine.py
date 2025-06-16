"""
AI Engine for Gemini 1.5 Pro API - Enhanced and robust version.

Requirements:
    pip install --upgrade google-generativeai
    .env file with GOOGLE_API_KEY
"""

import os
import re
import json
from typing import Dict, List, Tuple, Any
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────────
MODEL_NAME = "models/gemini-1.5-pro-latest"
API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "Missing GOOGLE_API_KEY environment variable. "
        "Create one at https://aistudio.google.com/app/apikey and add it to your .env file"
    )

try:
    genai.configure(api_key=API_KEY)
    # Connection test
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    raise RuntimeError(f"Error configuring Gemini API: {e}")

# Function to get current date dynamically
def get_current_date():
    """Get current date in YYYY-MM-DD format"""
    return datetime.now().strftime("%Y-%m-%d")

# ── Function definitions for the AI ─────────────────────────────────────────
def get_system_prompt():
    """Generate system prompt with current date"""
    today = get_current_date()
    return f"""
You are an AI assistant specialized in budget management and personal finance.

AVAILABLE COMMANDS:
When the user wants to record, delete or query expenses, respond EXACTLY with one of these commands:

1. To record an expense:
FUNCTION_CALL: insert_payment
ARGUMENTS: {{"amount": <number>, "category": "<category>", "description": "<description>", "date": "<YYYY-MM-DD>"}}

2. To delete an expense:
FUNCTION_CALL: delete_payment
ARGUMENTS: {{"expense_id": <number>}}

3. To query expenses by category:
FUNCTION_CALL: query_expenses_by_category
ARGUMENTS: {{"category": "<category>"}}

4. To list all expenses in a category (with IDs):
FUNCTION_CALL: list_expenses_by_category
ARGUMENTS: {{"category": "<category>"}}

VALID CATEGORIES: "Groceries", "Electronics", "Entertainment", "Other"

IMPORTANT:
- If the user just wants to chat, respond normally
- If you need to execute a function, use EXACTLY the format shown above
- For dates, use YYYY-MM-DD format
- If no date is specified, use today's date: {today}
- Always validate amounts are positive numbers
- Be helpful and friendly in your responses

EXAMPLES:
User: "Record a $50 expense for groceries"
Response:
FUNCTION_CALL: insert_payment
ARGUMENTS: {{"amount": 50, "category": "Groceries", "description": "groceries", "date": "{today}"}}

User: "How much have I spent on entertainment?"
Response:
FUNCTION_CALL: query_expenses_by_category
ARGUMENTS: {{"category": "Entertainment"}}

User: "Delete expense with ID 5"
Response:
FUNCTION_CALL: delete_payment
ARGUMENTS: {{"expense_id": 5}}

User: "Hello, how are you?"
Response: Hello! I'm doing well, thanks. I'm your budget assistant. How can I help you today?
"""

def chat_completion(history: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    Handle a conversation with Gemini 1.5 Pro from a history.

    Args:
        history (list): List of tuples with format [("user", "..."), ("assistant", "...")]

    Returns:
        dict: {"type": "text", "content": ...} or {"type": "function_call", "name": ..., "arguments": ...}
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        # Prepare history in the format Gemini expects
        gemini_history = []
        # Add system prompt as first message with current date
        system_prompt = get_system_prompt()
        gemini_history.append({
            "role": "user", 
            "parts": [system_prompt]
        })
        gemini_history.append({
            "role": "model", 
            "parts": ["Understood. I'm your budget assistant and I'm ready to help you manage your expenses."]
        })

        # Convert history
        for role, content in history:
            gemini_role = "model" if role == "assistant" else "user"
            gemini_history.append({
                "role": gemini_role, 
                "parts": [content]
            })

        if not gemini_history or gemini_history[-1]["role"] != "user":
            raise ValueError("History is empty or last message is not from user.")

        # Extract the last user message
        last_message = gemini_history.pop()

        # Create chat with previous history
        chat = model.start_chat(history=gemini_history)

        # Send the new user message
        response = chat.send_message(last_message["parts"][0])
        reply_text = response.text.strip()

        # Detect if it's a function call
        if "FUNCTION_CALL:" in reply_text and "ARGUMENTS:" in reply_text:
            return _parse_function_call(reply_text)
        else:
            # Normal response
            return {
                "type": "text",
                "content": reply_text,
            }

    except Exception as e:
        error_message = str(e)
        if "429" in error_message and "quota" in error_message.lower():
            return {
                "type": "text",
                "content": "⚠️ You've reached your Gemini free usage limit. Please wait a while or switch API keys."
            }
        return {
            "type": "text",
            "content": f"⚠️ Error communicating with API: {error_message}",
        }

def _parse_function_call(text: str) -> Dict[str, Any]:
    """
    Parse a function call response from the specified format.
    
    Args:
        text: Text with format "FUNCTION_CALL: name\nARGUMENTS: {json}"
    
    Returns:
        Dict with type, name and arguments
    """
    try:
        # Extract function name
        function_match = re.search(r'FUNCTION_CALL:\s*(\w+)', text)
        if not function_match:
            raise ValueError("Function name not found")
        
        function_name = function_match.group(1)
        
        # Extract JSON arguments - improved regex
        # Look for the JSON object after ARGUMENTS:
        args_match = re.search(r'ARGUMENTS:\s*(\{[^}]+\})', text, re.DOTALL)
        if not args_match:
            raise ValueError("Arguments not found")
        
        args_json = args_match.group(1)
        
        # Clean up the JSON string
        # Remove any newlines within the JSON
        args_json = args_json.replace('\n', ' ')
        
        # Parse JSON
        arguments = json.loads(args_json)
        
        # Validate function name
        valid_functions = ["insert_payment", "delete_payment", "query_expenses_by_category", "list_expenses_by_category"]
        if function_name not in valid_functions:
            raise ValueError(f"Invalid function: {function_name}")
        
        # Validate arguments based on function
        if function_name == "insert_payment":
            if "amount" not in arguments:
                raise ValueError("Missing 'amount' in arguments")
            if arguments["amount"] <= 0:
                raise ValueError("Amount must be positive")
            if "category" not in arguments:
                raise ValueError("Missing 'category' in arguments")
            if "date" not in arguments:
                arguments["date"] = get_current_date()
            if "description" not in arguments:
                arguments["description"] = ""
                
        elif function_name == "delete_payment":
            if "expense_id" not in arguments:
                raise ValueError("Missing 'expense_id' in arguments")
            if not isinstance(arguments["expense_id"], int):
                arguments["expense_id"] = int(arguments["expense_id"])
                
        elif function_name == "query_expenses_by_category":
            if "category" not in arguments:
                raise ValueError("Missing 'category' in arguments")
        
        elif function_name == "list_expenses_by_category":
            if "category" not in arguments:
                raise ValueError("Missing 'category' in arguments")

        
        return {
            "type": "function_call",
            "name": function_name,
            "arguments": arguments,
        }
        
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "type": "text",
            "content": f"I understood you want to manage expenses, but I couldn't process the command correctly. Error: {str(e)}. Please try rephrasing your request.",
        }

def test_api_connection() -> bool:
    """
    Test connection with Gemini API.
    
    Returns:
        bool: True if connection is successful
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content("Say 'test'")
        return "test" in response.text.lower()
    except Exception:
        return False

# Additional helper functions
def get_expense_insights(expenses_summary: Dict[str, float]) -> str:
    """Generate insights from expense summary"""
    if not expenses_summary:
        return "No expenses recorded yet."
    
    total = sum(expenses_summary.values())
    insights = [f"Total expenses: ${total:.2f}"]
    
    # Find highest category
    if expenses_summary:
        highest_category = max(expenses_summary.items(), key=lambda x: x[1])
        insights.append(f"Highest spending: {highest_category[0]} (${highest_category[1]:.2f})")
    
    return "\n".join(insights)

if __name__ == "__main__":
    # Basic test
    print("🤖 AI Engine Test")
    print(f"📅 Current date: {get_current_date()}")
    
    if test_api_connection():
        print("✅ Gemini API connection successful")
        
        # Test chat
        test_history = [("user", "Hello, how are you?")]
        result = chat_completion(test_history)
        print(f"Test response type: {result['type']}")
        print(f"Test response content: {result['content'][:100]}...")
        
        # Test function parsing
        test_history2 = [("user", "Record a $50 expense for groceries")]
        result2 = chat_completion(test_history2)
        print(f"\nFunction call test: {result2}")
    else:
        print("❌ Failed to connect to Gemini API")