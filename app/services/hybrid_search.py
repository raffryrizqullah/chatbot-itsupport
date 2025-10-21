"""
Hybrid search service combining vector search with keyword (BM25) search.

Provides better search accuracy by combining semantic similarity (vector)
with exact keyword matching (BM25 algorithm).
"""

from typing import List, Dict, Any, Optional, Tuple
from langchain.schema.document import Document
import logging
import math
from collections import Counter

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    Service for hybrid search combining vector similarity and BM25 keyword matching.

    Hybrid search combines:
    1. Vector search (semantic similarity) - 70% weight
    2. BM25 keyword search (exact term matching) - 30% weight
    """

    def __init__(
        self,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        k1: float = 1.5,
        b: float = 0.75
    ):
        """
        Initialize hybrid search service.

        Args:
            vector_weight: Weight for vector similarity scores (0.0-1.0).
            bm25_weight: Weight for BM25 scores (0.0-1.0).
            k1: BM25 term frequency saturation parameter.
            b: BM25 length normalization parameter.
        """
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.k1 = k1
        self.b = b

        # Ensure weights sum to 1.0
        total_weight = vector_weight + bm25_weight
        if abs(total_weight - 1.0) > 0.001:
            logger.warning(
                f"Weights sum to {total_weight}, normalizing to 1.0"
            )
            self.vector_weight = vector_weight / total_weight
            self.bm25_weight = bm25_weight / total_weight

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization (split by whitespace and lowercase).

        Args:
            text: Text to tokenize.

        Returns:
            List of tokens.
        """
        return text.lower().split()

    def _compute_bm25_scores(
        self,
        query: str,
        documents: List[Document],
        avgdl: Optional[float] = None
    ) -> List[float]:
        """
        Compute BM25 scores for documents given a query.

        BM25 Formula:
        score(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1 + 1)) / (f(qi,D) + k1 * (1 - b + b * |D| / avgdl))

        Where:
        - IDF(qi) = log((N - df(qi) + 0.5) / (df(qi) + 0.5))
        - f(qi,D) = frequency of term qi in document D
        - |D| = document length
        - avgdl = average document length
        - N = total number of documents

        Args:
            query: Search query.
            documents: List of documents to score.
            avgdl: Average document length (computed if not provided).

        Returns:
            List of BM25 scores (one per document).
        """
        if not documents:
            return []

        query_tokens = self._tokenize(query)

        # Tokenize all documents
        doc_tokens_list = [
            self._tokenize(doc.page_content) for doc in documents
        ]

        # Compute average document length if not provided
        if avgdl is None:
            avgdl = sum(len(tokens) for tokens in doc_tokens_list) / len(doc_tokens_list)

        # Compute document frequencies (df) for each query term
        N = len(documents)
        df = {}
        for token in query_tokens:
            df[token] = sum(1 for doc_tokens in doc_tokens_list if token in doc_tokens)

        # Compute IDF for each query term
        idf = {}
        for token in query_tokens:
            idf[token] = math.log((N - df[token] + 0.5) / (df[token] + 0.5) + 1.0)

        # Compute BM25 score for each document
        scores = []
        for doc_tokens in doc_tokens_list:
            score = 0.0
            doc_len = len(doc_tokens)
            term_freqs = Counter(doc_tokens)

            for token in query_tokens:
                if token in term_freqs:
                    freq = term_freqs[token]
                    numerator = freq * (self.k1 + 1)
                    denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / avgdl)
                    score += idf[token] * (numerator / denominator)

            scores.append(score)

        return scores

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """
        Normalize scores to 0.0-1.0 range using min-max normalization.

        Args:
            scores: Raw scores.

        Returns:
            Normalized scores (0.0-1.0).
        """
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        # Avoid division by zero
        if max_score == min_score:
            return [1.0] * len(scores)

        return [
            (score - min_score) / (max_score - min_score)
            for score in scores
        ]

    def rerank_with_keywords(
        self,
        query: str,
        documents: List[Document],
        vector_scores: List[float]
    ) -> Tuple[List[Document], List[float]]:
        """
        Re-rank documents using hybrid search (vector + BM25).

        Args:
            query: Search query.
            documents: Retrieved documents from vector search.
            vector_scores: Similarity scores from vector search.

        Returns:
            Tuple of (reranked_documents, hybrid_scores).
        """
        if not documents:
            return documents, vector_scores

        logger.info(f"Applying hybrid search re-ranking for query: '{query[:50]}...'")

        # Compute BM25 scores
        bm25_scores = self._compute_bm25_scores(query, documents)

        # Normalize both score sets to 0.0-1.0
        normalized_vector = self._normalize_scores(vector_scores)
        normalized_bm25 = self._normalize_scores(bm25_scores)

        # Compute hybrid scores (weighted combination)
        hybrid_scores = [
            self.vector_weight * v_score + self.bm25_weight * b_score
            for v_score, b_score in zip(normalized_vector, normalized_bm25)
        ]

        # Re-rank by hybrid scores
        ranked_pairs = sorted(
            zip(documents, hybrid_scores, vector_scores, bm25_scores),
            key=lambda x: x[1],
            reverse=True
        )

        reranked_docs = [doc for doc, _, _, _ in ranked_pairs]
        reranked_hybrid_scores = [score for _, score, _, _ in ranked_pairs]

        # Log top result improvement
        if ranked_pairs:
            top_doc, top_hybrid, top_vector, top_bm25 = ranked_pairs[0]
            logger.info(
                f"Top result: hybrid={top_hybrid:.3f} (vector={top_vector:.3f}, bm25={top_bm25:.3f})"
            )

        return reranked_docs, reranked_hybrid_scores

    def boost_by_metadata(
        self,
        query: str,
        documents: List[Document],
        scores: List[float],
        boost_config: Optional[Dict[str, float]] = None
    ) -> Tuple[List[Document], List[float]]:
        """
        Boost scores based on metadata field matches.

        Args:
            query: Search query.
            documents: Documents to boost.
            scores: Current scores.
            boost_config: Boost amounts per metadata field.
                Example: {"keywords": 0.1, "category": 0.05}

        Returns:
            Tuple of (documents, boosted_scores).
        """
        if boost_config is None:
            boost_config = {
                "keywords": 0.15,  # Keyword match boost
                "category": 0.10,  # Category match boost
                "platform": 0.05,  # Platform match boost
            }

        query_lower = query.lower()
        query_words = set(query_lower.split())

        boosted_scores = scores.copy()

        for idx, doc in enumerate(documents):
            metadata = doc.metadata or {}

            # Keyword boost
            keywords = metadata.get("keywords", [])
            if keywords and isinstance(keywords, list):
                keyword_matches = sum(
                    1 for kw in keywords
                    if kw.lower() in query_lower
                )
                if keyword_matches > 0:
                    boost = boost_config.get("keywords", 0.1) * keyword_matches
                    boosted_scores[idx] = min(boosted_scores[idx] + boost, 1.0)
                    logger.debug(
                        f"Keyword boost: +{boost:.2f} for {keyword_matches} matches"
                    )

            # Category boost
            category = metadata.get("category", "").lower()
            if category and category in query_lower:
                boost = boost_config.get("category", 0.05)
                boosted_scores[idx] = min(boosted_scores[idx] + boost, 1.0)
                logger.debug(f"Category boost: +{boost:.2f} for '{category}'")

            # Platform boost
            platform = metadata.get("platform", "").lower()
            if platform and platform in query_lower:
                boost = boost_config.get("platform", 0.05)
                boosted_scores[idx] = min(boosted_scores[idx] + boost, 1.0)
                logger.debug(f"Platform boost: +{boost:.2f} for '{platform}'")

        # Re-sort by boosted scores
        sorted_pairs = sorted(
            zip(documents, boosted_scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [doc for doc, _ in sorted_pairs], [score for _, score in sorted_pairs]
