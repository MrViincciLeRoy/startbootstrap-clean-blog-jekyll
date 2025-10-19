"""
RagSys.py - Research V4
RAG System with JSON configuration management
All settings loaded from ConfigManager
"""

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from typing import List, Dict, Optional
import logging

#from ConfigManager import ConfigManager

logger = logging.getLogger(__name__)


class RAGSystem:
    """RAG System with configuration-driven setup"""

    def __init__(self, config: ConfigManager = None):
        """
        Initialize RAG system with configuration.

        Args:
            config: ConfigManager instance. If None, creates new instance.
        """
        if config is None:
            config = ConfigManager()
        
        self.config = config
        self.embedding_model_name = config.get_embedding_model()
        self.llm_model_name = config.get_llm_model()
        self.device = config.get_device()
        self.load_in_8bit = config.get_load_in_8bit()
        
        print(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        # FAISS index components
        self.index = None
        self.texts = []
        self.metadata = []
        self.d = None
        
        logger.info(f"RAG System initialized with config")
        logger.info(f"  Embedding: {self.embedding_model_name}")
        logger.info(f"  LLM: {self.llm_model_name}")
        logger.info(f"  Device: {self.device}")

    def load_llm(self, device: str = None, load_in_8bit: bool = None):
        """
        Load the LLM model.

        Args:
            device: Device to load model on. If None, uses config value.
            load_in_8bit: Whether to load in 8-bit. If None, uses config value.
        """
        device = device or self.device
        load_in_8bit = load_in_8bit if load_in_8bit is not None else self.load_in_8bit

        print(f"Loading LLM on device: {device}")
        logger.info(f"Loading LLM: {self.llm_model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.llm_model_name)

        self.generator = pipeline(
            "text-generation",
            model=self.llm_model_name,
            tokenizer=self.tokenizer,
            device_map=device,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            model_kwargs={"load_in_8bit": load_in_8bit} if load_in_8bit else {}
        )

        logger.info("LLM loaded successfully!")

    def build_index(self, texts: List[str], metadata: List[Dict]):
        """
        Build FAISS index from texts and metadata.

        Args:
            texts: List of text chunks to index
            metadata: List of metadata dictionaries for each text
        """
        print("Generating embeddings...")
        logger.info(f"Building index from {len(texts)} texts")
        
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)

        self.texts = texts
        self.metadata = metadata
        self.d = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(self.d)
        self.index.add(np.array(embeddings).astype('float32'))

        logger.info(f"Index built with {self.index.ntotal} vectors")
        print(f"✓ Index built with {self.index.ntotal} vectors")

    def retrieve(self, query: str, k: int = 3) -> List[Dict]:
        """
        Retrieve top-k most relevant documents for a query.

        Args:
            query: Search query
            k: Number of documents to retrieve

        Returns:
            List of dictionaries containing text, metadata, and distance
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        query_embedding = self.embedding_model.encode([query]).astype('float32')
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for i, idx in enumerate(indices[0]):
            results.append({
                'text': self.texts[idx],
                'metadata': self.metadata[idx],
                'distance': float(distances[0][i]),
                'similarity': float(1 / (1 + distances[0][i]))
            })

        return results

    def generate_context(self, retrieved_docs: List[Dict], max_length: int = 2000) -> str:
        """
        Generate context string from retrieved documents.

        Args:
            retrieved_docs: List of retrieved document dictionaries
            max_length: Maximum character length for context

        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0

        for i, doc in enumerate(retrieved_docs, 1):
            source = doc['metadata'].get('source', 'Unknown')
            text = doc['text']

            chunk = f"[Source {i}: {source}]\n{text}\n\n"

            if current_length + len(chunk) > max_length:
                break

            context_parts.append(chunk)
            current_length += len(chunk)

        return "".join(context_parts)

    def query(self, question: str, k: int = 5, max_new_tokens: int = 2000,
              temperature: float = 0.7) -> Dict:
        """
        Complete RAG pipeline: retrieve + generate.

        Args:
            question: User's question
            k: Number of documents to retrieve
            max_new_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature for generation

        Returns:
            Dictionary with answer, sources, and retrieved documents
        """
        if self.generator is None:
            raise ValueError("LLM not loaded. Call load_llm() first.")

        logger.info(f"Processing query: {question[:100]}...")
        
        # Step 1: Retrieve relevant documents
        print(f"Retrieving top {k} documents...")
        retrieved_docs = self.retrieve(question, k=k)

        # Step 2: Generate context
        context = self.generate_context(retrieved_docs)

        # Step 3: Create prompt
        prompt = self._create_prompt(question, context)

        # Step 4: Generate answer using LLM
        print("Generating answer...")
        answer = self._generate_answer(prompt, max_new_tokens, temperature)

        return {
            'question': question,
            'answer': answer,
            'sources': [doc['metadata'] for doc in retrieved_docs],
            'retrieved_docs': retrieved_docs,
            'context': context
        }

    def _create_prompt(self, question: str, context: str) -> str:
        """Create prompt for LLM."""
        prompt = f"""<s>[INST] You are a helpful assistant that answers questions based on the provided context.

Context:
{context}

Question: {question}

Instructions:
- You are writing about native South African plants based on context
- Answer the question based ONLY on the information provided in the context above
- If the context doesn't contain enough information to answer the question, say so
- Cite which source(s) you used in your answer
- Be concise but thorough [/INST]
- Do not include these instructions
- Answer in a Wikipedia blog type

Answer:"""
        return prompt

    def _generate_answer(self, prompt: str, max_new_tokens: int,
                        temperature: float) -> str:
        """Generate answer using Hugging Face LLM."""
        try:
            outputs = self.generator(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                top_p=0.95,
                top_k=50,
                return_full_text=False
            )

            answer = outputs[0]['generated_text'].strip()
            return answer

        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return f"Error generating answer: {str(e)}"

    def save_index(self, filepath: str):
        """Save FAISS index to disk."""
        if self.index is None:
            raise ValueError("No index to save")
        faiss.write_index(self.index, filepath)
        logger.info(f"Index saved to {filepath}")

    def load_index(self, filepath: str, texts: List[str], metadata: List[Dict]):
        """Load FAISS index from disk."""
        self.index = faiss.read_index(filepath)
        self.texts = texts
        self.metadata = metadata
        self.d = self.index.d
        logger.info(f"Index loaded from {filepath}")

    def get_statistics(self) -> Dict:
        """Get RAG system statistics."""
        stats = {
            "embedding_model": self.embedding_model_name,
            "llm_model": self.llm_model_name,
            "device": self.device,
            "index_size": self.index.ntotal if self.index else 0,
            "embedding_dimension": self.d,
            "total_texts": len(self.texts)
        }
        return stats

    def print_statistics(self):
        """Print RAG system statistics."""
        stats = self.get_statistics()
        print("\n" + "="*60)
        print("RAG System Statistics")
        print("="*60)
        print(f"Embedding Model: {stats['embedding_model']}")
        print(f"LLM Model: {stats['llm_model']}")
        print(f"Device: {stats['device']}")
        print(f"Index Size: {stats['index_size']} vectors")
        print(f"Embedding Dimension: {stats['embedding_dimension']}")
        print(f"Total Texts: {stats['total_texts']}")
        print("="*60 + "\n")


# Example usage
if __name__ == "__main__":
    # Initialize with config
    config = ConfigManager(verbose=True)
    config.print_summary()
    
    # Initialize RAG system
    rag = RAGSystem(config)
    
    # Print statistics
    rag.print_statistics()
