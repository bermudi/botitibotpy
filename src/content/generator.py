import time
from typing import Optional, Dict, Any
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.gemini import GeminiEmbedding
from ..config import Config
import os

class ContentGenerator:
    def __init__(self):
        """Initialize the content generator with LlamaIndex components"""
        # Configure LlamaIndex to use Gemini embeddings
        Settings.embed_model = GeminiEmbedding(
            model_name="models/embedding-001",
            api_key=Config.GOOGLE_API_KEY
        )
        
        self.llm = OpenAI(
            temperature=0.7,
            model=Config.OPENAI_API_MODEL,
            api_base=Config.OPENAI_API_BASE,
            api_key=Config.OPENAI_API_KEY
        )
        self.index = None
        
    def load_content_source(self, directory_path: str) -> bool:
        """Load content from a directory to use as source material"""
        try:
            print(f"Attempting to load content from: {os.path.abspath(directory_path)}")
            if not os.path.exists(directory_path):
                print(f"Directory does not exist: {directory_path}")
                return False
                
            files = os.listdir(directory_path)
            print(f"Found files: {files}")
            
            documents = SimpleDirectoryReader(directory_path).load_data()
            print(f"Loaded {len(documents)} documents")
            
            self.index = VectorStoreIndex.from_documents(documents)
            return True
        except Exception as e:
            print(f"Error loading content source: {str(e)}")
            print(f"Error type: {type(e)}")
            return False
            
    def generate_post(self, prompt: str, max_length: Optional[int] = None,
                 tone: Optional[str] = None, style: Optional[str] = None) -> Optional[str]:
        try:
            if not self.index:
                raise ValueError("No content source loaded. Call load_content_source first.")
            
            complete_prompt = self._build_generation_prompt(prompt, max_length, tone, style)
            query_engine = self.index.as_query_engine()
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = query_engine.query(complete_prompt)
                    return str(response)
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"Final attempt failed: {str(e)}")
                        return None
                    print(f"Attempt {attempt + 1} failed, retrying...")
                    time.sleep(1)
                                    
        except Exception as e:
            print(f"Error generating post: {str(e)}")
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
