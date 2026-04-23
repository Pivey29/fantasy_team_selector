-- Cleanup (Optional, keep commented unless resetting)
--DROP SCHEMA IF EXISTS prd CASCADE;

-- Create the Schema
CREATE SCHEMA IF NOT EXISTS prd;

-- 1. Players Table
CREATE TABLE prd.players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    division TEXT NOT NULL, 
    throwing NUMERIC DEFAULT 0,
    avg_assists NUMERIC DEFAULT 0,
    athleticism NUMERIC DEFAULT 0,
    avg_goals NUMERIC DEFAULT 0,
    game_iq NUMERIC DEFAULT 0,
    total NUMERIC DEFAULT 0,
    price NUMERIC DEFAULT 0,
    has_submitted_rank BOOLEAN DEFAULT FALSE
);

-- 2. Managers Table
CREATE TABLE prd.managers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_name TEXT NOT NULL,
    team_name TEXT UNIQUE NOT NULL,
    pin TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    transfers_used INTEGER DEFAULT 0,
    captain_changes_used INTEGER DEFAULT 0
);


-- 3. Rosters Table 
CREATE TABLE prd.rosters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id UUID REFERENCES prd.managers(id) ON DELETE CASCADE,
    player_id UUID REFERENCES prd.players(id),
    is_captain BOOLEAN DEFAULT FALSE,
    player_role TEXT DEFAULT 'hybrid' CHECK (player_role IN ('handler', 'cutter', 'hybrid')),
    division TEXT NOT NULL, 
    acquired_at TIMESTAMPTZ DEFAULT now(),
    valid_from TIMESTAMPTZ DEFAULT now(),
    valid_to TIMESTAMPTZ -- NULL means currently active
);

-- 4. Player Scores
CREATE TABLE prd.player_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES prd.players(id) ON DELETE CASCADE,
    match_id TEXT,
    game_datetime TIMESTAMPTZ NOT NULL,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    callahans INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    CONSTRAINT unique_player_game UNIQUE (player_id, game_datetime)
);

-- MIGRATION: Add player_role to existing rosters table (if not already present)
-- Uncomment and run if updating an existing database:
--ALTER TABLE prd.rosters ADD COLUMN IF NOT EXISTS player_role TEXT DEFAULT 'hybrid' CHECK (player_role IN ('handler', 'cutter', 'hybrid'));
-- If migrating from neutral to hybrid values:
--UPDATE prd.rosters SET player_role = 'hybrid' WHERE player_role = 'neutral';

-- MIGRATION: Update player_scores table for game-based scoring
-- Uncomment and run if updating an existing database:
--ALTER TABLE prd.player_scores ADD COLUMN IF NOT EXISTS game_number INTEGER;
--ALTER TABLE prd.player_scores ADD COLUMN IF NOT EXISTS goals INTEGER DEFAULT 0;
--ALTER TABLE prd.player_scores ADD COLUMN IF NOT EXISTS assists INTEGER DEFAULT 0;
--ALTER TABLE prd.player_scores ADD COLUMN IF NOT EXISTS callahans INTEGER DEFAULT 0;
--ALTER TABLE prd.player_scores ADD COLUMN IF NOT EXISTS game_datetime TIMESTAMPTZ;
--ALTER TABLE prd.player_scores DROP COLUMN IF EXISTS day_number;
--ALTER TABLE prd.player_scores DROP COLUMN IF EXISTS points_earned;

-- MIGRATION: Update rosters player_role constraint to include 'hybrid'
-- Uncomment and run if updating an existing database:
-- First update any 'neutral' values to 'hybrid'
--UPDATE prd.rosters SET player_role = 'hybrid' WHERE player_role = 'neutral';
-- Then drop the old constraint and add the new one
--ALTER TABLE prd.rosters DROP CONSTRAINT IF EXISTS rosters_player_role_check;
--ALTER TABLE prd.rosters ADD CONSTRAINT rosters_player_role_check CHECK (player_role IN ('handler', 'cutter', 'hybrid'));

-- MIGRATION: Create games table for tournament tracking
-- Uncomment and run if updating an existing database:
--CREATE TABLE prd.games (
--    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--    game_number INTEGER NOT NULL UNIQUE,
--    game_date TIMESTAMPTZ NOT NULL,
--    home_team TEXT,
--    away_team TEXT,
--    created_at TIMESTAMPTZ DEFAULT now()
--);

-- 5. Security & Permissions (The "No-Headache" Configuration)
-- Enable RLS on all
ALTER TABLE prd.players ENABLE ROW LEVEL SECURITY;
ALTER TABLE prd.managers ENABLE ROW LEVEL SECURITY;
ALTER TABLE prd.rosters ENABLE ROW LEVEL SECURITY;
ALTER TABLE prd.player_scores ENABLE ROW LEVEL SECURITY;

-- Create "Universal Access" Policies for the App
-- Players: Read for all, Update for self-ranking
CREATE POLICY "Public Players" ON prd.players FOR ALL USING (true) WITH CHECK (true);

-- Managers: Read, Insert (signup), Update (transfers)
CREATE POLICY "Public Managers" ON prd.managers FOR ALL USING (true) WITH CHECK (true);

-- Rosters: Read, Insert, Update (sunset), Delete (draft resets)
CREATE POLICY "Public Rosters" ON prd.rosters FOR ALL USING (true) WITH CHECK (true);

-- Scores: Read, Insert/Update (via sync script)
CREATE POLICY "Public Scores" ON prd.player_scores FOR ALL USING (true) WITH CHECK (true);

-- 6. Grant Schema Access
GRANT USAGE ON SCHEMA prd TO anon, authenticated, service_role;

-- 7. Grant Table Permissions (ALL is safer for your rapid prdelopment)
GRANT ALL ON ALL TABLES IN SCHEMA prd TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA prd TO anon, authenticated, service_role;

-- 8. Ensure future tables inherit these rights
ALTER DEFAULT PRIVILEGES IN SCHEMA prd 
GRANT ALL ON TABLES TO anon, authenticated, service_role;

-- 9. Refresh API Cache
NOTIFY pgrst, 'reload schema';

CREATE TABLE prd.matches (
    id TEXT PRIMARY KEY,
    division TEXT NOT NULL, -- 'Open' or 'Women'
    stage TEXT NOT NULL,    -- e.g., 'Pool A', 'Finals'
    team_a TEXT NOT NULL,
    team_b TEXT NOT NULL,
    
    -- Results
    score_a INT DEFAULT NULL,
    score_b INT DEFAULT NULL,
    
    -- Spirit Team A (Scores awarded TO Team A by Team B)
    s_rules_a INT DEFAULT 2,
    s_fouls_a INT DEFAULT 2,
    s_fair_a INT DEFAULT 2,
    s_pos_a INT DEFAULT 2,
    s_comm_a INT DEFAULT 2,
    spirit_total_a INT DEFAULT 0,
    mrp_a TEXT DEFAULT NULL,

    -- Spirit Team B (Scores awarded TO Team B by Team A)
    s_rules_b INT DEFAULT 2,
    s_fouls_b INT DEFAULT 2,
    s_fair_b INT DEFAULT 2,
    s_pos_b INT DEFAULT 2,
    s_comm_b INT DEFAULT 2,
    spirit_total_b INT DEFAULT 0,
    mrp_b TEXT DEFAULT NULL,

    -- Metadata
    field TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'scheduled', -- 'scheduled', 'completed'
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);