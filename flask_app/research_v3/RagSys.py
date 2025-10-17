import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from typing import List, Dict, Optional

class RAGSystem:
    def __init__(self, embedding_model: str = 'all-MiniLM-L6-v2',
                 llm_model: str = 'openai-community/gpt2'):
        """
        Initialize RAG system with embedding model and LLM from Hugging Face

        Args:
            embedding_model: Name of the sentence transformer model
            llm_model: Name of the Hugging Face LLM model
        """
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer(embedding_model)

        print(f"Loading LLM: {llm_model}...")
        self.llm_model_name = llm_model
        self.tokenizer = None
        self.llm = None
        self.generator = None

        # FAISS index components
        self.index = None
        self.texts = []
        self.metadata = []
        self.d = None

    def load_llm(self, device: str = 'auto', load_in_8bit: bool = True):
        """
        Load the LLM model (can be done separately to save memory)

        Args:
            device: Device to load model on ('cuda', 'cpu', or 'auto')
            load_in_8bit: Whether to load model in 8-bit precision (saves memory)
        """
        print(f"Loading LLM on device: {device}")

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.llm_model_name)

        # Create text generation pipeline
        self.generator = pipeline(
            "text-generation",
            model=self.llm_model_name,
            tokenizer=self.tokenizer,
            device_map=device,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            model_kwargs={"load_in_8bit": load_in_8bit} if load_in_8bit else {}
        )

        print("LLM loaded successfully!")

    def build_index(self, texts: List[str], metadata: List[Dict]):
        """
        Build FAISS index from texts and metadata

        Args:
            texts: List of text chunks to index
            metadata: List of metadata dictionaries for each text
        """
        print("Generating embeddings...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)

        # Store for later retrieval
        self.texts = texts
        self.metadata = metadata
        self.d = embeddings.shape[1]

        # Create FAISS index
        self.index = faiss.IndexFlatL2(self.d)
        self.index.add(np.array(embeddings).astype('float32'))

        print(f"Index built with {self.index.ntotal} vectors")

    def retrieve(self, query: str, k: int = 3) -> List[Dict]:
        """
        Retrieve top-k most relevant documents for a query

        Args:
            query: Search query
            k: Number of documents to retrieve

        Returns:
            List of dictionaries containing text, metadata, and distance
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        # Encode query
        query_embedding = self.embedding_model.encode([query]).astype('float32')

        # Search
        distances, indices = self.index.search(query_embedding, k)

        # Format results
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
        Generate context string from retrieved documents

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
        Complete RAG pipeline: retrieve + generate

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
        """Create prompt for LLM (formatted for instruction-tuned models)"""

        # Format depends on the model - using Mistral/Llama instruction format
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
        """Generate answer using Hugging Face LLM"""
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
            return f"Error generating answer: {str(e)}"

    def save_index(self, filepath: str):
        """Save FAISS index to disk"""
        if self.index is None:
            raise ValueError("No index to save")
        faiss.write_index(self.index, filepath)
        print(f"Index saved to {filepath}")

    def load_index(self, filepath: str, texts: List[str], metadata: List[Dict]):
        """Load FAISS index from disk"""
        self.index = faiss.read_index(filepath)
        self.texts = texts
        self.metadata = metadata
        self.d = self.index.d
        print(f"Index loaded from {filepath}")

"""
# Example usage with Hugging Face models
if __name__ == "__main__":
    # Initialize RAG system with Hugging Face models
    # Popular options:
    # - 'mistralai/Mistral-7B-Instruct-v0.2' (recommended, good balance)
    # - 'meta-llama/Llama-2-7b-chat-hf' (requires access approval)
    # - 'google/flan-t5-large' (smaller, faster)
    # - 'tiiuae/falcon-7b-instruct'

    rag = RAGSystem(
        embedding_model='all-MiniLM-L6-v2',
        llm_model = 'LiquidAI/LFM2-1.2B-RAG'  # or any HF model
    )
    sources = data
    # Your existing data
    texts = [
        #"America is a climbing rose that was introduced in 1976 and was bred by William A. Warriner. This is a vigorous climber that produces coral-pink blossoms throughout the growing season. It is hardy in zones 5-9 and prefers full sun. The flowers are fragrant and can reach 4-5 inches in diameter.",
       #X['text'] for X in Source
    ]

    metadata = [

        #x['metadata'] for x in Source
        # Add more metadata here
    ]
    for x in sources:
         #print(x)
         texts.append(x['text'])
         metadata.append(x['metadata'])
    # Build index (this doesn't require GPU)
    rag.build_index(texts, metadata)

    # Load LLM (this step loads the model into memory)
    # Use load_in_8bit=True if you have limited GPU memory
    rag.load_llm(device='auto', load_in_8bit=False)

    # Query the system
    question = "How to care for roses?"
    result = rag.query(question, k=5, max_new_tokens=900, temperature=0.7)

    # Display results
    print("\n" + "="*70)
    print("QUESTION:", result['question'])
    print("\n" + "-"*70)
    print("ANSWER:", result['answer'])
    print("\n" + "-"*70)
    print("SOURCES:")
    for i, source in enumerate(result['sources'], 1):
        print(f"{i}. {source.get('title', 'Unknown')} ({source.get('source', 'Unknown')})")
        print(f"   URL: {source.get('url', 'N/A')}")

    # Show retrieved documents with similarity scores
    print("\n" + "-"*70)
    print("RETRIEVED DOCUMENTS:")
    for i, doc in enumerate(result['retrieved_docs'], 1):
        print(f"\n{i}. Similarity: {doc['similarity']:.3f} | Distance: {doc['distance']:.3f}")
        print(f"   Source: {doc['metadata'].get('title', 'Unknown')}")
        print(f"   Text: {doc['text'][:150]}...")
    print("="*70)"""
