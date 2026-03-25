-- Step 145: Copilot research memory – store prior copilot research sessions.
-- Links: copilot query, interpreted intent, plan ref, execution ref, insight summary ref, next-step refs, related sessions.

CREATE TABLE IF NOT EXISTS copilot_research_memory (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
    copilot_query TEXT,
    interpreted_intent TEXT,
    research_plan_ref TEXT,
    guided_execution_ref TEXT,
    insight_summary_ref TEXT,
    suggested_next_steps_ref JSONB DEFAULT '[]',
    related_session_ids JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_copilot_research_memory_session_id ON copilot_research_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_copilot_research_memory_workspace ON copilot_research_memory(workspace_id) WHERE workspace_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_copilot_research_memory_created_at ON copilot_research_memory(created_at DESC);
