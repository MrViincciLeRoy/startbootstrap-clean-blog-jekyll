import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from typing import List, Dict, Optional

class RAGSystem:
    def __init__(self, embedding_model: str = 'all-MiniLM-L6-v2',
                 llm_model: str = 'openai-community/gpt2',
                 confidence_threshold: float = 0.6,
                 strict_mode: bool = True):
        """
        Initialize RAG system with improved accuracy controls

        Args:
            embedding_model: Name of the sentence transformer model
            llm_model: Name of the Hugging Face LLM model
            confidence_threshold: Minimum similarity score to use retrieved docs
            strict_mode: If True, decline to answer when confidence is low
        """
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer(embedding_model)

        print(f"Loading LLM: {llm_model}...")
        self.llm_model_name = llm_model
        self.tokenizer = None
        self.generator = None

        # FAISS index components
        self.index = None
        self.texts = []
        self.metadata = []
        self.d = None
        
        # Accuracy controls
        self.confidence_threshold = confidence_threshold
        self.strict_mode = strict_mode
        self.max_context_length = 2000
        self.min_retrieved_docs = 2  # Minimum docs needed for confident answer

    def load_llm(self, device: str = 'auto', load_in_8bit: bool = True):
        """Load the LLM model with optimizations"""
        print(f"Loading LLM on device: {device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.llm_model_name)
        
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
        """Build FAISS index from texts and metadata"""
        print("Generating embeddings...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)

        self.texts = texts
        self.metadata = metadata
        self.d = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(self.d)
        self.index.add(np.array(embeddings).astype('float32'))

        print(f"Index built with {self.index.ntotal} vectors")

    def retrieve(self, query: str, k: int = 3) -> List[Dict]:
        """
        Retrieve top-k documents with confidence scoring

        Returns documents with similarity and confidence metrics
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        query_embedding = self.embedding_model.encode([query]).astype('float32')
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for i, idx in enumerate(indices[0]):
            similarity = float(1 / (1 + distances[0][i]))
            results.append({
                'text': self.texts[idx],
                'metadata': self.metadata[idx],
                'distance': float(distances[0][i]),
                'similarity': similarity,
                'is_confident': similarity >= self.confidence_threshold
            })

        return results

    def _validate_retrieval(self, retrieved_docs: List[Dict]) -> tuple[bool, str]:
        """
        Validate if retrieved documents are sufficient for answering

        Returns: (is_valid, reason)
        """
        if not retrieved_docs:
            return False, "No relevant documents found"
        
        # Check minimum number of confident documents
        confident_docs = [d for d in retrieved_docs if d['is_confident']]
        if len(confident_docs) < self.min_retrieved_docs:
            return False, f"Insufficient confident sources (found {len(confident_docs)}, need {self.min_retrieved_docs})"
        
        # Check average similarity
        avg_similarity = np.mean([d['similarity'] for d in retrieved_docs])
        if avg_similarity < self.confidence_threshold:
            return False, f"Low average relevance score ({avg_similarity:.2f})"
        
        return True, "Valid"

    def generate_context(self, retrieved_docs: List[Dict], 
                        max_length: Optional[int] = None) -> str:
        """Generate context string, prioritizing high-confidence documents"""
        if max_length is None:
            max_length = self.max_context_length
        
        # Sort by similarity (highest first)
        sorted_docs = sorted(retrieved_docs, key=lambda x: x['similarity'], reverse=True)
        
        context_parts = []
        current_length = 0

        for i, doc in enumerate(sorted_docs, 1):
            source = doc['metadata'].get('source', 'Unknown')
            text = doc['text']
            similarity = doc['similarity']

            # Include confidence indicator
            chunk = f"[Source {i}: {source} (Relevance: {similarity:.2f})]\n{text}\n\n"

            if current_length + len(chunk) > max_length:
                break

            context_parts.append(chunk)
            current_length += len(chunk)

        return "".join(context_parts)

    def _create_strict_prompt(self, question: str, context: str) -> str:
        """Create a more restrictive prompt that discourages hallucinations"""
        prompt = f"""[INST] You are a factual assistant answering questions about native South African plants.

CRITICAL RULES:
- ONLY use information explicitly stated in the context below
- If information is not in the context, say "I don't have information about this"
- Do not infer, extrapolate, or use general knowledge
- Do not make up statistics or specific details
- If the context is unclear or contradictory, acknowledge this

Context:
{context}

Question: {question}

Provide a clear, concise answer based ONLY on the context provided. If the context doesn't contain the answer, state that explicitly. [/INST]

Answer:"""
        return prompt

    def _create_standard_prompt(self, question: str, context: str) -> str:
        """Create standard prompt for RAG"""
        prompt = f"""[INST] You are a helpful assistant answering questions about plants.

Context:
{context}

Question: {question}

Answer based on the provided context. [/INST]

Answer:"""
        return prompt

    def _generate_answer(self, prompt: str, max_new_tokens: int,
                        temperature: float) -> str:
        """Generate answer with error handling"""
        try:
            outputs = self.generator(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=max(0.1, temperature),  # Avoid temperature=0 which can cause issues
                do_sample=temperature > 0.1,
                top_p=0.9,
                top_k=30,
                return_full_text=False
            )

            answer = outputs[0]['generated_text'].strip()
            return answer

        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def query(self, question: str, k: int = 5, max_new_tokens: int = 500,
              temperature: float = 0.3) -> Dict:
        """
        Complete RAG pipeline with accuracy validation

        Args:
            question: User's question
            k: Number of documents to retrieve
            max_new_tokens: Maximum tokens to generate (reduced by default)
            temperature: Lower temperature = more deterministic (default 0.3)
        """
        if self.generator is None:
            raise ValueError("LLM not loaded. Call load_llm() first.")

        # Step 1: Retrieve relevant documents
        print(f"Retrieving top {k} documents...")
        retrieved_docs = self.retrieve(question, k=k)

        # Step 2: Validate retrieval
        is_valid, validation_reason = self._validate_retrieval(retrieved_docs)
        
        if not is_valid and self.strict_mode:
            return {
                'question': question,
                'answer': f"I cannot answer this question reliably. {validation_reason}. Please provide more specific context or documentation.",
                'sources': [],
                'retrieved_docs': retrieved_docs,
                'context': "",
                'confidence': 'low',
                'validation_failed': True
            }

        # Step 3: Generate context
        context = self.generate_context(retrieved_docs)

        # Step 4: Create prompt (use strict mode by default)
        prompt = self._create_strict_prompt(question, context)

        # Step 5: Generate answer
        print("Generating answer...")
        answer = self._generate_answer(prompt, max_new_tokens, temperature)

        # Calculate average confidence
        avg_confidence = np.mean([d['similarity'] for d in retrieved_docs])

        return {
            'question': question,
            'answer': answer,
            'sources': [doc['metadata'] for doc in retrieved_docs],
            'retrieved_docs': retrieved_docs,
            'context': context,
            'confidence': 'high' if avg_confidence >= self.confidence_threshold else 'low',
            'avg_similarity': float(avg_confidence),
            'validation_passed': is_valid
        }

    def batch_query(self, questions: List[str], k: int = 5) -> List[Dict]:
        """Process multiple questions with accuracy tracking"""
        results = []
        for question in questions:
            result = self.query(question, k=k)
            results.append(result)
        return results

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
