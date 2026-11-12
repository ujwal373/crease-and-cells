"""NPC configuration — maps every NPC ID from cc-world.js to its role, family,
session, and tier so encounter_service can dispatch correctly.

Roles mirror cc-engine.js MockAdapter:
  friend      — question encounter (fixed or adaptive family)
  store       — store encounter
  staff/work  — chat encounter with a rotating tip
  practice    — question encounter with daily double-coin bonus
  lesson/quest— lesson topic picker (requires tier)
  recruit     — lobby encounter to enrol in a session
  match       — lobby encounter for a timed match session
  checkpoint  — gated passage encounter
"""
from __future__ import annotations

NPC_CONFIG: dict[str, dict] = {
    # ------------------------------------------------------------------ #
    # Coaches — fixed family, one per skill family
    # ------------------------------------------------------------------ #
    "mukesh": {"role": "friend", "family": "maths",  "name": "Coach Mukesh"},
    "viral":  {"role": "friend", "family": "text",   "name": "Coach Viral"},
    "asst2":  {"role": "friend", "family": "logic",  "name": "Assistant Coach"},
    "asst3":  {"role": "friend", "family": "date",   "name": "Assistant Coach"},
    "asst4":  {"role": "friend", "family": "lookup", "name": "Assistant Coach"},
    "asst5":  {"role": "friend", "family": "stats",  "name": "Assistant Coach"},
    "asst6":  {"role": "friend", "family": "arrays", "name": "Assistant Coach"},

    # ------------------------------------------------------------------ #
    # Store
    # ------------------------------------------------------------------ #
    "akshita": {"role": "store", "name": "Akshita"},

    # ------------------------------------------------------------------ #
    # Friends — give question encounters, family adapts to player skill
    # ------------------------------------------------------------------ #
    "parth":  {"role": "friend", "family": "maths",  "name": "Parth"},
    "sahil":  {"role": "friend", "family": "logic",  "name": "Sahil"},
    "nikhil": {"role": "friend", "family": "maths",  "name": "Nikhil"},
    "rahul":  {"role": "friend", "family": "logic",  "name": "Rahul"},
    "nawaz":  {"role": "friend", "family": "maths",  "name": "Nawaz"},
    "jinal":  {"role": "friend", "family": "text",   "name": "Jinal"},
    "mo":     {"role": "friend", "family": "logic",  "name": "Mo"},

    # National squad friends (tier 7 required)
    "p1": {"role": "friend", "family": "arrays", "tier": 7, "name": "Squad member"},
    "p2": {"role": "friend", "family": "stats",  "tier": 7, "name": "Squad member"},
    "p3": {"role": "friend", "family": "lookup", "tier": 7, "name": "Squad member"},
    "p4": {"role": "friend", "family": "maths",  "tier": 7, "name": "Squad member"},
    "p5": {"role": "friend", "family": "logic",  "tier": 7, "name": "Squad member"},
    "p6": {"role": "friend", "family": "text",   "tier": 7, "name": "Squad member"},
    "p7": {"role": "friend", "family": "date",   "tier": 7, "name": "Squad member"},
    "p8": {"role": "friend", "family": "arrays", "tier": 7, "name": "Squad member"},

    # ------------------------------------------------------------------ #
    # Staff / workers — chat / tips only
    # ------------------------------------------------------------------ #
    "maya":       {"role": "staff", "name": "Maya"},
    "bholu":      {"role": "staff", "name": "Bholu"},
    "nandini":    {"role": "staff", "name": "Nandini"},
    "gill":       {"role": "staff", "name": "Gill"},
    "curator":    {"role": "staff", "name": "Curator"},
    "groundsman": {"role": "staff", "name": "Groundsman"},
    "fIcon":      {"role": "staff", "name": "Franchise Icon"},
    "fMgr":       {"role": "staff", "name": "Franchise Manager"},
    "fData":      {"role": "staff", "name": "Data Analyst"},
    "fMed":       {"role": "staff", "name": "Medical Staff"},
    "fSC":        {"role": "staff", "name": "Strength Coach"},
    "fPhys":      {"role": "staff", "name": "Physio"},

    # ------------------------------------------------------------------ #
    # Practice — question encounter, daily double-coin bonus
    # ------------------------------------------------------------------ #
    "practice": {"role": "practice", "family": "maths", "tier": 1, "name": "Practice Nets"},

    # ------------------------------------------------------------------ #
    # Lesson / quest — topic picker, requires tier
    # ------------------------------------------------------------------ #
    "sana":   {"role": "lesson", "lesson": "bowling",  "tier": 1, "name": "Sana"},
    "fDev":   {"role": "lesson", "lesson": "bowling",  "tier": 6, "name": "Developer Coach"},
    "fBat":   {"role": "lesson", "lesson": "batting",  "tier": 6, "name": "Batting Coach"},
    "fBowl":  {"role": "lesson", "lesson": "bowling",  "tier": 6, "name": "Bowling Coach"},
    "fField": {"role": "lesson", "lesson": "fielding", "tier": 6, "name": "Fielding Coach"},
    "nBat":   {"role": "lesson", "lesson": "batting",  "tier": 7, "name": "Academy Batting Coach"},
    "nBowl":  {"role": "lesson", "lesson": "bowling",  "tier": 7, "name": "Academy Bowling Coach"},
    "nField": {"role": "lesson", "lesson": "fielding", "tier": 7, "name": "Academy Fielding Coach"},

    # ------------------------------------------------------------------ #
    # Recruit — enrol in a session (exam or trial)
    # ------------------------------------------------------------------ #
    "dean":  {"role": "recruit", "tier": 1, "session": "univ_exam",    "name": "Dean Joshi"},
    "arjun": {"role": "recruit", "tier": 3, "session": "intra_final",  "name": "Selector Arjun"},
    "lad":   {"role": "recruit", "tier": 5, "session": "state_exam",   "name": "Selector Lad"},
    "fDir":  {"role": "recruit", "tier": 6, "session": "league_exam",  "name": "Franchise Director"},
    "nCap":  {"role": "recruit", "tier": 7, "session": "national_exam","name": "National Captain"},

    # ------------------------------------------------------------------ #
    # Match — timed multi-round match session
    # ------------------------------------------------------------------ #
    "shieldSel": {"role": "match", "tier": 2, "session": "shield",   "name": "Shield Selector"},
    "mishra":    {"role": "match", "tier": 4, "session": "inter",    "name": "Manager Mishra"},
    "fHead":     {"role": "match", "tier": 6, "session": "leagueA",  "name": "Head Coach"},
    "fPerf":     {"role": "match", "tier": 6, "session": "leagueB",  "name": "Performance Coach"},
    "nCoach":    {"role": "match", "tier": 7, "session": "national", "name": "National Coach"},

    # ------------------------------------------------------------------ #
    # Checkpoint — gated passage, requires steps cleared
    # ------------------------------------------------------------------ #
    "steward":   {"role": "checkpoint", "tier": 3, "step": 1, "name": "Steward"},
    "secretary": {"role": "checkpoint", "tier": 3, "step": 2, "name": "Secretary"},
    "nFit":      {"role": "checkpoint", "tier": 7, "step": 1, "name": "Fitness Tester"},
    "nSel":      {"role": "checkpoint", "tier": 7, "step": 2, "name": "National Selector"},
    "nMgr":      {"role": "checkpoint", "tier": 7, "step": 3, "name": "National Manager"},
}
