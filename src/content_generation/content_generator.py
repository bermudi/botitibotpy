from llama_index import VectorStoreIndex, SimpleDirectoryReader, ServiceContext
from llama_index.llms import OpenAI
from llama_index.prompts import PromptTemplate
import os

class ContentGenerator:
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.7):
        """
        Initializes the content generator with LlamaIndex configuration.

        Args:
            model_name: The name of the LLM model to use.
            temperature: The temperature parameter for content generation.
        """
        self.llm = OpenAI(model=model_name, temperature=temperature)
        self.service_context = ServiceContext.from_defaults(llm=self.llm)
        
        # Define content generation prompt template
        self.prompt_template = PromptTemplate(
            "You are a social media content creator. Create engaging content based on the following prompt:\n"
            "Prompt: {prompt}\n"
            "Consider the platform's character limits and best practices for engagement."
        )

    def generate_content(self, prompt: str, max_length: int = 280) -> str:
        """
        Generates content using LlamaIndex based on the given prompt.

        Args:
            prompt: The prompt to generate content from.
            max_length: Maximum length of the generated content.

        Returns:
            The generated content.
        """
        try:
            # Create index with the prompt
            index = VectorStoreIndex.from_documents(
                [], service_context=self.service_context
            )
            
            # Create query engine with length constraint
            query_engine = index.as_query_engine(
                response_mode="compact",
                text_qa_template=self.prompt_template,
                similarity_top_k=1
            )
            
            # Generate content
            response = query_engine.query(
                f"{prompt}. Keep the response under {max_length} characters."
            )
            
            return str(response).strip()
        except Exception as e:
            return f"Error generating content: {str(e)}"

def generate_content(prompt: str, max_length: int = 280) -> str:
    """
    Convenience function for generating content using default settings.

    Args:
        prompt: The prompt to generate content from.
        max_length: Maximum length of the generated content.

    Returns:
        The generated content.
    """
    generator = ContentGenerator()
    return generator.generate_content(prompt, max_length)

if __name__ == '__main__':
    # Test with different content types
    test_prompt = "Write a short tweet about the benefits of using LLMs for content creation."
    generated_content = generate_content(test_prompt)
    print(f"Generated content: {generated_content}")

    # Test with longer content
    blog_prompt = "Write a 200-word blog post about AI in social media marketing."
    blog_content = generate_content(blog_prompt, max_length=200)
    print(f"\nGenerated blog content: {blog_content}")
