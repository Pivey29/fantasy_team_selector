# basic settings

import pytz
from datetime import datetime, timedelta

# --- GAME RULES & LABELS ---
TOURNAMENT_NAME = "OW Nationals 2026 - Fantasy Draft"
DIV_OPEN_LABEL = "opens"
DIV_WOMEN_LABEL = "womens"
SCHEMA = "prd"
# RANKING_DATA = "data/test.csv"
RESULTS_TEAMS_TAB = "Sheet1"
RESULTS_SCORES_TAB = "Scores v2"
ROSTER_SIZE = 9
BUDGET_LIMIT = 100
MAX_GENDER_SIZE = 5
MIN_GENDER_SIZE = 4
MAX_TEAM_SIZE = 2
CAPTAIN_MULTIPLIER = 2
PIN_LENGTH = 4
MAX_PLAYER_TRANSFERS = 2
MAX_CAPTAIN_CHANGES = 2
# tables names from DB
TABLE_PLAYERS = "players"
TABLE_SCORES  = "player_scores"
TABLE_MANAGERS = "managers"
TABLE_ROSTERS  = "rosters"

# Pricing
MEAN = 12
STD_DEV = 7

# --- TIMEZONE & CALCULATIONS ---
SAST = pytz.timezone('Africa/Johannesburg')

def get_now():
    return datetime.now(SAST)

# --- TOURNAMENT MILESTONES ---
RANKING_END_DT = datetime(2026, 4, 10, 18, 0, tzinfo=SAST)
DRAFT_END_DT   = datetime(2026, 4, 12, 20, 0, tzinfo=SAST)
TOURNAMENT_START_DT = datetime(2026, 4, 13, 8, 0, tzinfo=SAST) # Morning of Day 1

# --- 3. STAGE AUTOMATION ---
# Set to "RATINGS", "DRAFT", "LIVE" to override, or None for Auto-mode
MANUAL_STAGE = "RATINGS" 

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