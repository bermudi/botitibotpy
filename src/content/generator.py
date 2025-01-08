import time
import logging
import os
import hashlib
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, Document
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.gemini import GeminiEmbedding
import chromadb
from ..config import Config

logger = logging.getLogger("botitibot.content")

class ContentGenerator:
    def __init__(self, log_level: int = logging.INFO):
        """Initialize the content generator with LlamaIndex and ChromaDB components
        
        Args:
            log_level: The logging level to use (default: logging.INFO)
        """
        self.log_level = log_level
        logger.setLevel(log_level)
        
        logger.info("Initializing ContentGenerator", extra={
            'context': {
                'log_level': log_level,
                'component': 'content_generator'
            }
        })
        
        # Initialize Gemini embedding model
        logger.debug("Setting up Gemini embedding model", extra={
            'context': {
                'model': "models/embedding-001",
                'component': 'content_generator.embedding'
            }
        })
        self.embed_model = GeminiEmbedding(
            model_name="models/embedding-001",
            api_key=Config.GOOGLE_API_KEY
        )
        Settings.embed_model = self.embed_model
        
        # Configure LlamaIndex LLM settings
        logger.debug("Configuring LlamaIndex LLM settings", extra={
            'context': {
                'model': Config.OPENAI_API_MODEL,
                'temperature': 0.7,
                'component': 'content_generator.llm'
            }
        })
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
        logger.debug(f"Initializing ChromaDB client with persist_dir: {self.persist_dir}", extra={
            'context': {
                'persist_dir': self.persist_dir,
                'component': 'content_generator.chromadb'
            }
        })
        self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection_name = "content_collection"
        self.chroma_collection = self.chroma_client.get_or_create_collection(self.collection_name)
        
        # Initialize vector store
        logger.debug("Setting up vector store and storage context", extra={
            'context': {
                'component': 'content_generator.vector_store'
            }
        })
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # Track document hashes
        self.document_hashes = {}
        logger.info("ContentGenerator initialized successfully", extra={
            'context': {
                'component': 'content_generator'
            }
        })

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
                logger.info("Loading existing index from ChromaDB", extra={
                    'context': {
                        'component': 'content_generator.index'
                    }
                })
                self.index = VectorStoreIndex.from_vector_store(
                    self.vector_store,
                    embed_model=self.embed_model
                )
                logger.info(f"Index successfully loaded from {self.persist_dir}", extra={
                    'context': {
                        'component': 'content_generator.index'
                    }
                })
                return True
            logger.info("No existing index found in ChromaDB", extra={
                'context': {
                    'component': 'content_generator.index'
                }
            })
            return False
        except Exception as e:
            logger.error(f"Failed to load index: {str(e)}", exc_info=True, extra={
                'context': {
                    'component': 'content_generator.index'
                }
            })
            return False

    def load_content_source(self, directory_path: str) -> bool:
        """Load content from a directory, updating only if documents have changed."""
        try:
            logger.info(f"Loading content from directory: {os.path.abspath(directory_path)}", extra={
                'context': {
                    'directory_path': directory_path,
                    'component': 'content_generator.content_source'
                }
            })
            if not os.path.exists(directory_path):
                logger.error(f"Directory does not exist: {directory_path}", extra={
                    'context': {
                        'directory_path': directory_path,
                        'component': 'content_generator.content_source'
                    }
                })
                return False

            # Load documents
            documents = SimpleDirectoryReader(directory_path).load_data()
            logger.info(f"Found {len(documents)} documents in directory", extra={
                'context': {
                    'directory_path': directory_path,
                    'component': 'content_generator.content_source'
                }
            })

            # Track new or modified documents
            new_docs = []
            new_ids = []
            new_metadata = []

            for doc in documents:
                doc_hash = self._calculate_document_hash(doc.text)
                doc_id = self._get_document_id(doc.metadata.get('file_path', 'unknown'), doc.text)
                
                # Check if document is new or modified
                if doc_id not in self.document_hashes or self.document_hashes[doc_id] != doc_hash:
                    logger.debug(f"New or modified document found: {doc.metadata.get('file_path', 'unknown')}", extra={
                        'context': {
                            'file_path': doc.metadata.get('file_path', 'unknown'),
                            'component': 'content_generator.content_source'
                        }
                    })
                    new_docs.append(doc)
                    new_ids.append(doc_id)
                    new_metadata.append({
                        "file_path": doc.metadata.get('file_path', 'unknown'),
                        "hash": doc_hash
                    })
                    self.document_hashes[doc_id] = doc_hash

            if new_docs:
                logger.info(f"Adding/updating {len(new_docs)} documents to index", extra={
                    'context': {
                        'component': 'content_generator.index'
                    }
                })
                # Create or update index with new documents
                if self.index is None:
                    logger.debug("Creating new index", extra={
                        'context': {
                            'component': 'content_generator.index'
                        }
                    })
                    self.index = VectorStoreIndex.from_documents(
                        new_docs,
                        storage_context=self.storage_context,
                        embed_model=self.embed_model
                    )
                else:
                    logger.debug("Updating existing index", extra={
                        'context': {
                            'component': 'content_generator.index'
                        }
                    })
                    for doc, doc_id in zip(new_docs, new_ids):
                        self.index.insert(doc, id=doc_id)
                
                logger.info("Documents successfully indexed", extra={
                    'context': {
                        'component': 'content_generator.index'
                    }
                })
            else:
                logger.info("No new or modified documents to index", extra={
                    'context': {
                        'component': 'content_generator.index'
                    }
                })

            return True

        except Exception as e:
            logger.error(f"Error loading content source: {str(e)}", exc_info=True, extra={
                'context': {
                    'component': 'content_generator.content_source'
                }
            })
            return False

    def save_index(self):
        """ChromaDB automatically persists changes, this method is kept for compatibility."""
        if self.index:
            logger.info(f"Index is automatically persisted in {self.persist_dir}", extra={
                'context': {
                    'persist_dir': self.persist_dir,
                    'component': 'content_generator.index'
                }
            })
        else:
            logger.warning("No index to save", extra={
                'context': {
                    'component': 'content_generator.index'
                }
            })
            
    def generate_post_withRAG(self, prompt: str, max_length: Optional[int] = None,
                     tone: Optional[str] = None, style: Optional[str] = None) -> Optional[str]:
        try:
            if not self.index:
                logger.error("No content source loaded", extra={
                    'context': {
                        'component': 'content_generator.post'
                    }
                })
                raise ValueError("No content source loaded. Call load_content_source first.")
            
            complete_prompt = self._build_generation_prompt(prompt, max_length, tone, style)
            logger.debug(f"Generated complete prompt: {complete_prompt}", extra={
                'context': {
                    'prompt': prompt,
                    'component': 'content_generator.post'
                }
            })
            
            # Debug index state
            logger.debug(f"Index stats: {self.index.summary}", extra={
                'context': {
                    'component': 'content_generator.index'
                }
            })
            
            try:
                query_engine = self.index.as_query_engine()
                logger.debug("Query engine created successfully", extra={
                    'context': {
                        'component': 'content_generator.query_engine'
                    }
                })
            except Exception as qe:
                logger.error(f"Failed to create query engine: {str(qe)}", exc_info=True, extra={
                    'context': {
                        'component': 'content_generator.query_engine'
                    }
                })
                raise
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.debug(f"Attempting query (attempt {attempt + 1}/{max_retries})", extra={
                        'context': {
                            'attempt': attempt + 1,
                            'component': 'content_generator.query'
                        }
                    })
                    logger.debug(f"Using LLM: {self.llm.__class__.__name__}", extra={
                        'context': {
                            'llm': self.llm.__class__.__name__,
                            'component': 'content_generator.llm'
                        }
                    })
                    
                    response = query_engine.query(complete_prompt)
                    logger.info("Query completed successfully", extra={
                        'context': {
                            'component': 'content_generator.query'
                        }
                    })
                    logger.debug(f"Response type: {type(response)}", extra={
                        'context': {
                            'response_type': type(response),
                            'component': 'content_generator.query'
                        }
                    })
                    return str(response)
                except Exception as e:
                    logger.warning(f"Query attempt {attempt + 1} failed: {str(e)}", extra={
                        'context': {
                            'attempt': attempt + 1,
                            'component': 'content_generator.query'
                        }
                    })
                    
                    if attempt == max_retries - 1:
                        logger.error("All query attempts failed", exc_info=True, extra={
                            'context': {
                                'component': 'content_generator.query'
                            }
                        })
                        raise
                    logger.info(f"Retrying query after attempt {attempt + 1}", extra={
                        'context': {
                            'attempt': attempt + 1,
                            'component': 'content_generator.query'
                        }
                    })
                    time.sleep(1)
                                    
        except Exception as e:
            logger.error(f"Error in generate_post_withRAG: {str(e)}", exc_info=True, extra={
                'context': {
                    'component': 'content_generator.post'
                }
            })
            return None

    def generate_post(self, prompt: str, max_length: Optional[int] = None,
                     tone: Optional[str] = None, style: Optional[str] = None) -> Optional[str]:
        """Generate content using direct LLM without RAG"""
        try:
            complete_prompt = self._build_generation_prompt(prompt, max_length, tone, style)
            logger.debug("Sending direct prompt to LLM", extra={
                'context': {
                    'prompt': complete_prompt,
                    'component': 'content_generator.direct_prompt'
                }
            })
            response = self.llm.complete(complete_prompt)
            logger.info("Direct prompt completed successfully", extra={
                'context': {
                    'component': 'content_generator.direct_prompt'
                }
            })
            return response.text
        except Exception as e:
            logger.error(f"Error in generate_post: {str(e)}", exc_info=True, extra={
                'context': {
                    'component': 'content_generator.direct_prompt'
                }
            })
            return None

    def direct_prompt(self, prompt: str) -> Optional[str]:
        """Send a prompt directly to the LLM without using RAG or vector database"""
        try:
            logger.debug("Sending direct prompt to LLM", extra={
                'context': {
                    'prompt': prompt,
                    'component': 'content_generator.direct_prompt'
                }
            })
            response = self.llm.complete(prompt)
            logger.info("Direct prompt completed successfully", extra={
                'context': {
                    'component': 'content_generator.direct_prompt'
                }
            })
            return response.text
        except Exception as e:
            logger.error(f"Error in direct prompt: {str(e)}", exc_info=True, extra={
                'context': {
                    'component': 'content_generator.direct_prompt'
                }
            })
            return None

    def _build_generation_prompt(self,
                               base_prompt: str,
                               max_length: Optional[int] = None,
                               tone: Optional[str] = None,
                               style: Optional[str] = None) -> str:
        """Build a complete prompt incorporating all parameters"""
        logger.debug("Building generation prompt", extra={
            'context': {
                'base_prompt': base_prompt,
                'component': 'content_generator.prompt'
            }
        })
        prompt_parts = [base_prompt]
        
        if max_length:
            prompt_parts.append(f"Keep the response under {max_length} characters.")
            
        if tone:
            prompt_parts.append(f"Use a {tone} tone.")
            
        if style:
            prompt_parts.append(f"Write in a {style} style.")
            
        final_prompt = " ".join(prompt_parts)
        logger.debug(f"Generated prompt: {final_prompt}", extra={
            'context': {
                'prompt': final_prompt,
                'component': 'content_generator.prompt'
            }
        })
        return final_prompt

    def load_webpage(self, url: str) -> Optional[Document]:
        """Load and parse content from a web page.
        
        Args:
            url: The URL of the web page to parse
            
        Returns:
            Optional[Document]: A Document object containing the parsed content and metadata,
                              or None if parsing fails
        """
        try:
            logger.info(f"Fetching content from URL: {url}", extra={
                'context': {
                    'url': url,
                    'component': 'content_generator.webpage'
                }
            })
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract main content (prioritize article or main content areas)
            content_areas = soup.find_all(['article', 'main']) or [soup.find('body')]
            content = ""
            
            for area in content_areas:
                if area:
                    # Remove script and style elements
                    for element in area(['script', 'style']):
                        element.decompose()
                    content += area.get_text(separator='\n', strip=True)
            
            # Extract metadata
            metadata = {
                'url': url,
                'title': soup.title.string if soup.title else '',
                'source_type': 'webpage',
                'timestamp': datetime.now().isoformat(),
            }
            
            # Create document
            doc = Document(
                text=content,
                metadata=metadata
            )
            
            logger.info(f"Successfully parsed webpage: {metadata['title']}", extra={
                'context': {
                    'title': metadata['title'],
                    'component': 'content_generator.webpage'
                }
            })
            return doc
            
        except Exception as e:
            logger.error(f"Error parsing webpage {url}: {str(e)}", exc_info=True, extra={
                'context': {
                    'url': url,
                    'component': 'content_generator.webpage'
                }
            })
            return None
            
    def load_webpage_batch(self, urls: List[str]) -> List[Document]:
        """Load and parse content from multiple web pages.
        
        Args:
            urls: List of URLs to parse
            
        Returns:
            List[Document]: List of successfully parsed Document objects
        """
        documents = []
        for url in urls:
            doc = self.load_webpage(url)
            if doc:
                documents.append(doc)
        return documents

    def add_webpage_to_index(self, url: str) -> bool:
        """Parse a webpage and add its content to the index."""
        try:
            doc = self.load_webpage(url)
            if not doc:
                return False
                
            doc_hash = self._calculate_document_hash(doc.text)
            doc_id = self._get_document_id(url, doc.text)
            
            # Check if document is new or modified
            if doc_id not in self.document_hashes or self.document_hashes[doc_id] != doc_hash:
                logger.info(f"Adding new webpage to index: {url}", extra={
                    'context': {
                        'url': url,
                        'component': 'content_generator.index'
                    }
                })
                
                if self.index is None:
                    self.index = VectorStoreIndex.from_documents(
                        [doc],
                        storage_context=self.storage_context,
                        embed_model=self.embed_model
                    )
                else:
                    self.index.insert(doc, id=doc_id)
                    
                self.document_hashes[doc_id] = doc_hash
                return True
            
            logger.info(f"Webpage already indexed and unchanged: {url}", extra={
                'context': {
                    'url': url,
                    'component': 'content_generator.index'
                }
            })
            return True
            
        except Exception as e:
            logger.error(f"Error adding webpage to index: {str(e)}", exc_info=True, extra={
                'context': {
                    'component': 'content_generator.index'
                }
            })
            return False

    def parse_rss_feed(self, feed_url: str) -> Optional[List[Document]]:
        """Parse an RSS feed and convert entries to documents.
        
        Args:
            feed_url: URL of the RSS feed
            
        Returns:
            Optional[List[Document]]: List of Document objects from feed entries,
                                    or None if parsing fails
        """
        try:
            logger.info(f"Fetching RSS feed: {feed_url}", extra={
                'context': {
                    'feed_url': feed_url,
                    'component': 'content_generator.rss'
                }
            })
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:  # feedparser sets this flag for malformed feeds
                logger.error(f"Malformed RSS feed at {feed_url}: {feed.bozo_exception}", extra={
                    'context': {
                        'feed_url': feed_url,
                        'component': 'content_generator.rss'
                    }
                })
                return None
                
            documents = []
            for entry in feed.entries:
                # Extract content (prefer full content over summary)
                content = ''
                if hasattr(entry, 'content'):
                    content = entry.content[0].value
                elif hasattr(entry, 'summary'):
                    content = entry.summary
                elif hasattr(entry, 'description'):
                    content = entry.description
                    
                # Clean content (remove HTML if present)
                if content:
                    soup = BeautifulSoup(content, 'html.parser')
                    content = soup.get_text(separator='\n', strip=True)
                
                # Extract publication date
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6]).isoformat()
                
                # Create metadata
                metadata = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'author': entry.get('author', ''),
                    'published_date': pub_date,
                    'feed_url': feed_url,
                    'source_type': 'rss',
                    'feed_title': feed.feed.get('title', ''),
                }
                
                # Create document
                doc = Document(
                    text=content,
                    metadata=metadata
                )
                documents.append(doc)
            
            logger.info(f"Successfully parsed {len(documents)} entries from RSS feed: {feed.feed.get('title', feed_url)}", extra={
                'context': {
                    'feed_url': feed_url,
                    'component': 'content_generator.rss'
                }
            })
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_url}: {str(e)}", exc_info=True, extra={
                'context': {
                    'feed_url': feed_url,
                    'component': 'content_generator.rss'
                }
            })
            return None
            
    def monitor_rss_feed(self, feed_url: str) -> Tuple[int, int]:
        """Monitor an RSS feed and add new entries to the index.
        
        Args:
            feed_url: URL of the RSS feed to monitor
            
        Returns:
            Tuple[int, int]: (number of new entries, number of failed entries)
        """
        try:
            documents = self.parse_rss_feed(feed_url)
            if not documents:
                return (0, 0)
                
            new_entries = 0
            failed_entries = 0
            
            for doc in documents:
                try:
                    doc_hash = self._calculate_document_hash(doc.text)
                    doc_id = self._get_document_id(doc.metadata['link'], doc.text)
                    
                    # Check if entry is new or modified
                    if doc_id not in self.document_hashes or self.document_hashes[doc_id] != doc_hash:
                        logger.info(f"Adding new RSS entry to index: {doc.metadata['title']}", extra={
                            'context': {
                                'title': doc.metadata['title'],
                                'component': 'content_generator.index'
                            }
                        })
                        
                        if self.index is None:
                            self.index = VectorStoreIndex.from_documents(
                                [doc],
                                storage_context=self.storage_context,
                                embed_model=self.embed_model
                            )
                        else:
                            self.index.insert(doc, id=doc_id)
                            
                        self.document_hashes[doc_id] = doc_hash
                        new_entries += 1
                        
                except Exception as e:
                    logger.error(f"Error processing RSS entry {doc.metadata.get('title', 'unknown')}: {str(e)}", exc_info=True, extra={
                        'context': {
                            'title': doc.metadata.get('title', 'unknown'),
                            'component': 'content_generator.index'
                        }
                    })
                    failed_entries += 1
                    
            return (new_entries, failed_entries)
            
        except Exception as e:
            logger.error(f"Error monitoring RSS feed {feed_url}: {str(e)}", exc_info=True, extra={
                'context': {
                    'feed_url': feed_url,
                    'component': 'content_generator.rss'
                }
            })
            return (0, 0)

    def list_sources(self) -> List[Dict[str, Any]]:
        """List all content sources and their status.
        
        Returns:
            List[Dict[str, Any]]: List of content sources with metadata
        """
        try:
            logger.debug("Listing content sources", extra={
                'context': {
                    'component': 'content_generator.sources'
                }
            })
            
            sources = []
            # Get all documents from ChromaDB
            docs = self.chroma_collection.get()
            
            # Group documents by source
            source_groups = {}
            for i, doc_id in enumerate(docs['ids']):
                metadata = docs['metadatas'][i]
                source_type = metadata.get('source_type', 'unknown')
                source_id = metadata.get('file_path', metadata.get('url', metadata.get('feed_url', 'unknown')))
                
                if source_id not in source_groups:
                    source_groups[source_id] = {
                        'id': source_id,
                        'type': source_type,
                        'document_count': 0,
                        'last_updated': None,
                        'metadata': metadata
                    }
                source_groups[source_id]['document_count'] += 1
                
                # Track most recent update
                timestamp = metadata.get('timestamp')
                if timestamp:
                    if not source_groups[source_id]['last_updated'] or timestamp > source_groups[source_id]['last_updated']:
                        source_groups[source_id]['last_updated'] = timestamp
            
            sources = list(source_groups.values())
            logger.info(f"Found {len(sources)} content sources", extra={
                'context': {
                    'source_count': len(sources),
                    'component': 'content_generator.sources'
                }
            })
            return sources
            
        except Exception as e:
            logger.error(f"Error listing content sources: {str(e)}", exc_info=True, extra={
                'context': {
                    'component': 'content_generator.sources'
                }
            })
            return []

    def update_index(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Update the content index by checking all sources for changes.
        
        Args:
            dry_run: If True, only report what would be updated without making changes
            
        Returns:
            List[Dict[str, Any]]: List of changes made or that would be made
        """
        try:
            logger.info("Starting index update", extra={
                'context': {
                    'dry_run': dry_run,
                    'component': 'content_generator.index'
                }
            })
            
            changes = []
            sources = self.list_sources()
            
            for source in sources:
                try:
                    source_id = source['id']
                    source_type = source['type']
                    
                    logger.debug(f"Checking source: {source_id}", extra={
                        'context': {
                            'source_id': source_id,
                            'source_type': source_type,
                            'component': 'content_generator.index'
                        }
                    })
                    
                    if source_type == 'webpage':
                        if not dry_run:
                            success = self.add_webpage_to_index(source_id)
                            if success:
                                changes.append({
                                    'type': 'update',
                                    'source_id': source_id,
                                    'source_type': source_type
                                })
                        else:
                            changes.append({
                                'type': 'would_update',
                                'source_id': source_id,
                                'source_type': source_type
                            })
                            
                    elif source_type == 'rss':
                        if not dry_run:
                            new_entries, failed = self.monitor_rss_feed(source_id)
                            if new_entries > 0:
                                changes.append({
                                    'type': 'update',
                                    'source_id': source_id,
                                    'source_type': source_type,
                                    'new_entries': new_entries,
                                    'failed_entries': failed
                                })
                        else:
                            changes.append({
                                'type': 'would_update',
                                'source_id': source_id,
                                'source_type': source_type
                            })
                            
                    elif source_type == 'file':
                        if not dry_run:
                            directory = os.path.dirname(source_id)
                            if self.load_content_source(directory):
                                changes.append({
                                    'type': 'update',
                                    'source_id': source_id,
                                    'source_type': source_type
                                })
                        else:
                            changes.append({
                                'type': 'would_update',
                                'source_id': source_id,
                                'source_type': source_type
                            })
                            
                except Exception as e:
                    logger.error(f"Error updating source {source_id}: {str(e)}", exc_info=True, extra={
                        'context': {
                            'source_id': source_id,
                            'error': str(e),
                            'component': 'content_generator.index'
                        }
                    })
                    changes.append({
                        'type': 'error',
                        'source_id': source_id,
                        'error': str(e)
                    })
            
            logger.info(f"Index update complete with {len(changes)} changes", extra={
                'context': {
                    'change_count': len(changes),
                    'dry_run': dry_run,
                    'component': 'content_generator.index'
                }
            })
            return changes
            
        except Exception as e:
            logger.error(f"Error updating index: {str(e)}", exc_info=True, extra={
                'context': {
                    'component': 'content_generator.index'
                }
            })
            return [{'type': 'error', 'error': str(e)}]

    def generate_reply(self, original_post: str, comment_text: str) -> Optional[str]:
        """Generate a reply to a comment using direct LLM"""
        try:
            # Build a prompt that includes both the original post and the comment
            prompt = f"""Given this original post:
"{original_post}"

And this comment:
"{comment_text}"

Generate a friendly and engaging reply that:
1. Acknowledges the comment
2. Maintains a conversational tone
3. Adds value to the discussion
4. Stays relevant to the original post's topic

Reply:"""
            
            logger.debug("Generating reply with prompt", extra={
                'context': {
                    'original_post': original_post,
                    'comment': comment_text,
                    'component': 'content_generator.reply'
                }
            })
            
            response = self.llm.complete(prompt)
            logger.info("Reply generated successfully", extra={
                'context': {
                    'component': 'content_generator.reply'
                }
            })
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating reply: {str(e)}", exc_info=True)
            return None
