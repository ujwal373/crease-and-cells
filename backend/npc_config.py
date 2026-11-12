"""NPC ID to role/family/session configuration.

Keys are the NPC IDs sent by the frontend (from cc-world.js). Values are dicts
describing how the backend should handle an encounter with that NPC.

Roles:
  friend      - asks a formula question from their family
  practice    - same as friend, first question each day pays double coins
  store       - returns item catalogue
  staff       - returns a rotating tip (chat encounter)
  lesson      - offers lesson topic choices then teaches steps
  checkpoint  - asks a checkpoint question for a tier
  recruit     - shows club lobby for an enrolment session
  match       - shows club lobby for a repeat match session
"""
from __future__ import annotations

NPC_CONFIG: dict[str, dict] = {
    # Coaches — one per family
    "coach0": {"role": "friend",      "family": "maths",  "name": "Coach Rao"},
    "coach1": {"role": "friend",      "family": "text",   "name": "Coach Singh"},
    "coach2": {"role": "friend",      "family": "logic",  "name": "Coach Mehta"},
    "coach3": {"role": "friend",      "family": "date",   "name": "Coach Joshi"},
    "coach4": {"role": "friend",      "family": "lookup", "name": "Coach Pillai"},
    "coach5": {"role": "friend",      "family": "stats",  "name": "Coach Das"},
    "coach6": {"role": "friend",      "family": "arrays", "name": "Coach Bose"},

    # Friends (ask questions from various families)
    "parth":  {"role": "friend",      "family": "maths",  "name": "Parth"},
    "sahil":  {"role": "friend",      "family": "logic",  "name": "Sahil"},
    "nikhil": {"role": "friend",      "family": "stats",  "name": "Nikhil"},
    "rahul":  {"role": "friend",      "family": "text",   "name": "Rahul"},
    "nawaz":  {"role": "friend",      "family": "lookup", "name": "Nawaz"},
    "jinal":  {"role": "friend",      "family": "arrays", "name": "Jinal"},
    "mo":     {"role": "friend",      "family": "date",   "name": "Mo"},

    # Stores
    "akshita": {"role": "store",                          "name": "Akshita"},
    "kit":     {"role": "store",                          "name": "Kit Room"},

    # Staff (tips only)
    "tea":     {"role": "staff",                          "name": "Tea Stall"},

    # Practice (same as friend but daily bonus)
    "pav":     {"role": "practice",   "family": "maths",  "name": "Pav"},

    # Lesson mentors — lesson key maps to LESSON_TOPICS in game_config
    "sana":    {"role": "lesson",     "lesson": "bowling", "tier": 1, "name": "Sana"},
    "fBat":    {"role": "lesson",     "lesson": "batting", "tier": 1, "name": "Farhan"},
    "fFld":    {"role": "lesson",     "lesson": "fielding","tier": 2, "name": "Fiona"},

    # Recruiters — enrolment sessions (one per club tier 1-7)
    "rec1":    {"role": "recruit",    "tier": 1, "session": "univ_exam",    "name": "Dean Joshi"},
    "rec2":    {"role": "recruit",    "tier": 2, "session": "shield",       "name": "Coach Waugh"},
    "rec3":    {"role": "recruit",    "tier": 3, "session": "intra_final",  "name": "Selector Nair"},
    "rec4":    {"role": "recruit",    "tier": 4, "session": "inter",        "name": "Manager Das"},
    "rec5":    {"role": "recruit",    "tier": 5, "session": "state_exam",   "name": "Selector Bose"},
    "rec6":    {"role": "recruit",    "tier": 6, "session": "league_exam",  "name": "Agent Kapoor"},
    "rec7":    {"role": "recruit",    "tier": 7, "session": "national_exam","name": "Chief Selector"},

    # Match officials — repeat matches (after enrolment)
    "w0":      {"role": "match",      "tier": 2, "session": "shield",       "name": "Umpire Kapoor"},
    "w1":      {"role": "match",      "tier": 4, "session": "inter",        "name": "Umpire Rao"},
    "w2":      {"role": "match",      "tier": 6, "session": "leagueA",      "name": "Umpire Singh"},
    "w3":      {"role": "match",      "tier": 6, "session": "leagueB",      "name": "Umpire Mehta"},
    "w4":      {"role": "match",      "tier": 7, "session": "national",     "name": "Umpire Khan"},

    # Checkpoints (tier, step)
    "w5":      {"role": "checkpoint", "tier": 3, "step": 1,                 "name": "Captain Patel"},
    "cp32":    {"role": "checkpoint", "tier": 3, "step": 2,                 "name": "Captain Sharma"},
    "cp71":    {"role": "checkpoint", "tier": 7, "step": 1,                 "name": "National Coach"},
    "cp72":    {"role": "checkpoint", "tier": 7, "step": 2,                 "name": "National Selector"},
    "cp73":    {"role": "checkpoint", "tier": 7, "step": 3,                 "name": "Board Director"},
}
