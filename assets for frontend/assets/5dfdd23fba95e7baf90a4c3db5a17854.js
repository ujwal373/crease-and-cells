/* Crease and Cells: every label the player can read, in one place.
   Friends, family and local coaches use real first names chosen by the owner.
   League, board, franchise and player names are neutral placeholders on purpose:
   the first brief ruled out real players, teams and brands. Replace them here if you hold the rights.
   CC0 dedication, written for this project. */
(function (root) {
  'use strict';
  root.CCNames = {
    /* division and venue labels, tier 1 to 7 */
    clubs: [
      { id: 'univ', division: 'University of Mumbai', venue: 'University of Mumbai' },
      { id: 'shield', division: 'Shield Cup', venue: 'University Ground' },
      { id: 'intra', division: 'Suburban Association', venue: 'Borivali District Club' },
      { id: 'inter', division: 'Inter Divisions', venue: 'Borivali District Club ground' },
      { id: 'state', division: 'State Trophy', venue: 'State Cricket Ground' },
      { id: 'league', division: 'Harbour Blues', venue: 'Harbour Blues Town' },
      { id: 'national', division: 'National XI', venue: 'National Stadium' }
    ],
    /* people: id -> [display name, short role] */
    people: {
      mukesh: ['Mukesh', 'Head coach, maths lane'],
      viral: ['Viral', 'Head coach, text lane'],
      asst2: ['Coach Imran', 'Logic lane'], asst3: ['Coach Leela', 'Dates lane'], asst4: ['Coach Mohan', 'Lookup lane'], asst5: ['Coach Sarita', 'Stats lane'], asst6: ['Coach Dhruv', 'Arrays lane'],
      parth: ['Parth', 'Your brother'],
      akshita: ['Akshita', 'Store assistant'],
      maya: ['Maya', 'Store owner'],
      bholu: ['Bholu', 'Tea stall'], nandini: ['Nandini', 'Kit repair'], gill: ['Mr Gill', 'Pavilion'], sana: ['Selector Sana', 'Notice board'],
      /* University */
      dean: ['Prof. Desai', 'Admissions'],
      sahil: ['Sahil', 'Friend'], nikhil: ['Nikhil', 'Friend'], rahul: ['Rahul', 'Friend'], nawaz: ['Nawaz', 'Friend'], jinal: ['Jinal', 'Friend'], mo: ['Mo', 'Friend'],
      practice: ['Practice captain', 'Daily practice'],
      /* Shield Cup */
      shieldSel: ['Selector Kamat', 'Shield Cup match'],
      /* Borivali District Club */
      steward: ['Gate steward', 'Checkpoint 1'], secretary: ['Club secretary', 'Checkpoint 2'], arjun: ['Arjun', 'Coach, checkpoint 3'], mishra: ['Mishra', 'Inter Divisions coach'],
      /* State ground */
      lad: ['Lad sir', 'State Trophy coach'], curator: ['Curator Bhide', 'Trophy room'], groundsman: ['Groundsman Pillai', 'Pitch'],
      /* Franchise town (placeholders for the real staff list) */
      fIcon: ['Dev Malhotra', 'Icon'], fHead: ['Tom Fairley', 'Head coach'], fPerf: ['Neel Sathe', 'Director of performance'],
      fBat: ['Rohan Sen', 'Batting coach'], fBowl: ['Nick Harlow', 'Bowling coach'], fDev: ['Kunal Apte', 'Development bowling coach'], fField: ['Dilip Nair', 'Fielding coach'],
      fDir: ['Anand Saxena', 'Director of cricket'], fData: ['Meera Iyer', 'Chief officer, data and innovation'], fMed: ['Ben Carver', 'Head of sports science and medicine'],
      fSC: ['Paul Dsouza', 'Strength and conditioning'], fPhys: ['Craig Naidu', 'Physiotherapist'], fMgr: ['Prakash Jadhav', 'Team manager'],
      /* National XI (placeholders) */
      nCoach: ['Head Coach Hegde', 'National head coach'], nCap: ['Captain Rane', 'National captain'],
      p1: ['Kabir Joshi', 'Player'], p2: ['Hari Menon', 'Player'], p3: ['Laksh Rathi', 'Player'], p4: ['Bilal Shah', 'Player'],
      p5: ['Jai Tandon', 'Player'], p6: ['Anwar Sheikh', 'Player'], p7: ['Sid Gowda', 'Player'], p8: ['Bhaskar Nene', 'Player'],
      nBat: ['Vikram Pawar', 'Batting mentor'], nBowl: ['Sameer Khatri', 'Bowling mentor'], nField: ['Rajan Thorat', 'Fielding mentor'],
      nFit: ['Fitness assessor', 'Checkpoint 1'], nSel: ['Selection chair', 'Checkpoint 2'], nMgr: ['Team manager', 'Checkpoint 3']
    }
  };
  if (typeof module !== 'undefined') module.exports = root.CCNames;
})(typeof window !== 'undefined' ? window : globalThis);
