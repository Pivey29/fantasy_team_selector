-- Cleanup (Optional, keep commented unless resetting)
-- DROP SCHEMA IF EXISTS prd CASCADE;

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
    total NUMERIC DEFAULT 0,
    price NUMERIC DEFAULT 0,
    has_submitted_rank BOOLEAN DEFAULT FALSE
);

-- 2. Managers Table 
CREATE TABLE prd.managers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_name TEXT NOT NULL,
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
    division TEXT NOT NULL, 
    acquired_at TIMESTAMPTZ DEFAULT now(),
    valid_from TIMESTAMPTZ DEFAULT now(),
    valid_to TIMESTAMPTZ -- NULL means currently active
);

-- 4. Player Scores
CREATE TABLE prd.player_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES prd.players(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    points_earned NUMERIC DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    CONSTRAINT unique_player_day UNIQUE (player_id, day_number)
);

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

-- 7. Grant Table Permissions (ALL is safer for your rapid development)
GRANT ALL ON ALL TABLES IN SCHEMA prd TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA prd TO anon, authenticated, service_role;

-- 8. Ensure future tables inherit these rights
ALTER DEFAULT PRIVILEGES IN SCHEMA prd 
GRANT ALL ON TABLES TO anon, authenticated, service_role;

-- 9. Refresh API Cache
NOTIFY pgrst, 'reload schema';