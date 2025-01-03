from src.content.generator import ContentGenerator

def main():
    # Initialize the content generator
    generator = ContentGenerator()
    
    # Test different direct prompts
    
    # Simple question
    prompt = "What is the capital of France?"
    response = generator.direct_prompt(prompt)
    print("\nSimple question:")
    print(f"Prompt: {prompt}")
    print(f"Response: {response}")
    
    # Creative writing
    prompt = "Write a haiku about programming"
    response = generator.direct_prompt(prompt)
    print("\nCreative writing:")
    print(f"Prompt: {prompt}")
    print(f"Response: {response}")
    
    # Technical explanation
    prompt = "Explain how a hash table works in simple terms"
    response = generator.direct_prompt(prompt)
    print("\nTechnical explanation:")
    print(f"Prompt: {prompt}")
    print(f"Response: {response}")

if __name__ == "__main__":
    main()
