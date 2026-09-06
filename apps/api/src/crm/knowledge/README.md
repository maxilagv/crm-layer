# Knowledge

Backend RAG knowledge base for business facts used by AI replies and document drafts.

Embeddings are stored in `crm.ai.AIEmbedding` with `owner_type="knowledge_chunk"` and
`owner_id=KnowledgeChunk.id`; there is no separate knowledge embedding table.

Reindexing legacy embeddings uses `AIEmbedding.source_text`, which is capped at 4000 chars.
That makes long legacy message reindexing lossy, while knowledge chunks are exact because
they are capped at the knowledge chunk size.

Retrieve/context results are cached for `KNOWLEDGE_CACHE_TTL`; after re-ingestion, already
cached queries may return previous chunks until the TTL expires.

TODO FE: add a Settings page named "Base de conocimiento", analogous to Documents, for
uploading manual text/PDF sources and showing ingest status.
