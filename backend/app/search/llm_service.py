from typing import List, Dict
import numpy as np


class LLMService:
    """Service for RAG and Summarization"""

    def __init__(self, model):
        # use shared model
        self.model = model

    def _split_into_sentences(self, text: str) -> List[str]:
        """Simple rule-based sentence splitting"""
        # A more robust splitter (e.g. nltk/spacy) would be better but requires more dependencies
        # This is a basic approximation for the POC
        return [
            s.strip()
            for s in text.replace("!", ".").replace("?", ".").split(".")
            if len(s.strip()) > 20
        ]

    def generate_summary(self, query: str, context_documents: List[Dict]) -> str:
        """
        Generate a summary answer based on the query and context documents.

        Strategy: Extractive Summarization (Semantic)
        1. Extract sentences from all context documents.
        2. Embed the query and all sentences.
        3. Find sentences most similar to the query.
        4. Return top k sentences as the 'answer'.
        """
        if not context_documents:
            return "No documents found to summarize."

        all_sentences = []
        for doc in context_documents:
            # Prefer content, fallback to background/scope
            text = (
                doc.get("content")
                or f"{doc.get('background', '')} {doc.get('scope', '')}"
            )
            sentences = self._split_into_sentences(text)
            all_sentences.extend(sentences)

        if not all_sentences:
            return "Content is too short to summarize."

        # Limit to reasonable amount to avoid freezing CPU
        all_sentences = all_sentences[:500]

        # Embeddings
        query_embedding = self.model.encode(query)
        sentence_embeddings = self.model.encode(all_sentences)

        # Calculate Cosine Similarity
        # (normalized vectors assumed for dot product to be cosine sim, SentenceTransformer usually returns normalized?)
        # Actually utilize util.cos_sim if available, or manual dot product
        from sentence_transformers import util

        scores = util.cos_sim(query_embedding, sentence_embeddings)[0]

        # Get top 5 sentences
        top_k = min(5, len(all_sentences))
        top_indices = np.argsort(scores.numpy())[-top_k:][::-1]

        k_sentences = [all_sentences[i] for i in top_indices]

        # Construct summary
        summary = "Based on the search results, here are the most relevant points:\n\n"
        for s in k_sentences:
            summary += f"- {s}.\n"

        return summary
