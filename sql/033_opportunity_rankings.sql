-- Step 188: Opportunity rankings – store ranked opportunity scores with signal components.
-- opportunity_score (final), rank, demand/competition/trend/price_stability/listing_density, history blending.

CREATE TABLE IF NOT EXISTS opportunity_rankings (
    id SERIAL PRIMARY KEY,
    opportunity_ref TEXT NOT NULL,
    opportunity_score NUMERIC NOT NULL,
    rank INTEGER,
    demand_score NUMERIC,
    competition_score NUMERIC,
    trend_score NUMERIC,
    price_stability NUMERIC,
    listing_density NUMERIC,
    previous_score NUMERIC,
    score_history JSONB DEFAULT '[]',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opportunity_rankings_ref ON opportunity_rankings(opportunity_ref);
CREATE INDEX IF NOT EXISTS idx_opportunity_rankings_recorded_at ON opportunity_rankings(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_opportunity_rankings_score ON opportunity_rankings(opportunity_score DESC);
