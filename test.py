"""
Test script for Google Generative AI (google.generativeai) library.
Tests the Gemini 3 Pro Preview model with various prompts.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai


def load_api_key():
    """Load the GEMINI_API_KEY from the .env file."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    return api_key


def configure_genai(api_key: str):
    """Configure the Google Generative AI library with the API key."""
    genai.configure(api_key=api_key)


def test_simple_text_generation():
    """Test simple text generation with Gemini 3 Pro Preview."""
    print("\n" + "=" * 50)
    print("Test 1: Simple Text Generation")
    print("=" * 50)
    
    model = genai.GenerativeModel("gemini-3-pro-preview")
    response = model.generate_content("What is the capital of France?")
    
    print(f"Prompt: What is the capital of France?")
    print(f"Response: {response.text}")
    return True


def test_creative_writing():
    """Test creative writing capabilities."""
    print("\n" + "=" * 50)
    print("Test 2: Creative Writing")
    print("=" * 50)
    
    model = genai.GenerativeModel("gemini-3-pro-preview")
    response = model.generate_content(
        "Write a short haiku about programming."
    )
    
    print(f"Prompt: Write a short haiku about programming.")
    print(f"Response:\n{response.text}")
    return True


def test_code_generation():
    """Test code generation capabilities."""
    print("\n" + "=" * 50)
    print("Test 3: Code Generation")
    print("=" * 50)
    
    model = genai.GenerativeModel("gemini-3-pro-preview")
    response = model.generate_content(
        "Write a Python function that calculates the factorial of a number."
    )
    
    print(f"Prompt: Write a Python function that calculates the factorial of a number.")
    print(f"Response:\n{response.text}")
    return True


def test_conversation():
    """Test multi-turn conversation using chat."""
    print("\n" + "=" * 50)
    print("Test 4: Multi-turn Conversation")
    print("=" * 50)
    
    model = genai.GenerativeModel("gemini-3-pro-preview")
    chat = model.start_chat(history=[])
    
    response1 = chat.send_message("Hello! My name is John.")
    print(f"User: Hello! My name is John.")
    print(f"Model: {response1.text}")
    
    response2 = chat.send_message("What is my name?")
    print(f"\nUser: What is my name?")
    print(f"Model: {response2.text}")
    return True


def test_with_generation_config():
    """Test text generation with custom configuration."""
    print("\n" + "=" * 50)
    print("Test 5: Custom Generation Config")
    print("=" * 50)
    
    model = genai.GenerativeModel("gemini-3-pro-preview")
    
    generation_config = genai.GenerationConfig(
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        max_output_tokens=256,
    )
    
    response = model.generate_content(
        "Explain quantum computing in one sentence.",
        generation_config=generation_config
    )
    
    print(f"Prompt: Explain quantum computing in one sentence.")
    print(f"Temperature: 0.7, Top-P: 0.9, Top-K: 40")
    print(f"Response: {response.text}")
    return True


def test_list_models():
    """List available models."""
    print("\n" + "=" * 50)
    print("Test 6: List Available Models")
    print("=" * 50)
    
    models = genai.list_models()
    print("Available Gemini models:")
    for model in models:
        if "gemini" in model.name.lower():
            print(f"  - {model.name}")
    return True


def main():
    """Main function to run all tests."""
    print("=" * 50)
    print("Google Generative AI Library Test")
    print("Model: gemini-3-pro-preview")
    print("=" * 50)
    
    try:
        api_key = load_api_key()
        configure_genai(api_key)
        print("✓ API Key loaded and configured successfully")
    except ValueError as e:
        print(f"✗ Error: {e}")
        return
    
    tests = [
        ("Simple Text Generation", test_simple_text_generation),
        ("Creative Writing", test_creative_writing),
        ("Code Generation", test_code_generation),
        ("Multi-turn Conversation", test_conversation),
        ("Custom Generation Config", test_with_generation_config),
        ("List Available Models", test_list_models),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"\n✓ {test_name} - PASSED")
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_name} - FAILED: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)


if __name__ == "__main__":
    main()
