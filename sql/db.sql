--DROP TABLE IF EXISTS rosters;
--DROP TABLE IF EXISTS managers;
--DROP TABLE IF EXISTS players;
--DROP TABLE IF EXISTS transfer_logs;

-- 1. Players Table (Your master list from the CSV)
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    division TEXT NOT NULL, -- 'opens' or 'womens'
    throwing NUMERIC NOT NULL,
    catching NUMERIC NOT NULL,
    athleticism NUMERIC NOT NULL,
    defense NUMERIC NOT NULL,
    game_iq NUMERIC NOT NULL,
    total NUMERIC NOT NULL,
    price NUMERIC NOT NULL
);

-- 2. Managers Table (The "User" account)
CREATE TABLE managers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_name TEXT NOT NULL,
    pin TEXT NOT NULL, -- Plain text 4-digit PIN for simplicity
    created_at TIMESTAMPTZ,
    transfers_used INTEGER DEFAULT 0,
    captain_changes_used INTEGER DEFAULT 0
);

-- 3. Rosters Table (The 9 players selected by each manager)
CREATE TABLE rosters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id UUID REFERENCES managers(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id),
    is_captain BOOLEAN DEFAULT FALSE,
    division TEXT NOT NULL, -- Helps with the 4/4/1 logic later
    acquired_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ
);

-- 5. Recommended Index for Performance
-- This makes looking up the "current" roster (where valid_to is null) lightning fast
CREATE INDEX idx_roster_active_lookup ON rosters (manager_id, valid_from, valid_to);

-- 4. Changes (log of transfers)
CREATE TABLE transfer_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id UUID REFERENCES managers(id),
    player_out_id UUID REFERENCES players(id),
    player_in_id UUID REFERENCES players(id),
    changed_at TIMESTAMPTZ
);

-- scores
-- 1. Create the Table with constraints built-in
CREATE TABLE IF NOT EXISTS player_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Adding UNIQUE right here is the fastest way to set it up
    player_id UUID UNIQUE NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    
    player_name TEXT,
    total_score NUMERIC DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Performance Index (Still recommended for fast lookups)
CREATE INDEX IF NOT EXISTS idx_player_scores_player_id ON player_scores(player_id);

-- 3. Security (Ensures your app can read the data)
ALTER TABLE player_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read access" ON player_scores FOR SELECT USING (true);