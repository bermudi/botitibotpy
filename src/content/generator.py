from typing import Optional, Dict, Any
from llama_index import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    ServiceContext,
    LLMPredictor,
    PromptHelper
)
from llama_index.llms import OpenAI
from ..config import Config

class ContentGenerator:
    def __init__(self):
        """Initialize the content generator with LlamaIndex components"""
        # Set up LLM predictor with OpenAI
        llm_predictor = LLMPredictor(
            llm=OpenAI(
                temperature=0.7,
                model="gpt-3.5-turbo",
                api_key=Config.OPENAI_API_KEY
            )
        )
        
        # Configure prompt helper for token limits
        prompt_helper = PromptHelper(
            max_input_size=4096,
            num_output=512,
            max_chunk_overlap=20
        )
        
        # Create service context
        self.service_context = ServiceContext.from_defaults(
            llm_predictor=llm_predictor,
            prompt_helper=prompt_helper
        )
        
        self.index = None
        
    def load_content_source(self, directory_path: str) -> bool:
        """Load content from a directory to use as source material"""
        try:
            documents = SimpleDirectoryReader(directory_path).load_data()
            self.index = VectorStoreIndex.from_documents(
                documents,
                service_context=self.service_context
            )
            return True
        except Exception as e:
            print(f"Error loading content source: {e}")
            return False
            
    def generate_post(self, 
                     prompt: str,
                     max_length: Optional[int] = None,
                     tone: Optional[str] = None,
                     style: Optional[str] = None) -> Optional[str]:
        """Generate a social media post based on the provided parameters"""
        try:
            if not self.index:
                raise ValueError("No content source loaded. Call load_content_source first.")
            
            # Build the complete prompt with style parameters
            complete_prompt = self._build_generation_prompt(prompt, max_length, tone, style)
            
            # Query the index
            query_engine = self.index.as_query_engine()
            response = query_engine.query(complete_prompt)
            
            return str(response)
            
        except Exception as e:
            print(f"Error generating post: {e}")
            return None
            
    def _build_generation_prompt(self,
                               base_prompt: str,
                               max_length: Optional[int] = None,
                               tone: Optional[str] = None,
                               style: Optional[str] = None) -> str:
        """Build a complete prompt incorporating all parameters"""
        prompt_parts = [base_prompt]
        
        if max_length:
            prompt_parts.append(f"Keep the response under {max_length} characters.")
            
        if tone:
            prompt_parts.append(f"Use a {tone} tone.")
            
        if style:
            prompt_parts.append(f"Write in a {style} style.")
            
        return " ".join(prompt_parts) 