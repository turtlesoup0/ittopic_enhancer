"""Topic-Reference matching service with weighted embedding and trust score integration."""
import chromadb
from chromadb.config import Settings
from typing import List, Optional
import uuid
import logging
import numpy as np

from app.services.matching.embedding import get_embedding_service
from app.models.topic import Topic
from app.models.reference import ReferenceDocument, MatchedReference, ReferenceSourceType
from app.core.config import get_settings
from app.core.errors import ChromaDBError
from app.core.resilience import with_circuit_breaker, get_circuit_breaker
from app.core.logging import get_logger, log_error

logger = get_logger(__name__)
settings = get_settings()


class MatchingService:
    """Service for matching topics with reference documents using weighted embeddings."""

    # Field weights for embedding generation
    FIELD_WEIGHTS = {
        "definition": settings.field_weight_definition,      # 0.35
        "lead": settings.field_weight_lead,                  # 0.25
        "keywords": settings.field_weight_keywords,          # 0.25
        "hashtags": settings.field_weight_hashtags,          # 0.10
        "memory": settings.field_weight_memory,              # 0.05
    }

    # Trust scores by source type
    TRUST_SCORES = {
        ReferenceSourceType.PDF_BOOK: settings.trust_score_pdf_book,    # 1.0
        ReferenceSourceType.MARKDOWN: settings.trust_score_markdown,     # 0.6
    }

    # Similarity thresholds by source type
    SIMILARITY_THRESHOLDS = {
        ReferenceSourceType.PDF_BOOK: settings.similarity_threshold_pdf_book,    # 0.65
        ReferenceSourceType.MARKDOWN: settings.similarity_threshold_markdown,     # 0.7
    }

    def __init__(self):
        """Initialize matching service."""
        self.embedding_service = get_embedding_service()
        self._client = None
        self._collection = None
        # Circuit Breaker for ChromaDB
        self._circuit_breaker = get_circuit_breaker(
            service_name="chromadb",
            failure_threshold=5,
            recovery_timeout=60.0,
        )

    @property
    def client(self):
        """Get ChromaDB client."""
        if self._client is None:
            try:
                self._client = chromadb.PersistentClient(
                    path=settings.chromadb_path,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                logger.info("chromadb_client_initialized", path=settings.chromadb_path)
            except Exception as e:
                log_error(
                    logger,
                    ChromaDBError(
                        message=f"Failed to initialize ChromaDB client: {e}",
                        operation="initialize_client",
                        original_error=e,
                    ),
                )
                raise
        return self._client

    @property
    def collection(self):
        """Get or create ChromaDB collection."""
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=settings.chromadb_collection,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("chromadb_collection_accessed", name=settings.chromadb_collection)
            except Exception as e:
                log_error(
                    logger,
                    ChromaDBError(
                        message=f"Failed to get or create collection: {e}",
                        operation="get_or_create_collection",
                        original_error=e,
                    ),
                )
                raise
        return self._collection

    def _chunk_document(self, content: str) -> List[str]:
        """
        Split document into chunks if it exceeds threshold.

        Args:
            content: Document content to chunk

        Returns:
            List of content chunks
        """
        if len(content) <= settings.chunk_size_threshold:
            return [content]

        chunks = []
        start = 0
        content_length = len(content)

        while start < content_length:
            end = start + settings.chunk_size_threshold

            # Try to find a good break point (newline or period)
            if end < content_length:
                # Look for sentence boundary
                for break_char in ['\n\n', '\n', '. ']:
                    last_break = content.rfind(break_char, start, end)
                    if last_break != -1 and last_break > start:
                        end = last_break + len(break_char)
                        break

            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = max(start + 1, end - settings.chunk_overlap)

        return chunks

    def _prepare_weighted_topic_text(self, topic: Topic) -> str:
        """
        Prepare topic text for embedding with field weights.

        Creates a weighted representation by repeating fields according to their weights.
        Higher weight fields appear more frequently in the resulting text.

        Args:
            topic: Topic to prepare text for

        Returns:
            Weighted text string for embedding
        """
        weighted_parts = []

        # 정의 (definition) - weight 0.35
        if topic.content.정의:
            # Repeat 3 times to achieve ~0.35 weight (3/8 = 0.375)
            weighted_parts.extend([topic.content.정의] * 3)

        # 리드문 (lead) - weight 0.25
        if topic.content.리드문:
            # Repeat 2 times to achieve ~0.25 weight (2/8 = 0.25)
            weighted_parts.extend([topic.content.리드문] * 2)

        # 키워드 (keywords) - weight 0.25
        if topic.content.키워드:
            keywords_text = " ".join(topic.content.키워드)
            # Repeat 2 times to achieve ~0.25 weight
            weighted_parts.extend([keywords_text] * 2)

        # 해시태그 (hashtags) - weight 0.10
        if topic.content.해시태그:
            # Single inclusion for ~0.125 weight (1/8)
            weighted_parts.append(topic.content.해시태그)

        # 암기 (memory) - weight 0.05
        if topic.content.암기:
            # Single inclusion for ~0.125 weight
            weighted_parts.append(topic.content.암기)

        # Join with space
        return " ".join(weighted_parts)

    def _compute_final_score(self, similarity_score: float, trust_score: float) -> float:
        """
        Compute final score combining similarity and trust.

        Formula: final_score = similarity_score * (base_weight + trust_weight * trust_score)

        Args:
            similarity_score: Raw cosine similarity score (0-1)
            trust_score: Trust score of the source (0-1)

        Returns:
            Final adjusted score (0-1)
        """
        trust_factor = settings.base_similarity_weight + settings.trust_score_weight * trust_score
        final_score = similarity_score * trust_factor
        return float(max(0.0, min(1.0, final_score)))

    def _get_similarity_threshold(self, source_type: ReferenceSourceType) -> float:
        """Get similarity threshold for a specific source type."""
        return self.SIMILARITY_THRESHOLDS.get(
            source_type,
            settings.similarity_threshold  # Default threshold
        )

    def _get_default_trust_score(self, source_type: ReferenceSourceType) -> float:
        """Get default trust score for a specific source type."""
        return self.TRUST_SCORES.get(source_type, 0.7)  # Default 0.7

    async def index_references(self, references: List[ReferenceDocument]) -> int:
        """
        Index reference documents in vector database.

        Handles document chunking for large documents (>5000 chars).

        Args:
            references: List of reference documents

        Returns:
            Number of successfully indexed reference chunks
        """
        if not references:
            return 0

        async def _index():
            indexed_count = 0
            chunks_to_index = []

            # Generate embeddings and chunk large documents
            for ref in references:
                # Set default trust score if not provided
                if ref.trust_score == 1.0:  # Default value
                    ref.trust_score = self._get_default_trust_score(ref.source_type)

                # Chunk large documents
                content_chunks = self._chunk_document(ref.content)

                for chunk_idx, chunk in enumerate(content_chunks):
                    # Generate embedding for chunk
                    chunk_embedding = self.embedding_service.encode(chunk).tolist()

                    # Create unique chunk ID
                    chunk_id = f"{ref.id}_chunk{chunk_idx}" if len(content_chunks) > 1 else ref.id

                    chunks_to_index.append({
                        "id": chunk_id,
                        "embedding": chunk_embedding,
                        "content": chunk[:10000],  # ChromaDB size limit
                        "metadata": {
                            "domain": ref.domain,
                            "source_type": ref.source_type.value,
                            "trust_score": ref.trust_score,
                            "title": ref.title[:500],
                            "parent_id": ref.id,
                            "is_chunk": len(content_chunks) > 1,
                            "chunk_index": chunk_idx,
                        }
                    })

            # Prepare data for ChromaDB
            if chunks_to_index:
                ids = [c["id"] for c in chunks_to_index]
                embeddings = [c["embedding"] for c in chunks_to_index]
                documents = [c["content"] for c in chunks_to_index]
                metadatas = [c["metadata"] for c in chunks_to_index]

                # Add to collection
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )

                indexed_count = len(chunks_to_index)

            logger.info("references_indexed", count=len(references), chunks=indexed_count)
            return indexed_count

        try:
            return await with_circuit_breaker("chromadb", _index)
        except Exception as e:
            log_error(
                logger,
                ChromaDBError(
                    message=f"Failed to index references: {e}",
                    operation="index_references",
                    original_error=e,
                ),
            )
            raise

    async def find_references(
        self,
        topic: Topic,
        top_k: int = 5,
        domain_filter: Optional[str] = None,
    ) -> List[MatchedReference]:
        """
        Find matching reference documents for a topic.

        Uses weighted embeddings for topic representation and combines
        similarity with trust scores for final ranking.

        Args:
            topic: Topic to find references for
            top_k: Number of top matches to return
            domain_filter: Optional domain filter

        Returns:
            List of matched references with adjusted similarity scores
        """
        async def _find():
            # Generate weighted topic embedding
            topic_text = self._prepare_weighted_topic_text(topic)
            topic_embedding = self.embedding_service.encode(topic_text).tolist()

            # Build where clause for filtering
            where_clause = None
            if domain_filter and domain_filter != "all":
                where_clause = {"domain": domain_filter}

            # Query ChromaDB - get more candidates for filtering
            results = self.collection.query(
                query_embeddings=[topic_embedding],
                n_results=min(top_k * 3, 100),  # Get more candidates for threshold filtering
                where=where_clause,
            )

            # Process results with trust score integration
            matched_references = []
            seen_parent_ids = set()  # Track parent IDs to deduplicate chunks

            if results["ids"] and results["ids"][0]:
                for i, ref_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    source_type = ReferenceSourceType(metadata.get("source_type", "markdown"))

                    # Get similarity threshold for this source type
                    threshold = self._get_similarity_threshold(source_type)

                    # Get raw similarity score
                    raw_similarity = 1 - results["distances"][0][i]  # Convert distance to similarity

                    # Get trust score
                    trust_score = metadata.get("trust_score", self._get_default_trust_score(source_type))

                    # Compute final score
                    final_score = self._compute_final_score(raw_similarity, trust_score)

                    # Only include if above threshold
                    if final_score >= threshold:
                        parent_id = metadata.get("parent_id", ref_id)

                        # Skip if we already have a chunk from this document with higher score
                        if parent_id in seen_parent_ids:
                            continue

                        # Extract relevant snippet
                        document = results["documents"][0][i] if results["documents"] else ""

                        matched_references.append(
                            MatchedReference(
                                reference_id=parent_id,
                                title=metadata.get("title", "Unknown"),
                                source_type=source_type,
                                similarity_score=final_score,  # Use final adjusted score
                                domain=metadata.get("domain", ""),
                                trust_score=trust_score,
                                relevant_snippet=document[:500],
                            )
                        )
                        seen_parent_ids.add(parent_id)

                    # Stop if we have enough results
                    if len(matched_references) >= top_k:
                        break

            # Sort by final score
            matched_references.sort(key=lambda x: x.similarity_score, reverse=True)

            logger.info(
                "references_found",
                topic_id=topic.id,
                count=len(matched_references),
            )
            return matched_references

        try:
            return await with_circuit_breaker("chromadb", _find)
        except Exception as e:
            log_error(
                logger,
                ChromaDBError(
                    message=f"Failed to find references for topic {topic.id}: {e}",
                    operation="find_references",
                    topic_id=topic.id,
                    original_error=e,
                ),
            )
            # Return empty list on error (degraded behavior)
            return []

    async def reset_collection(self):
        """Reset the entire collection."""
        async def _reset():
            self.client.delete_collection(settings.chromadb_collection)
            self._collection = None
            logger.info("collection_reset", name=settings.chromadb_collection)

        try:
            await with_circuit_breaker("chromadb", _reset)
        except Exception as e:
            log_error(
                logger,
                ChromaDBError(
                    message=f"Failed to reset collection: {e}",
                    operation="reset_collection",
                    original_error=e,
                ),
            )
            raise


# Global matching service instance
_matching_service: MatchingService | None = None


def get_matching_service() -> MatchingService:
    """Get or create global matching service instance."""
    global _matching_service
    if _matching_service is None:
        _matching_service = MatchingService()
    return _matching_service
