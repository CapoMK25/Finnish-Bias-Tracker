-- Ensure the pgvector extension exists before attempting to use the vector type
CREATE EXTENSION IF NOT EXISTS vector;

-- Convert TEXT embedding column to vector(768) with an HNSW index.
-- Losslessly casts the existing JSON-text array format into native vectors.
ALTER TABLE "articles"
  ALTER COLUMN "embedding" TYPE vector(768)
  USING embedding::vector;

CREATE INDEX "articles_embedding_idx"
  ON "articles"
  USING hnsw ("embedding" vector_cosine_ops);
