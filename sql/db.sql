--DROP TABLE IF EXISTS rosters;
--DROP TABLE IF EXISTS managers;
--DROP TABLE IF EXISTS players;
--DROP TABLE IF EXISTS transfer_logs;

-- Create the Schema
CREATE SCHEMA IF NOT EXISTS prd;

-- 1. Players Table
CREATE TABLE prd.players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    division TEXT NOT NULL, 
    throwing NUMERIC DEFAULT 0,
    catching NUMERIC DEFAULT 0,
    athleticism NUMERIC DEFAULT 0,
    defense NUMERIC DEFAULT 0,
    game_iq NUMERIC DEFAULT 0,
    total NUMERIC DEFAULT 0,  -- calculated
    price NUMERIC DEFAULT 0, -- calculated
    has_submitted_rank BOOLEAN DEFAULT FALSE
);

-- 2. Managers Table 
CREATE TABLE prd.managers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_name TEXT NOT NULL,
    pin TEXT NOT NULL, 
    created_at TIMESTAMPTZ,
    transfers_used INTEGER DEFAULT 0,
    captain_changes_used INTEGER DEFAULT 0
);

-- 3. Rosters Table 
CREATE TABLE prd.rosters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id UUID REFERENCES prd.managers(id) ON DELETE CASCADE,
    player_id UUID REFERENCES prd.players(id),
    is_captain BOOLEAN DEFAULT FALSE,
    division TEXT NOT NULL, 
    acquired_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ -- currently active
);

-- 4. Player Scores (The Daily Ledger)
CREATE TABLE prd.player_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES prd.players(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL, -- 1, 2, 3...
    points_earned NUMERIC DEFAULT 0,
    updated_at TIMESTAMPTZ,
    
    -- UNIQUE constraint: One player can only have one score record PER DAY
    CONSTRAINT unique_player_day UNIQUE (player_id, day_number)
);

-- 5. Indexes for Speed
CREATE INDEX idx_roster_active_lookup ON prd.rosters (manager_id, valid_from, valid_to);
CREATE INDEX idx_scores_lookup ON prd.player_scores (player_id, day_number);

-- 6. Security (RLS)
ALTER TABLE prd.players ENABLE ROW LEVEL SECURITY;
ALTER TABLE prd.managers ENABLE ROW LEVEL SECURITY;
ALTER TABLE prd.rosters ENABLE ROW LEVEL SECURITY;
ALTER TABLE prd.player_scores ENABLE ROW LEVEL SECURITY;

-- Simple "Public Read" policies for all tables
CREATE POLICY "Allow public read players" ON prd.players FOR SELECT USING (true);
CREATE POLICY "Allow public read managers" ON prd.managers FOR SELECT USING (true);
CREATE POLICY "Allow public read rosters" ON prd.rosters FOR SELECT USING (true);
CREATE POLICY "Allow public read scores" ON prd.player_scores FOR SELECT USING (true);

-- 1. Grant "Usage" (the ability to enter the schema)
GRANT USAGE ON SCHEMA prd TO anon, authenticated, service_role;

-- 2. Grant "Select" (the ability to read data) on all current tables
GRANT SELECT ON ALL TABLES IN SCHEMA prd TO anon, authenticated, service_role;

-- 3. Grant "Insert/Update" (the ability to submit ratings/drafts)
GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA prd TO anon, authenticated, service_role;

-- 4. Ensure future tables in this schema also get these permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA prd 
GRANT SELECT, INSERT, UPDATE ON TABLES TO anon, authenticated, service_role;

CREATE POLICY "Allow public read access" ON prd.players
  FOR SELECT USING (true);

-- 3. Allow the app to update rows (for the ranking form)
CREATE POLICY "Allow public update access" ON prd.players
  FOR UPDATE USING (true);

-- 4. Final cache refresh
NOTIFY pgrst, 'reload schema';

NOTIFY pgrst, 'reload schema';