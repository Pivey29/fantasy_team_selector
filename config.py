# basic settings

import pytz
from datetime import datetime

# --- GAME RULES & LABELS ---
TOURNAMENT_NAME = "OW Nationals 2026 - Fantasy Draft"
DIV_OPEN_LABEL = "opens"
DIV_WOMEN_LABEL = "womens"
SCHEMA = "prd"
ROSTER_SIZE= 10
BUDGET_LIMIT = 100
MAX_GENDER_SIZE = 5
MIN_GENDER_SIZE = 5
MAX_TEAM_SIZE = 2
CAPTAIN_MULTIPLIER = 2

# --- PLAYER ROLES & SCORING ---
PLAYER_ROLES = ["handler", "cutter", "hybrid"]
ROLE_DESCRIPTIONS = {
    "handler": "🎯 Handler - Sets up plays (6 pts/assist, 2 pts/goal)",
    "cutter": "🏃 Cutter - Field runner (2 pts/assist, 6 pts/goal)",
    "hybrid": "⚪ Hybrid - Versatile (4 pts/assist, 4 pts/goal)"
}
ROLE_MULTIPLIERS = {
    "handler": {"assists": 6, "goals": 2},  # Handlers get bonus for assists
    "cutter": {"assists": 2, "goals": 6},   # Cutters get bonus for goals
    "hybrid": {"assists": 4, "goals": 4}   # Hybrid gets balanced points
}

PIN_LENGTH = 4
MAX_PLAYER_TRANSFERS = 4
MAX_CAPTAIN_CHANGES = 2
# tables names from DB
TABLE_PLAYERS = "players"
TABLE_SCORES  = "player_scores"
TABLE_MANAGERS = "managers"
TABLE_ROSTERS  = "rosters"

# Pricing
MEAN = 11
STD_DEV = 6

# --- TIMEZONE & CALCULATIONS ---
SAST = pytz.timezone('Africa/Johannesburg')

def get_now():
    return datetime.now(SAST)

# --- TOURNAMENT MILESTONES ---
RANKING_END_DT = datetime(2026, 4, 18, 18, 0, tzinfo=SAST)
DRAFT_END_DT   = datetime(2026, 4, 25, 8, 0, tzinfo=SAST)
TOURNAMENT_START_DT = datetime(2026, 4, 25, 8, 0, tzinfo=SAST) # Morning of Day 1

# --- 3. STAGE AUTOMATION ---
# Set to "RATINGS", "DRAFT", "LIVE" to override, or None for Auto-mode
MANUAL_STAGE = None

def get_current_stage():
    if MANUAL_STAGE:
        return MANUAL_STAGE
    
    now = get_now()
    if now < RANKING_END_DT:
        return "RATINGS"
    elif now < DRAFT_END_DT:
        return "DRAFT"
    else:
        return "LIVE"

def get_current_day():
    """Calculates tournament day (1, 2, 3...) based on start date."""
    now = get_now()
    if now < TOURNAMENT_START_DT:
        return 0 # Tournament hasn't started
    
    delta = now - TOURNAMENT_START_DT
    # Adding 1 because Day 1 starts at hour 0 of the tournament
    return delta.days + 1

def get_current_stage():
    if MANUAL_STAGE: return MANUAL_STAGE
    now = datetime.now(pytz.timezone('Africa/Johannesburg'))
    if now < RANKING_END_DT: return "RATINGS"
    elif now < TOURNAMENT_START_DT: return "DRAFT"
    else: return "LIVE"