import {
  pgTable,
  uuid,
  text,
  integer,
  timestamp,
  boolean,
  numeric,
  jsonb,
  index,
  uniqueIndex,
} from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

/**
 * Sources: news outlets we track.
 *
 * Bias score is the *source-level* hard label. Per-article scores live in `articleScores`.
 */
export const sources = pgTable('sources', {
  id: uuid('id').defaultRandom().primaryKey(),
  slug: text('slug').notNull().unique(),
  name: text('name').notNull(),
  url: text('url').notNull(),
  rssUrl: text('rss_url'),
  biasScore: integer('bias_score').notNull(), // -3 to +3
  sourceType: text('source_type').notNull(), // party_organ | mainstream | tabloid | business | public | alternative | wire
  ownership: text('ownership'),
  flagged: boolean('flagged').default(false).notNull(),
  language: text('language').notNull().default('fi'), // 'fi' | 'sv' | 'en'
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
});

/**
 * Articles: individual scraped pieces.
 *
 * `embedding` is set after the embedding worker runs.
 * `clusterId` is set after clustering runs.
 */
export const articles = pgTable(
  'articles',
  {
    id: uuid('id').defaultRandom().primaryKey(),
    sourceId: uuid('source_id')
      .notNull()
      .references(() => sources.id, { onDelete: 'cascade' }),
    url: text('url').notNull(),
    title: text('title').notNull(),
    body: text('body').notNull(),
    publishedAt: timestamp('published_at', { withTimezone: true }),
    scrapedAt: timestamp('scraped_at', { withTimezone: true }).defaultNow().notNull(),
    contentHash: text('content_hash').notNull(),
    language: text('language').notNull().default('fi'),
    articleType: text('article_type').notNull().default('news'), // news | opinion | analysis | blog
    // Note: pgvector type is added via raw SQL migration since drizzle-orm doesn't
    // have native pgvector support yet. See migrations/0001_add_pgvector.sql
    clusterId: uuid('cluster_id'),
  },
  (table) => ({
    urlIdx: uniqueIndex('articles_url_idx').on(table.url),
    contentHashIdx: uniqueIndex('articles_content_hash_idx').on(table.contentHash),
    publishedAtIdx: index('articles_published_at_idx').on(table.publishedAt),
    sourceIdIdx: index('articles_source_id_idx').on(table.sourceId),
    clusterIdIdx: index('articles_cluster_id_idx').on(table.clusterId),
  })
);

/**
 * Article scores: per-article bias scoring from LLM.
 *
 * Articles can have multiple scores (different models, different prompt versions, re-scores).
 * The latest score is typically what's shown, but history is preserved for auditability.
 */
export const articleScores = pgTable(
  'article_scores',
  {
    id: uuid('id').defaultRandom().primaryKey(),
    articleId: uuid('article_id')
      .notNull()
      .references(() => articles.id, { onDelete: 'cascade' }),
    biasScore: integer('bias_score').notNull(), // -3 to +3
    confidence: numeric('confidence', { precision: 3, scale: 2 }).notNull(), // 0.00-1.00
    rationale: text('rationale').notNull(),
    examples: jsonb('examples').$type<string[]>().notNull().default([]),
    topic: text('topic'),
    summary: text('summary'),
    model: text('model').notNull(),
    promptVersion: text('prompt_version').notNull(),
    scoredAt: timestamp('scored_at', { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    articleIdIdx: index('article_scores_article_id_idx').on(table.articleId),
    scoredAtIdx: index('article_scores_scored_at_idx').on(table.scoredAt),
  })
);

/**
 * Clusters: groups of articles covering the same story.
 */
export const clusters = pgTable(
  'clusters',
  {
    id: uuid('id').defaultRandom().primaryKey(),
    title: text('title'),
    firstSeenAt: timestamp('first_seen_at', { withTimezone: true }).notNull(),
    lastSeenAt: timestamp('last_seen_at', { withTimezone: true }).notNull(),
    articleCount: integer('article_count').notNull().default(0),
    biasDistribution: jsonb('bias_distribution').$type<Record<string, number>>(),
    entropy: numeric('entropy', { precision: 4, scale: 3 }),
    blindspotLabel: text('blindspot_label'), // left_blindspot | right_blindspot | balanced | null
    createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
  },
  (table) => ({
    lastSeenAtIdx: index('clusters_last_seen_at_idx').on(table.lastSeenAt),
  })
);

/**
 * Human reviews: methodology calibration data.
 */
export const humanReviews = pgTable('human_reviews', {
  id: uuid('id').defaultRandom().primaryKey(),
  articleId: uuid('article_id')
    .notNull()
    .references(() => articles.id, { onDelete: 'cascade' }),
  reviewer: text('reviewer').notNull(),
  humanScore: integer('human_score').notNull(),
  llmScore: integer('llm_score').notNull(),
  notes: text('notes'),
  reviewedAt: timestamp('reviewed_at', { withTimezone: true }).defaultNow().notNull(),
});

// Relations
export const sourcesRelations = relations(sources, ({ many }) => ({
  articles: many(articles),
}));

export const articlesRelations = relations(articles, ({ one, many }) => ({
  source: one(sources, {
    fields: [articles.sourceId],
    references: [sources.id],
  }),
  cluster: one(clusters, {
    fields: [articles.clusterId],
    references: [clusters.id],
  }),
  scores: many(articleScores),
  reviews: many(humanReviews),
}));

export const articleScoresRelations = relations(articleScores, ({ one }) => ({
  article: one(articles, {
    fields: [articleScores.articleId],
    references: [articles.id],
  }),
}));

export const humanReviewsRelations = relations(humanReviews, ({ one }) => ({
  article: one(articles, {
    fields: [humanReviews.articleId],
    references: [articles.id],
  }),
}));

export const clustersRelations = relations(clusters, ({ many }) => ({
  articles: many(articles),
}));
