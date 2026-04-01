--DROP TABLE IF EXISTS rosters;
--DROP TABLE IF EXISTS managers;
--DROP TABLE IF EXISTS players;

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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    transfers_used INTEGER DEFAULT 0,
    COLUMN captain_changes_used INTEGER DEFAULT 0
);

-- 3. Rosters Table (The 9 players selected by each manager)
CREATE TABLE rosters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id UUID REFERENCES managers(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id),
    is_captain BOOLEAN DEFAULT FALSE,
    division TEXT NOT NULL, -- Helps with the 4/4/1 logic later
    acquired_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_to TIMESTAMP WITH TIME ZONE;
);

-- 4. Changes (log of transfers)
CREATE TABLE transfer_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id UUID REFERENCES managers(id),
    player_out_id UUID REFERENCES players(id),
    player_in_id UUID REFERENCES players(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);