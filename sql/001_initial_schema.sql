-- Initial schema for Amazon Research Tool. Run once; safe to re-run (IF NOT EXISTS).
-- Tables: asins, product_metrics, price_history, review_history, category_scans, scoring_results, bot_runs, error_logs

-- Core product identity
CREATE TABLE IF NOT EXISTS asins (
    id SERIAL PRIMARY KEY,
    asin TEXT NOT NULL UNIQUE,
    title TEXT,
    brand TEXT,
    category TEXT,
    product_url TEXT,
    main_image_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asins_asin ON asins(asin);
CREATE INDEX IF NOT EXISTS idx_asins_category ON asins(category);

-- Current metrics snapshot (one row per ASIN, updated on refresh)
CREATE TABLE IF NOT EXISTS product_metrics (
    id SERIAL PRIMARY KEY,
    asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
    price NUMERIC(12, 2),
    currency TEXT,
    bsr TEXT,
    rating NUMERIC(3, 2),
    review_count INTEGER,
    seller_count INTEGER,
    fba_signal TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(asin_id)
);

CREATE INDEX IF NOT EXISTS idx_product_metrics_asin_id ON product_metrics(asin_id);

-- Price history for trends
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
    price NUMERIC(12, 2),
    currency TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_history_asin_id ON price_history(asin_id);
CREATE INDEX IF NOT EXISTS idx_price_history_recorded_at ON price_history(recorded_at);

-- Review/rating history
CREATE TABLE IF NOT EXISTS review_history (
    id SERIAL PRIMARY KEY,
    asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
    review_count INTEGER,
    rating NUMERIC(3, 2),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_history_asin_id ON review_history(asin_id);

-- Category scan runs (discovery bot)
CREATE TABLE IF NOT EXISTS category_scans (
    id SERIAL PRIMARY KEY,
    category TEXT,
    scan_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scan_finished_at TIMESTAMPTZ,
    asins_discovered INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running'
);

CREATE INDEX IF NOT EXISTS idx_category_scans_started ON category_scans(scan_started_at);

-- Scoring results (opportunity engine)
CREATE TABLE IF NOT EXISTS scoring_results (
    id SERIAL PRIMARY KEY,
    asin_id INTEGER NOT NULL REFERENCES asins(id) ON DELETE CASCADE,
    competition_score NUMERIC(5, 2),
    demand_score NUMERIC(5, 2),
    opportunity_score NUMERIC(5, 2),
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scoring_results_asin_id ON scoring_results(asin_id);
CREATE INDEX IF NOT EXISTS idx_scoring_results_opportunity ON scoring_results(opportunity_score DESC);

-- Bot run log (scheduler / bots)
CREATE TABLE IF NOT EXISTS bot_runs (
    id SERIAL PRIMARY KEY,
    bot_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_bot_runs_bot_name ON bot_runs(bot_name);
CREATE INDEX IF NOT EXISTS idx_bot_runs_started ON bot_runs(started_at);

-- Error log (monitoring / debugging)
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    message TEXT,
    context JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_error_logs_source ON error_logs(source);
