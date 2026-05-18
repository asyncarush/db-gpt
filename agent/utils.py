import json
import re
from langchain_core.messages import AIMessage

def safe_model_invoke(llm_with_tools, messages):
    """Wrapper to handle malformed tool calls from Llama on Groq"""
    try:
        return llm_with_tools.invoke(messages)
    except Exception as e:
        error_str = str(e)
        
        # Extract the malformed function call from error
        # Pattern: <function=tool_name={"key": "value"}>
        # or: <function=tool_name {"key": "value"}>
        pattern = r'<function=(\w+)[=\s](\{.*?\})\s*>'
        match = re.search(pattern, error_str, re.DOTALL)
        
        if match:
            tool_name = match.group(1)
            try:
                tool_args = json.loads(match.group(2))
                # Reconstruct a proper AIMessage with tool call
                return AIMessage(
                    content="",
                    tool_calls=[{
                        "name": tool_name,
                        "args": tool_args,
                        "id": f"recovered_{tool_name}",
                        "type": "tool_call"
                    }]
                )
            except json.JSONDecodeError:
                raise e
        raise e