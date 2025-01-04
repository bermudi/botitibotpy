import time
import logging
import os
import hashlib
from typing import Optional, Dict, Any, List
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.gemini import GeminiEmbedding
import chromadb
from ..config import Config

class ContentGenerator:
    def __init__(self):
        """Initialize the content generator with LlamaIndex and ChromaDB components"""
        # Configure logging
        logging.basicConfig(level=logging.DEBUG)
        
        # Initialize Gemini embedding model
        self.embed_model = GeminiEmbedding(
            model_name="models/embedding-001",
            api_key=Config.GOOGLE_API_KEY
        )
        Settings.embed_model = self.embed_model
        
        # Configure LlamaIndex LLM settings
        Settings.llm = OpenAI(
            temperature=0.7,
            model=Config.OPENAI_API_MODEL,
            api_base=Config.OPENAI_API_BASE,
            api_key=Config.OPENAI_API_KEY
        )
        
        self.llm = Settings.llm
        self.index = None
        self.persist_dir = "chroma_db"
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection_name = "content_collection"
        self.chroma_collection = self.chroma_client.get_or_create_collection(self.collection_name)
        
        # Initialize vector store
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # Track document hashes
        self.document_hashes = {}
    
    def _calculate_document_hash(self, content: str) -> str:
        """Calculate a hash for document content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_document_id(self, filepath: str, content: str) -> str:
        """Generate a unique document ID combining filepath and content hash."""
        return f"{filepath}_{self._calculate_document_hash(content)}"

    def load_index(self) -> bool:
        """Load the vector store index from ChromaDB."""
        try:
            if self.chroma_collection.count() > 0:
                self.index = VectorStoreIndex.from_vector_store(
                    self.vector_store,
                    embed_model=self.embed_model
                )
                print(f"Index loaded from {self.persist_dir}")
                return True
            return False
        except Exception as e:
            print(f"Error loading index: {str(e)}")
            return False

    def load_content_source(self, directory_path: str) -> bool:
        """Load content from a directory, updating only if documents have changed."""
        try:
            print(f"Checking content in: {os.path.abspath(directory_path)}")
            if not os.path.exists(directory_path):
                print(f"Directory does not exist: {directory_path}")
                return False

            # Load documents
            documents = SimpleDirectoryReader(directory_path).load_data()
            print(f"Found {len(documents)} documents")

            # Track new or modified documents
            new_docs = []
            new_ids = []
            new_metadata = []

            for doc in documents:
                doc_hash = self._calculate_document_hash(doc.text)
                doc_id = self._get_document_id(doc.metadata.get('file_path', 'unknown'), doc.text)
                
                # Check if document is new or modified
                if doc_id not in self.document_hashes or self.document_hashes[doc_id] != doc_hash:
                    new_docs.append(doc)
                    new_ids.append(doc_id)
                    new_metadata.append({
                        "file_path": doc.metadata.get('file_path', 'unknown'),
                        "hash": doc_hash
                    })
                    self.document_hashes[doc_id] = doc_hash

            if new_docs:
                print(f"Adding/updating {len(new_docs)} documents")
                # Create or update index with new documents
                if self.index is None:
                    self.index = VectorStoreIndex.from_documents(
                        new_docs,
                        storage_context=self.storage_context,
                        embed_model=self.embed_model
                    )
                else:
                    for doc, doc_id in zip(new_docs, new_ids):
                        self.index.insert(doc, id=doc_id)
                
                print("Documents successfully indexed")
            else:
                print("No new or modified documents to index")

            return True

        except Exception as e:
            print(f"Error loading content source: {str(e)}")
            print(f"Error type: {type(e)}")
            return False

    def save_index(self):
        """ChromaDB automatically persists changes, this method is kept for compatibility."""
        if self.index:
            print(f"Index is automatically persisted in {self.persist_dir}")
        else:
            print("No index to save.")
            
    def generate_post(self, prompt: str, max_length: Optional[int] = None,
                 tone: Optional[str] = None, style: Optional[str] = None) -> Optional[str]:
        try:
            if not self.index:
                raise ValueError("No content source loaded. Call load_content_source first.")
            
            complete_prompt = self._build_generation_prompt(prompt, max_length, tone, style)
            print(f"Complete prompt: {complete_prompt}")  # Debug logging
            
            # Debug index state
            print(f"Index stats: {self.index.summary}")
            
            try:
                query_engine = self.index.as_query_engine()
                print(f"Query engine created successfully")  # Debug logging
                print(f"Query engine type: {type(query_engine)}")
            except Exception as qe:
                print(f"Failed to create query engine: {str(qe)}")
                print(f"Query engine error type: {type(qe)}")
                raise
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Attempting query, try {attempt + 1}")  # Debug logging
                    print(f"LLM being used: {self.llm.__class__.__name__}")
                    
                    # Debug the query parameters
                    print(f"Query parameters: prompt_len={len(complete_prompt)}")
                    
                    response = query_engine.query(complete_prompt)
                    print(f"Query successful, response type: {type(response)}")
                    return str(response)
                except Exception as e:
                    print(f"Error in query attempt {attempt + 1}:")
                    print(f"Error type: {type(e)}")
                    print(f"Error message: {str(e)}")
                    print(f"Error details: {e.__dict__}")  # Print all error attributes
                    
                    if attempt == max_retries - 1:
                        print(f"Final attempt failed")
                        raise  # Re-raise to be caught by outer try-except
                    print(f"Attempt {attempt + 1} failed, retrying...")
                    time.sleep(1)
                                    
        except Exception as e:
            print(f"Error in generate_post:")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            print(f"Error details: {e.__dict__}")  # Print all error attributes
            return None
            
    def direct_prompt(self, prompt: str) -> Optional[str]:
        """Send a prompt directly to the LLM without using RAG or vector database"""
        try:
            # Using the OpenAI completion API directly through our LLM instance
            response = self.llm.complete(prompt)
            return response.text
        except Exception as e:
            print(f"Error in direct prompt: {str(e)}")
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
