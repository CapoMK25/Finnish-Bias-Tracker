CREATE TABLE IF NOT EXISTS "article_scores" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"article_id" uuid NOT NULL,
	"bias_score" integer NOT NULL,
	"confidence" numeric(3, 2) NOT NULL,
	"rationale" text NOT NULL,
	"examples" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"topic" text,
	"summary" text,
	"model" text NOT NULL,
	"prompt_version" text NOT NULL,
	"scored_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "articles" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"source_id" uuid NOT NULL,
	"url" text NOT NULL,
	"title" text NOT NULL,
	"body" text NOT NULL,
	"published_at" timestamp with time zone,
	"scraped_at" timestamp with time zone DEFAULT now() NOT NULL,
	"content_hash" text NOT NULL,
	"language" text DEFAULT 'fi' NOT NULL,
	"article_type" text DEFAULT 'news' NOT NULL,
	"cluster_id" uuid
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "clusters" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"title" text,
	"first_seen_at" timestamp with time zone NOT NULL,
	"last_seen_at" timestamp with time zone NOT NULL,
	"article_count" integer DEFAULT 0 NOT NULL,
	"bias_distribution" jsonb,
	"entropy" numeric(4, 3),
	"blindspot_label" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "human_reviews" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"article_id" uuid NOT NULL,
	"reviewer" text NOT NULL,
	"human_score" integer NOT NULL,
	"llm_score" integer NOT NULL,
	"notes" text,
	"reviewed_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "sources" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"slug" text NOT NULL,
	"name" text NOT NULL,
	"url" text NOT NULL,
	"rss_url" text,
	"bias_score" integer NOT NULL,
	"source_type" text NOT NULL,
	"ownership" text,
	"flagged" boolean DEFAULT false NOT NULL,
	"language" text DEFAULT 'fi' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "sources_slug_unique" UNIQUE("slug")
);
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "article_scores" ADD CONSTRAINT "article_scores_article_id_articles_id_fk" FOREIGN KEY ("article_id") REFERENCES "public"."articles"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "articles" ADD CONSTRAINT "articles_source_id_sources_id_fk" FOREIGN KEY ("source_id") REFERENCES "public"."sources"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "human_reviews" ADD CONSTRAINT "human_reviews_article_id_articles_id_fk" FOREIGN KEY ("article_id") REFERENCES "public"."articles"("id") ON DELETE cascade ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "article_scores_article_id_idx" ON "article_scores" USING btree ("article_id");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "article_scores_scored_at_idx" ON "article_scores" USING btree ("scored_at");--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS "articles_url_idx" ON "articles" USING btree ("url");--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS "articles_content_hash_idx" ON "articles" USING btree ("content_hash");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "articles_published_at_idx" ON "articles" USING btree ("published_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "articles_source_id_idx" ON "articles" USING btree ("source_id");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "articles_cluster_id_idx" ON "articles" USING btree ("cluster_id");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "clusters_last_seen_at_idx" ON "clusters" USING btree ("last_seen_at");