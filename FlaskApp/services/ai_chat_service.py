"""
AI Chat service using RAG with Groq and ChromaDB
Similar to the Jupyter notebook implementation
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from groq import Groq

class AIChatService:
    """Handles AI-powered Q&A about blog posts using RAG"""
    
    def __init__(self, posts_dir: str, groq_api_key: Optional[str] = None):
        self.posts_dir = Path(posts_dir)
        self.groq_api_key = groq_api_key or os.getenv('GROQ_API_KEY')
        
        # Initialize embedding model
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.Client()
        self.collection_name = "blog_posts_rag"
        
        # Initialize Groq client
        if self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key)
            self.has_groq = True
        else:
            self.groq_client = None
            self.has_groq = False
            print("⚠ Groq API key not configured. Only vector search available.")
    
    def clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^a-zA-Z0-9\s.,!?;:\'-]', ' ', text)
        return text.strip()
    
    def extract_title(self, content: str) -> str:
        """Extract title from blog post content"""
        title_match = re.search(r'title:\s*"([^"]+)"', content)
        if title_match:
            return title_match.group(1)
        
        title_match = re.search(r'title:\s*(.+?)\n', content)
        if title_match:
            return title_match.group(1).strip()
        
        return "Unknown Title"
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def index_posts(self) -> Dict[str, any]:
        """Index all blog posts into ChromaDB"""
        try:
            # Delete existing collection if it exists
            try:
                self.chroma_client.delete_collection(name=self.collection_name)
            except:
                pass
            
            # Create new collection
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Blog posts for RAG"}
            )
            
            # Find all post files
            post_files = list(self.posts_dir.glob("*.html")) + list(self.posts_dir.glob("*.md"))
            
            documents = []
            metadatas = []
            embeddings = []
            ids = []
            
            print(f"Processing {len(post_files)} blog posts...")
            
            for i, post_file in enumerate(post_files):
                try:
                    raw_content = post_file.read_text(encoding='utf-8')
                    title = self.extract_title(raw_content)
                    clean_content = self.clean_html(raw_content)
                    chunks = self.chunk_text(clean_content)
                    
                    # Create embeddings
                    chunk_embeddings = self.embedding_model.encode(chunks, show_progress_bar=False)
                    
                    for j, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                        documents.append(chunk)
                        embeddings.append(embedding.tolist())
                        metadatas.append({
                            "filename": post_file.name,
                            "title": title,
                            "chunk_id": j,
                            "source": "blog_post"
                        })
                        ids.append(f"{post_file.stem}_chunk_{j}")
                    
                    print(f"✓ Processed: {post_file.name} ({len(chunks)} chunks)")
                    
                except Exception as e:
                    print(f"✗ Error processing {post_file.name}: {e}")
            
            # Add to collection
            if documents:
                self.collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
                
                return {
                    'status': 'success',
                    'total_posts': len(post_files),
                    'total_chunks': len(documents),
                    'avg_chunks': len(documents) / len(post_files) if post_files else 0
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No documents to index'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def load_collection(self):
        """Load existing collection"""
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            return True
        except:
            return False
    
    def search_posts(self, query: str, n_results: int = 3) -> Dict[str, any]:
        """Search for relevant blog post chunks"""
        if not hasattr(self, 'collection'):
            if not self.load_collection():
                return {
                    'status': 'error',
                    'message': 'Collection not initialized. Please index posts first.'
                }
        
        try:
            query_embedding = self.embedding_model.encode(query).tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            search_results = []
            for i in range(len(results['documents'][0])):
                search_results.append({
                    'title': results['metadatas'][0][i]['title'],
                    'filename': results['metadatas'][0][i]['filename'],
                    'text': results['documents'][0][i][:300] + "...",
                    'distance': results['distances'][0][i]
                })
            
            return {
                'status': 'success',
                'results': search_results
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def ask_question(self, query: str, n_context: int = 3, model: str = "llama-3.3-70b-versatile") -> Dict[str, any]:
        """Ask a question and get AI-powered answer"""
        if not self.has_groq:
            return {
                'status': 'error',
                'message': 'Groq API not configured. Only vector search available.',
                'search_results': self.search_posts(query, n_context)
            }
        
        if not hasattr(self, 'collection'):
            if not self.load_collection():
                return {
                    'status': 'error',
                    'message': 'Collection not initialized. Please index posts first.'
                }
        
        try:
            # Get relevant context
            query_embedding = self.embedding_model.encode(query).tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_context
            )
            
            # Build context
            context_parts = []
            sources = []
            
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                context_parts.append(f"From '{metadata['title']}':\n{doc}")
                
                if metadata['title'] not in sources:
                    sources.append(metadata['title'])
            
            context = "\n\n".join(context_parts)
            
            # Build prompt
            prompt = f"""You are a helpful assistant answering questions about blog posts.

Context from relevant blog posts:
{context}

Question: {query}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information, say so."""

            # Call Groq
            completion = self.groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = completion.choices[0].message.content
            
            return {
                'status': 'success',
                'answer': answer,
                'sources': sources,
                'context_chunks': len(results['documents'][0])
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
