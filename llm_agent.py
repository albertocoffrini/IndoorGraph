# llm_agent.py

import requests
import json
from IndoorLLM_tool import compute_navigation

OLLAMA_URL = "http://localhost:11434/api/chat"
# MODEL = "llama3-groq-tool-use:latest"
# MODEL = "qwen2.5-coder:7b"
MODEL = "llama3.1:8b"
# MODEL = "qwen3.5:2b"

tools = [
    {
        "type": "function",
        "function": {
            "name": "compute_navigation",
            "description": "COMPUTE an indoor navigation path. If the profile is not specified, use 'all' automatically without asking the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string",
                                    "description": "Starting node id. The id is formed by numbers and letters. Use only the id, Never use 'position X' or 'number X' or 'point X'."},
                    "goal": {"type": "string",
                                    "description": "Goal node id. The id is formed by numbers and letters. Use only the id, Never use 'position X' or 'number X' or 'point X'."},
                    "profile": {
                        "type": "string",
                        "enum": [
                            "all",
                            "accessible",
                            "only_elevator",
                            "no_elevator",
                            "only_stairs",
                            "corridor_only"
                        ],
                        "description": "Navigation profile. If not provided, use 'all'. DO NOT ask the user."
                    }
                },
                "required": ["start", "goal"]
            }
        }
    }
    
]



def ask_llm(user_input):

    messages = [
        {
            "role": "system",
            "content": "You are an indoor navigation assistant.Convert raw navigation logs into clear directions while preserving ALL navigation data exactly.Rules:Keep all movement directions EXACTLY as given (LEFT, RIGHT, STRAIGHT, SLIGHT LEFT, U-TURN). Do NOT change or approximate directions.Keep the exact order of all navigation steps.Do NOT skip any movement step.Positional information (on your left/right/straight) must remain unchanged.You may simplify wording, but NEVER modify directions or their meaning.Remove only redundant system messages (e.g., Arrived at).Sound natural, but accuracy is more important than naturalness.Before producing the final answer, internally verify that: All directions match the input exactly"
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "tools": tools,
            "stream": False
        }
    )

    result = response.json()
    message = result["message"]


    # print("LLM response:", message)
    # print("LLM response (raw):", json.dumps(message, indent=2))
    
    if "tool_calls" in message:
        tool_call = message["tool_calls"][0]
        function_name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]

        print("Called tool:", function_name)
        print("Arguments:", arguments)

        tool_result = compute_navigation(
            start=arguments["start"],
            goal=arguments["goal"],
            profile=arguments["profile"]
        )

        messages.append(message)

        messages.append({
            "role": "tool",
            "name": function_name,
            "content": json.dumps(tool_result)
        })

        second_response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False
            }
        )

        final_answer = second_response.json()["message"]["content"]
        return final_answer

    else:
        return message["content"]



if __name__ == "__main__":
    while True:
        user_input = input("\nUser: ")
        answer = ask_llm(user_input)
        print("\nNavigation Assistant:", answer)
