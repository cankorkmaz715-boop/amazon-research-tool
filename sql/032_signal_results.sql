-- Step 187: Signal results – store analytical signals per opportunity for scoring.
-- demand_estimate, competition_level, trend_signal, price_stability, listing_density.

CREATE TABLE IF NOT EXISTS signal_results (
    id SERIAL PRIMARY KEY,
    opportunity_ref TEXT NOT NULL,
    marketplace TEXT,
    demand_estimate NUMERIC,
    competition_level NUMERIC,
    trend_signal NUMERIC,
    price_stability NUMERIC,
    listing_density NUMERIC,
    signals JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_results_opportunity_ref ON signal_results(opportunity_ref);
CREATE INDEX IF NOT EXISTS idx_signal_results_recorded_at ON signal_results(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_results_marketplace ON signal_results(marketplace) WHERE marketplace IS NOT NULL;
