import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SCHEMA = "dev"

# --- SETUP ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_migrations():
    """Run database migrations to update schema for game-based scoring."""

    print("🚀 Starting database migrations...")

    try:
        # Migration 1: Add columns to player_scores table
        print("📝 Updating player_scores table...")
        supabase.rpc('exec_sql', {
            'sql': f'''
                ALTER TABLE {SCHEMA}.player_scores
                ADD COLUMN IF NOT EXISTS game_number INTEGER,
                ADD COLUMN IF NOT EXISTS goals INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS assists INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS callahans INTEGER DEFAULT 0;
            '''
        }).execute()

        # Migration 2: Drop old columns if they exist
        print("🗑️  Removing old columns...")
        try:
            supabase.rpc('exec_sql', {
                'sql': f'ALTER TABLE {SCHEMA}.player_scores DROP COLUMN IF EXISTS day_number;'
            }).execute()
        except:
            print("day_number column not found or already removed")

        try:
            supabase.rpc('exec_sql', {
                'sql': f'ALTER TABLE {SCHEMA}.player_scores DROP COLUMN IF EXISTS points_earned;'
            }).execute()
        except:
            print("points_earned column not found or already removed")

        # Migration 3: Create games table
        print("🎮 Creating games table...")
        supabase.rpc('exec_sql', {
            'sql': f'''
                CREATE TABLE IF NOT EXISTS {SCHEMA}.games (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    game_number INTEGER NOT NULL UNIQUE,
                    game_date TIMESTAMPTZ NOT NULL,
                    home_team TEXT,
                    away_team TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            '''
        }).execute()

        # Migration 4: Enable RLS on games table
        print("🔒 Enabling RLS on games table...")
        supabase.rpc('exec_sql', {
            'sql': f'ALTER TABLE {SCHEMA}.games ENABLE ROW LEVEL SECURITY;'
        }).execute()

        supabase.rpc('exec_sql', {
            'sql': f'CREATE POLICY "Public Games" ON {SCHEMA}.games FOR ALL USING (true) WITH CHECK (true);'
        }).execute()

        print("✅ Migrations completed successfully!")
        print("🔄 Refreshing schema cache...")
        supabase.rpc('exec_sql', {
            'sql': 'NOTIFY pgrst, \'reload schema\';'
        }).execute()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

    return True

if __name__ == "__main__":
    success = run_migrations()
    if success:
        print("🎉 All migrations completed!")
    else:
        print("💥 Migration failed!")