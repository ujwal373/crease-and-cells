/* Crease and Cells: engine for the FRONTEND.
   window.CCApi is the only thing the world talks to. It has two adapters:
     MockAdapter  plays the server and the AI agents so the prototype works alone.
     HttpAdapter  skeleton that calls your real backend. Swap with CCApi.use('http', {baseUrl}).
   Nothing in the world decides rewards, questions or eligibility. It only shows what the adapter returns.
   CC0 dedication, written for this project. */
(function (root) {
  'use strict';
  var F = root.CCFormula;

  /* ---------- shared config the server also owns (the world reads it from GET /api/world) ---------- */
  var LEVEL_XP = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200];
  var SKILL_XP = [0, 60, 180, 360, 600];
  var FAMILIES = [
    { id: 'maths', name: 'Maths', blurb: 'SUM, AVERAGE, MIN, MAX, ROUND' },
    { id: 'text', name: 'Text', blurb: 'LEFT, RIGHT, MID, UPPER, TRIM, CONCAT' },
    { id: 'logic', name: 'Logic', blurb: 'IF, AND, OR, COUNTIF, SUMIF' },
    { id: 'date', name: 'Dates', blurb: 'DATE, YEAR, MONTH, DAYS' },
    { id: 'lookup', name: 'Lookup', blurb: 'VLOOKUP, INDEX, MATCH, XLOOKUP' },
    { id: 'stats', name: 'Stats', blurb: 'MEDIAN, LARGE, SMALL, RANK' },
    { id: 'arrays', name: 'Arrays', blurb: 'SUMPRODUCT, COUNTUNIQUE, TEXTJOIN' }
  ];
  var ITEMS = [
    { id: 'c_white', slot: 'cap', name: 'Basic White Cap', price: 0, hex: '#F4F1E8' },
    { id: 'c_sun', slot: 'cap', name: 'Sunrise Cap', price: 70, hex: '#F2B632' },
    { id: 'c_hat', slot: 'cap', name: 'Wide Sunhat', price: 90, hex: '#E9D8A6' },
    { id: 'c_helm', slot: 'cap', name: 'Training Helmet', price: 180, hex: '#2C3E6B' },
    { id: 'j_white', slot: 'jersey', name: 'Basic White Jersey', price: 0, hex: '#F4F1E8' },
    { id: 'j_sunrise', slot: 'jersey', name: 'Sunrise Gold Jersey', price: 100, hex: '#F2B632' },
    { id: 'j_teal', slot: 'jersey', name: 'Club Teal Stripe', price: 120, hex: '#1F7A7A' },
    { id: 'j_terra', slot: 'jersey', name: 'Terracotta Stripe', price: 140, hex: '#D9805F' },
    { id: 's_white', slot: 'shoes', name: 'Basic White Shoes', price: 0, hex: '#F4F1E8' },
    { id: 's_gold', slot: 'shoes', name: 'Sunrise Gold Shoes', price: 80, hex: '#F2B632' },
    { id: 's_teal', slot: 'shoes', name: 'Club Teal Shoes', price: 90, hex: '#1F7A7A' },
    { id: 's_night', slot: 'shoes', name: 'Night Spikes', price: 130, hex: '#26262B' },
    { id: 'a_white', slot: 'sleeve', name: 'Basic White Sleeve', price: 0, hex: '#F4F1E8' },
    { id: 'a_teal', slot: 'sleeve', name: 'Club Teal Sleeve', price: 50, hex: '#1F7A7A' },
    { id: 'a_gold', slot: 'sleeve', name: 'Sunrise Gold Sleeve', price: 50, hex: '#F2B632' },
    { id: 'a_terra', slot: 'sleeve', name: 'Terracotta Sleeve', price: 60, hex: '#D9805F' }
  ];
  /* Division and venue labels come from cc-names.js. Mode says how a player gets in. */
  var NM = (root.CCNames && root.CCNames.clubs) || [];
  function nmc(i, k, d) { return NM[i] && NM[i][k] ? NM[i][k] : d; }
  var CLUBS = [
    { tier: 1, id: 'univ', mode: 'exam', name: nmc(0, 'division', 'University'), venue: nmc(0, 'venue', 'University'), level: 2, skills: { maths: 1 }, gear: [] },
    { tier: 2, id: 'shield', mode: 'match', name: nmc(1, 'division', 'Shield Cup'), venue: nmc(1, 'venue', 'University Ground'), level: 3, skills: { maths: 2, logic: 1 }, gear: [{ any: 'jersey' }] },
    { tier: 3, id: 'intra', mode: 'checkpoints', name: nmc(2, 'division', 'Intra State'), venue: nmc(2, 'venue', 'District Club'), level: 4, skills: { logic: 2, text: 1 }, gear: [{ any: 'jersey' }, { any: 'cap' }] },
    { tier: 4, id: 'inter', mode: 'match', name: nmc(3, 'division', 'Inter Divisions'), venue: nmc(3, 'venue', 'District Club ground'), level: 5, skills: { lookup: 1, date: 1 }, gear: [{ any: 'jersey' }, { any: 'shoes' }] },
    { tier: 5, id: 'state', mode: 'exam', name: nmc(4, 'division', 'State Trophy'), venue: nmc(4, 'venue', 'State Ground'), level: 6, skills: { lookup: 2, stats: 1 }, gear: [{ any: 'jersey' }, { any: 'cap' }, { any: 'shoes' }] },
    { tier: 6, id: 'league', mode: 'exam', name: nmc(5, 'division', 'Franchise League'), venue: nmc(5, 'venue', 'Franchise Town'), level: 7, skills: { stats: 2, arrays: 1 }, gear: [{ any: 'jersey' }, { any: 'cap' }, { any: 'shoes' }, { any: 'sleeve' }] },
    { tier: 7, id: 'national', mode: 'checkpoints', name: nmc(6, 'division', 'National XI'), venue: nmc(6, 'venue', 'National Stadium'), level: 8, skills: { maths: 2, text: 2, logic: 2, date: 2, lookup: 2, stats: 2, arrays: 2 }, gear: [{ worn: 'c_helm' }, { worn: 'j_terra' }, { worn: 's_night' }, { any: 'sleeve' }] }
  ];

  /* ---------- seeded random ---------- */
  function rng(seed) { var a = seed >>> 0; return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function mk(seed) { var r = rng(seed); return { f: r, i: function (a, b) { return a + Math.floor(r() * (b - a + 1)); }, pick: function (l) { return l[Math.floor(r() * l.length)]; }, shuffle: function (l) { var o = l.slice(); for (var k = o.length - 1; k > 0; k--) { var j = Math.floor(r() * (k + 1)); var t = o[k]; o[k] = o[j]; o[j] = t; } return o; } }; }
  var NAMES = ['Arun', 'Bela', 'Chirag', 'Dev', 'Esha', 'Farid', 'Gita', 'Hari', 'Isha', 'Jai', 'Kavya', 'Lakhan', 'Mira', 'Nikhil', 'Omar', 'Pia', 'Qasim', 'Rhea', 'Sunil', 'Tara', 'Uday', 'Vani', 'Wasim', 'Yash', 'Zoya'];
  var CITIES = ['Harbour Blues', 'Lakeside Lions', 'Hillcrest Hawks', 'Riverbend Royals', 'Palmgrove Panthers', 'Stonebridge Strikers'];
  var VENUES = ['Harbour Oval', 'Lakeside Park', 'Hillcrest Ground', 'Riverbend Maidan', 'Palmgrove Arena', 'Stonebridge Green'];
  var SURN = ['Rao', 'Khan', 'Nair', 'Sen', 'Bose', 'Iyer', 'Das'];
  var BOWLERS = ['Pace', 'Spin', 'Swing', 'Seam'];
  var ROLES = ['Opener', 'Batter', 'All-rounder', 'Bowler', 'Keeper'];
  /* extra cricket columns so every sheet reads like a real scorebook */
  function decorate(q, R) {
    var h = q.rows[0] ? q.rows[0].join('|') : '', k;
    if (h === 'Match|Runs') { q.rows[0].push('Opponent', 'Venue'); for (k = 1; k < q.rows.length; k++) if (/^M\d+$/.test(String(q.rows[k][0]))) q.rows[k].push(R.pick(CITIES), R.pick(VENUES)); }
    else if (h === 'Over|Runs') { q.rows[0].push('Bowler type'); for (k = 1; k < q.rows.length; k++) if (typeof q.rows[k][0] === 'number') q.rows[k].push(R.pick(BOWLERS)); }
    else if (h === 'Spell|Overs') { q.rows[0].push('Bowler type'); for (k = 1; k < q.rows.length; k++) if (/^S\d+$/.test(String(q.rows[k][0]))) q.rows[k].push(R.pick(BOWLERS)); }
    else if (h === 'Player|Runs' || h === 'Player|Wickets') { q.rows[0].push('Team', 'Role'); for (k = 1; k < q.rows.length; k++) if (q.rows[k][0] !== 'Find' && q.rows[k][0] !== 'Runs' && q.rows[k][0] !== 'Wickets') q.rows[k].push(R.pick(CITIES), R.pick(ROLES)); }
    else if (h === 'Code|City') { q.rows[0][0] = 'Player ID'; q.rows[0][1] = 'Team'; }
    return q;
  }
  var colL = ['A', 'B', 'C', 'D', 'E', 'F'];
  function ref(r, c) { return colL[c] + (r + 1); }
  function rangeRef(c, r1, r2) { return colL[c] + (r1 + 1) + ':' + colL[c] + (r2 + 1); }

  /* ---------- question templates (the stand-in for your AI agents) ---------- */
  /* each returns { rows, tr, tc, mustUse, hint, explain, task, story } and the engine fills expected by evaluating the model answer */
  var T = {};
  T.maths = [
    function (R, d) { var n = R.i(5, 7), rows = [['Over', 'Runs']]; for (var k = 0; k < n; k++) rows.push([k + 1, R.i(2, 14)]); rows.push(['Total', '']); var tr = rows.length - 1; return { rows: rows, tr: tr, tc: 1, model: '=SUM(' + rangeRef(1, 1, tr - 1) + ')', mustUse: ['SUM'], story: 'The scorer lost the calculator again.', task: 'Add up every over in ' + rangeRef(1, 1, tr - 1) + ' and put the total in ' + ref(tr, 1) + '.', hint: 'SUM adds a range. Write =SUM(first:last).', explain: 'SUM adds all the numbers in a range.' }; },
    function (R, d) { var n = R.i(5, 7), rows = [['Spell', 'Overs']]; for (var k = 0; k < n; k++) rows.push(['S' + (k + 1), R.i(2, 6)]); rows.push(['Average', '']); var tr = rows.length - 1; return { rows: rows, tr: tr, tc: 1, model: '=ROUND(AVERAGE(' + rangeRef(1, 1, tr - 1) + '),2)', mustUse: ['AVERAGE'], story: 'A bowler wants the typical length of a spell.', task: 'Find the average overs in ' + rangeRef(1, 1, tr - 1) + ', rounded to 2 decimals, in ' + ref(tr, 1) + '.', hint: 'Wrap AVERAGE inside ROUND: =ROUND(AVERAGE(range),2).', explain: 'AVERAGE gives the mean. ROUND trims it to 2 decimals.' }; },
    function (R, d) { var n = R.i(5, 6), rows = [['Match', 'Runs']]; for (var k = 0; k < n; k++) rows.push(['M' + (k + 1), R.i(8, 90)]); rows.push(['Best', ''], ['Worst', '']); var tr = rows.length - 2; return { rows: rows, tr: tr, tc: 1, model: '=MAX(' + rangeRef(1, 1, tr - 1) + ')-MIN(' + rangeRef(1, 1, tr - 1) + ')', mustUse: ['MAX', 'MIN'], story: 'The selector wants the spread between a best and a worst score.', task: 'In ' + ref(tr, 1) + ' show the best score minus the worst score from ' + rangeRef(1, 1, tr - 1) + '.', hint: 'MAX(range) minus MIN(range).', explain: 'MAX finds the biggest, MIN the smallest. Subtract them for the spread.' }; }
  ];
  T.text = [
    function (R, d) { var rows = [['Player', 'Code']]; for (var k = 0; k < 5; k++) rows.push([R.pick(NAMES) + ' ' + R.pick(['Rao', 'Khan', 'Nair', 'Sen', 'Bose', 'Iyer', 'Das']), '']); var tr = 1; return { rows: rows, tr: tr, tc: 1, model: '=UPPER(LEFT(A2,3))', mustUse: ['LEFT'], story: 'The kit room labels bags with a short code.', task: 'In B2 make the first 3 letters of A2, in capitals.', hint: 'LEFT takes letters from the start. UPPER makes capitals. Nest them.', explain: 'LEFT(text,3) takes 3 letters. UPPER capitalises.' }; },
    function (R, d) { var f = R.pick(NAMES), l = R.pick(['Rao', 'Khan', 'Nair', 'Sen', 'Bose']); var rows = [['First', 'Last', 'Full'], [f, l, '']]; return { rows: rows, tr: 1, tc: 2, model: '=A2&" "&B2', mustUse: [], story: 'The team sheet needs full names.', task: 'In C2 join A2 and B2 with a single space between them.', hint: 'Use & to join text. Put " " between the two cells.', explain: 'The & operator joins text. A space is just text in quotes.' }; },
    function (R, d) { var id = R.pick(['HBR', 'LKS', 'HLC']) + '-' + R.i(100, 999); var rows = [['Ticket'], ['  ' + id + '  '], [''], ['Clean ID', '']]; rows = [['Match pass', 'Clean'], ['  ' + id.toLowerCase() + '  ', '']]; return { rows: rows, tr: 1, tc: 1, model: '=UPPER(TRIM(A2))', mustUse: ['TRIM'], story: 'Match pass codes arrive with stray spaces and small letters.', task: 'In B2 remove the extra spaces from A2 and make it all capitals.', hint: 'TRIM removes spaces. UPPER capitalises.', explain: 'TRIM cleans spaces, UPPER fixes the case.' }; }
  ];
  T.logic = [
    function (R, d) { var runs = R.i(20, 80); var rows = [['Runs', 'Result'], [runs, '']]; return { rows: rows, tr: 1, tc: 1, model: '=IF(A2>=50,"Fifty","Keep going")', mustUse: ['IF'], story: 'The scoreboard shows a badge for fifties.', task: 'In B2 show "Fifty" if A2 is 50 or more, otherwise "Keep going".', hint: 'IF(test, if true, if false). Text goes in quotes.', explain: 'IF picks one of two answers by testing a condition.' }; },
    function (R, d) { var n = R.i(6, 8), rows = [['Match', 'Runs']], th = R.pick([30, 40, 50]); for (var k = 0; k < n; k++) rows.push(['M' + (k + 1), R.i(5, 95)]); rows.push(['Count', '']); var tr = rows.length - 1; return { rows: rows, tr: tr, tc: 1, model: '=COUNTIF(' + rangeRef(1, 1, tr - 1) + ',">=' + th + '")', mustUse: ['COUNTIF'], story: 'The club book tracks good scores.', task: 'Count scores of ' + th + ' or more in ' + rangeRef(1, 1, tr - 1) + '. Answer in ' + ref(tr, 1) + '.', hint: 'COUNTIF(range, ">=' + th + '"). The condition is in quotes.', explain: 'COUNTIF counts the cells that meet one condition.' }; },
    function (R, d) { var n = R.i(6, 8), rows = [['Team', 'Runs']], pick = R.pick(['Harbour Blues', 'Lakeside Lions']); for (var k = 0; k < n; k++) rows.push([k % 2 ? 'Lakeside Lions' : 'Harbour Blues', R.i(10, 60)]); rows.push([pick + ' total', '']); var tr = rows.length - 1; return { rows: rows, tr: tr, tc: 1, model: '=SUMIF(A2:A' + tr + ',"' + pick + '",B2:B' + tr + ')', mustUse: ['SUMIF'], story: 'Two clubs share one score sheet.', task: 'Add only the ' + pick + ' rows from column B. Answer in ' + ref(tr, 1) + '.', hint: 'SUMIF(test range, "' + pick + '", sum range).', explain: 'SUMIF adds only the rows that match a test.' }; },
    function (R, d) { var a = R.i(10, 60), b = R.i(10, 60); var rows = [['Runs', 'Wkts', 'Bonus?'], [a, b % 8, '']]; return { rows: rows, tr: 1, tc: 2, model: '=IF(AND(A2>=30,B2<=4),"Yes","No")', mustUse: ['IF', 'AND'], story: 'A bonus needs two things at once.', task: 'In C2 show "Yes" if A2 is at least 30 AND B2 is 4 or fewer, otherwise "No".', hint: 'IF(AND(test1,test2),"Yes","No").', explain: 'AND is true only if every test is true.' }; }
  ];
  T.date = [
    function (R, d) { var y = 2026, m = R.i(1, 12), dd = R.i(1, 28), s = y + '-' + (m < 10 ? '0' : '') + m + '-' + (dd < 10 ? '0' : '') + dd; var rows = [['Match date', 'Month'], [s, '']]; return { rows: rows, tr: 1, tc: 1, model: '=MONTH(A2)', mustUse: ['MONTH'], story: 'The fixture list needs month numbers.', task: 'In B2 get the month number of the date in A2.', hint: 'MONTH takes a date.', explain: 'MONTH returns 1 to 12 from a date.' }; },
    function (R, d) { var a = R.i(1, 9), b = a + R.i(5, 40); function f(n) { var dt = new Date(Date.UTC(2026, 0, 1) + (n - 1) * 86400000); return dt.toISOString().slice(0, 10); } var rows = [['Camp start', 'Camp end', 'Days'], [f(a), f(b), '']]; return { rows: rows, tr: 1, tc: 2, model: '=DAYS(B2,A2)', mustUse: ['DAYS'], story: 'A training camp has dates but no length.', task: 'In C2 count the days from A2 to B2.', hint: 'DAYS(end, start). End comes first.', explain: 'DAYS subtracts one date from another.' }; },
    function (R, d) { var y = R.i(2, 6) + 2020, m = R.i(1, 12), dd = R.i(1, 28); var rows = [['Year', 'Month', 'Day', 'Date'], [y, m, dd, '']]; return { rows: rows, tr: 1, tc: 3, model: '=DATE(A2,B2,C2)', mustUse: ['DATE'], story: 'The registry stores dates in three columns.', task: 'In D2 build one real date from A2, B2 and C2.', hint: 'DATE(year, month, day).', explain: 'DATE assembles year, month and day into one date.' }; }
  ];
  T.lookup = [
    function (R, d) { var ns = R.shuffle(NAMES).slice(0, 5), rows = [['Player', 'Runs']]; ns.forEach(function (n) { rows.push([n, R.i(10, 90)]); }); var who = R.pick(ns); rows.push(['Find', who]); rows.push(['Runs', '']); return { rows: rows, tr: rows.length - 1, tc: 1, model: '=VLOOKUP(B7,A2:B6,2,FALSE)', mustUse: ['VLOOKUP'], story: 'Someone asks for one player by name.', task: 'In B8 look up the name in B7 inside A2:B6 and return the runs.', hint: 'VLOOKUP(what, table, column number, FALSE).', explain: 'VLOOKUP finds a row by its first column and returns another column.' }; },
    function (R, d) { var ns = R.shuffle(NAMES).slice(0, 5), rows = [['Player', 'Wickets']]; ns.forEach(function (n) { rows.push([n, R.i(1, 12)]); }); var who = R.pick(ns); rows.push(['Find', who]); rows.push(['Wickets', '']); return { rows: rows, tr: rows.length - 1, tc: 1, model: '=INDEX(B2:B6,MATCH(B7,A2:A6,0))', mustUse: ['INDEX', 'MATCH'], story: 'The coach wants a flexible lookup.', task: 'In B8 return the wickets for the name in B7 using INDEX and MATCH.', hint: 'MATCH finds the position. INDEX returns the value at that position.', explain: 'MATCH gives a position, INDEX picks the value there.' }; },
    function (R, d) { var ns = R.shuffle(NAMES).slice(0, 5), rows = [['Code', 'City']]; ns.forEach(function (n, k) { rows.push([n.slice(0, 2).toUpperCase() + k, R.pick(CITIES)]); }); var who = R.i(1, 5); rows.push(['Find', rows[who][0]]); rows.push(['Team', '']); return { rows: rows, tr: rows.length - 1, tc: 1, model: '=XLOOKUP(B7,A2:A6,B2:B6)', mustUse: ['XLOOKUP'], story: 'Every player ID needs a team beside it.', task: 'In B8 find the player ID in B7 and return their team using XLOOKUP.', hint: 'XLOOKUP(what, where to look, what to return).', explain: 'XLOOKUP searches one range and returns from another.' }; }
  ];
  T.stats = [
    function (R, d) { var n = R.i(6, 8), rows = [['Match', 'Runs']]; for (var k = 0; k < n; k++) rows.push(['M' + (k + 1), R.i(5, 95)]); rows.push(['Median', '']); var tr = rows.length - 1; return { rows: rows, tr: tr, tc: 1, model: '=MEDIAN(' + rangeRef(1, 1, tr - 1) + ')', mustUse: ['MEDIAN'], story: 'The analyst distrusts averages.', task: 'Find the middle score of ' + rangeRef(1, 1, tr - 1) + '.', hint: 'MEDIAN(range).', explain: 'MEDIAN is the middle value once sorted.' }; },
    function (R, d) { var n = R.i(6, 8), rows = [['Match', 'Runs']]; for (var k = 0; k < n; k++) rows.push(['M' + (k + 1), R.i(5, 95)]); rows.push(['2nd best', '']); var tr = rows.length - 1; return { rows: rows, tr: tr, tc: 1, model: '=LARGE(' + rangeRef(1, 1, tr - 1) + ',2)', mustUse: ['LARGE'], story: 'The selector needs the runner up.', task: 'Show the second largest score of ' + rangeRef(1, 1, tr - 1) + '.', hint: 'LARGE(range, 2).', explain: 'LARGE(range,k) gives the k-th biggest value.' }; }
  ];
  T.arrays = [
    function (R, d) { var n = R.i(4, 5), rows = [['Item', 'Qty', 'Price']]; for (var k = 0; k < n; k++) rows.push([R.pick(['Ball', 'Bat', 'Pad', 'Glove', 'Stump', 'Cone']) + k, R.i(1, 6), R.i(2, 12) * 10]); rows.push(['Total', '', '']); var tr = rows.length - 1; return { rows: rows, tr: tr, tc: 2, model: '=SUMPRODUCT(B2:B' + tr + ',C2:C' + tr + ')', mustUse: ['SUMPRODUCT'], story: 'The kit order needs a grand total.', task: 'In ' + ref(tr, 2) + ' multiply quantity by price for each row and add them all, in one formula.', hint: 'SUMPRODUCT(range1, range2).', explain: 'SUMPRODUCT multiplies matching cells and adds the results.' }; },
    function (R, d) { var n = R.i(7, 9), rows = [['Venue']]; for (var k = 0; k < n; k++) rows.push([R.pick(VENUES)]); rows.push(['Unique']); var tr = rows.length - 1; rows[tr][1] = ''; return { rows: rows, tr: tr, tc: 1, model: '=COUNTUNIQUE(A2:A' + tr + ')', mustUse: ['COUNTUNIQUE'], story: 'How many different grounds were used?', task: 'Count the different venues in A2:A' + tr + ' and put it in ' + ref(tr, 1) + '. (Google Sheets: COUNTUNIQUE.)', hint: 'COUNTUNIQUE(range).', explain: 'COUNTUNIQUE counts each distinct value once.' }; }
  ];

  function buildQuestion(family, level, seed) {
    var R = mk(seed), list = T[family] || T.maths, tpl = list[Math.floor(R.f() * list.length)];
    var q = decorate(tpl(R, level), R), grid = q.rows.map(function (r) { return r.slice(); });
    var expected = F.evaluate(q.model, grid);
    return { q: q, expected: expected };
  }

  /* ---------- sessions: exams, timed matches, repeat matches ---------- */
  var SESSIONS = {
    univ_exam: { name: 'University entrance exam', rounds: 3, pass: 2, secs: 0, cooldownH: 0, enrol: 1 },
    shield: { name: 'Shield Cup match', rounds: 5, pass: 3, secs: 90, cooldownH: 6, enrol: 2, tier: 2 },
    intra_final: { name: 'District club trial', rounds: 2, pass: 1, secs: 0, cooldownH: 0, enrol: 3 },
    inter: { name: 'Inter Divisions match', rounds: 5, pass: 3, secs: 90, cooldownH: 12, enrol: 4, tier: 4 },
    state_exam: { name: 'State trial', rounds: 4, pass: 3, secs: 0, cooldownH: 0, enrol: 5 },
    league_exam: { name: 'Franchise selection', rounds: 4, pass: 3, secs: 0, cooldownH: 0, enrol: 6 },
    leagueA: { name: 'Match at Ground A', rounds: 5, pass: 3, secs: 75, cooldownH: 0, tier: 6 },
    leagueB: { name: 'Match at Ground B', rounds: 5, pass: 3, secs: 75, cooldownH: 0, tier: 6 },
    national_exam: { name: 'National selection', rounds: 5, pass: 4, secs: 0, cooldownH: 0, enrol: 7 },
    national: { name: 'Stadium match', rounds: 6, pass: 4, secs: 60, cooldownH: 0, tier: 7, big: true }
  };
  var TIER_SESSION = ['univ_exam', 'shield', 'intra_final', 'inter', 'state_exam', 'league_exam', 'national_exam'];
  var CHECKPOINTS = { 3: 2, 7: 3 };
  var FACILITY_TIER = { gym: 6, pool: 6, sauna: 6, machine: 6, gymN: 7, poolN: 7 };
  var LESSON_TOPICS = { batting: ['maths', 'stats', 'logic'], bowling: ['text', 'lookup', 'date'], fielding: ['arrays', 'logic', 'text'] };
  var LESSONS = {
    maths: { title: 'Maths: totals and averages', steps: ['SUM adds a range: =SUM(B2:B7).', 'AVERAGE gives the mean: =AVERAGE(B2:B7).', 'MAX and MIN find the best and worst; ROUND tidies decimals.'], example: '=ROUND(AVERAGE(B2:B7),1)' },
    text: { title: 'Text: cleaning and joining', steps: ['LEFT, RIGHT and MID cut pieces out of text.', 'TRIM removes extra spaces; UPPER and PROPER fix the case.', 'The & sign joins text: =A2&" "&B2.'], example: '=UPPER(TRIM(A2))' },
    logic: { title: 'Logic: decisions and counting', steps: ['IF picks between two answers: =IF(A2>=50,"Fifty","No").', 'AND and OR combine tests inside IF.', 'COUNTIF counts matches and SUMIF adds only matching rows.'], example: '=COUNTIF(B2:B9,">=50")' },
    date: { title: 'Dates: gaps and parts', steps: ['DATE builds a date from year, month, day.', 'YEAR, MONTH and DAY pull the parts back out.', 'DAYS(end,start) counts the gap between two dates.'], example: '=DAYS(B2,A2)' },
    lookup: { title: 'Lookup: finding things', steps: ['VLOOKUP finds a row by its first column.', 'MATCH gives a position; INDEX returns the value at a position.', 'XLOOKUP searches one range and returns from another.'], example: '=INDEX(B2:B6,MATCH(B7,A2:A6,0))' },
    stats: { title: 'Stats: middles and ranks', steps: ['MEDIAN is the middle value once sorted.', 'LARGE(range,2) is the second biggest; SMALL is the opposite.', 'RANK tells you where one value stands in a list.'], example: '=LARGE(B2:B9,2)' },
    arrays: { title: 'Arrays: many cells at once', steps: ['SUMPRODUCT multiplies matching cells and adds them.', 'COUNTUNIQUE counts distinct values.', 'TEXTJOIN joins many cells with a separator.'], example: '=SUMPRODUCT(B2:B6,C2:C6)' }
  };
  var TIPS = ['Press F4 in Excel to lock a cell reference with dollar signs.', 'A range like B2:B7 is read top to bottom, then left to right.', 'If a formula shows #NAME?, check spelling and quote marks.', 'Name your header row clearly. Future you will thank present you.', 'Ctrl+Shift+Down selects a column of data in one go.', 'Check your answer with a quick mental estimate before you trust it.'];
  var FRIEND_SAY = { parth: 'Parth grins. "Remember our gully cricket days? Come on, help me with this sheet."', sahil: 'Sahil waves you over from the lawn. "Quick one before the lecture?"', nikhil: 'Nikhil slides his laptop across. "Settle a bet for us."', rahul: 'Rahul taps his notebook. "The scorebook is a mess again."', nawaz: 'Nawaz laughs. "You are the formula person now. Help."', jinal: 'Jinal looks up from her notes. "I have a puzzle for you."', mo: 'Mo shrugs. "Free coffee if you get this right."' };
  var ROLE_FAMILY = ['maths', 'text', 'logic', 'date', 'lookup', 'stats', 'arrays'];
  var HOUR = 3600000;

  /* ---------- MockAdapter ---------- */
  function MockAdapter(opts) {
    opts = opts || {};
    var delay = opts.delay != null ? opts.delay : 700;
    var failEvery = opts.failEvery || 0, calls = 0, counter = 0;
    var enc = {}, sess = {};
    var P = { coins: 20, xp: 0, level: 1, skills: {}, skillXp: {}, owned: { c_white: 1, j_white: 1, s_white: 1, a_white: 1 }, eq: { cap: 'c_white', jersey: 'j_white', shoes: 's_white', sleeve: 'a_white' }, tier: 0, cp: {}, cool: {}, look: null, created: false, lastFac: 0, practiceDay: '' };
    FAMILIES.forEach(function (f) { P.skills[f.id] = 0; P.skillXp[f.id] = 0; });
    function wait(v) { return new Promise(function (res, rej) { setTimeout(function () { calls++; if (failEvery && calls % failEvery === 0) rej({ code: 'NETWORK', message: 'The agent did not answer. Try again.' }); else { try { res(v()); } catch (e) { rej(e); } } }, delay); }); }
    function snap() { return JSON.parse(JSON.stringify({ coins: P.coins, xp: P.xp, level: P.level, skills: P.skills, skillXp: P.skillXp, owned: P.owned, eq: P.eq, tier: P.tier, cp: P.cp, look: P.look, created: P.created })); }
    function levelFor(xp) { var l = 1; for (var i = 1; i < LEVEL_XP.length; i++) if (xp >= LEVEL_XP[i]) l = i + 1; return l; }
    function skillFor(x) { var l = 0; for (var i = 1; i < SKILL_XP.length; i++) if (x >= SKILL_XP[i]) l = i; return l; }
    function itemOf(id) { return ITEMS.filter(function (i) { return i.id === id; })[0]; }
    function gearOk(g) { return g.worn ? P.eq[itemOf(g.worn).slot] === g.worn : Object.keys(P.owned).some(function (id) { var it = itemOf(id); return it.slot === g.any && it.price > 0; }); }
    function gearText(g) { return g.worn ? 'Wear the ' + itemOf(g.worn).name : 'Own an upgraded ' + g.any; }
    function pay(coins, xp, fam) {
      var before = P.level, bs = fam ? P.skills[fam] : 0;
      P.coins += coins; P.xp += xp; P.level = levelFor(P.xp);
      if (fam) { P.skillXp[fam] += xp; P.skills[fam] = skillFor(P.skillXp[fam]); }
      return { levelUp: P.level > before ? P.level : null, skillUp: fam ? P.skills[fam] > bs : false };
    }
    function requirements(c) {
      var out = [{ kind: 'level', text: 'Reach Level ' + c.level, ok: P.level >= c.level }];
      Object.keys(c.skills).forEach(function (k) { var fam = FAMILIES.filter(function (f) { return f.id === k; })[0]; out.push({ kind: 'skill', text: fam.name + ' skill ' + c.skills[k], ok: P.skills[k] >= c.skills[k] }); });
      c.gear.forEach(function (g) { out.push({ kind: 'gear', text: gearText(g), ok: gearOk(g) }); });
      var n = CHECKPOINTS[c.tier];
      if (n) out.push({ kind: 'checkpoint', text: 'Clear ' + n + ' checkpoints (' + ((P.cp[c.tier] || 0)) + ' of ' + n + ')', ok: (P.cp[c.tier] || 0) >= n });
      return out;
    }
    function clubState(c) {
      var req = requirements(c), met = req.every(function (r) { return r.ok; });
      return { id: c.id, tier: c.tier, name: c.name, venue: c.venue, mode: c.mode, requirements: req, eligible: met && P.tier === c.tier - 1, enrolled: P.tier >= c.tier, reason: P.tier >= c.tier ? 'enrolled' : P.tier < c.tier - 1 ? 'previous' : met ? 'ready' : 'requirements' };
    }
    function cooling(sid) { var t = P.cool[sid]; return t && Date.now() < t ? t : 0; }
    function sessionPurpose(sid) { var s = SESSIONS[sid]; if (s.enrol && s.tier) return P.tier >= s.enrol ? 'play' : 'enrol'; if (s.enrol) return P.tier >= s.enrol ? 'joined' : 'enrol'; return 'play'; }
    function sessionFor(npc) { if (npc.session) return npc.session; if (npc.role === 'recruit') return TIER_SESSION[npc.tier - 1]; return null; }
    function markers(npcs) {
      var out = {};
      (npcs || []).forEach(function (n) {
        var m = 'new', t = n.tier || 0;
        if (n.role === 'store') m = 'store';
        else if (n.role === 'staff') m = 'talk';
        else if (n.role === 'practice') m = P.tier >= 1 ? 'new' : 'locked';
        else if (n.role === 'lesson') m = P.tier >= t ? 'learn' : 'locked';
        else if (n.role === 'checkpoint') { var done = P.cp[t] || 0; m = P.tier >= t ? 'done' : done >= n.step ? 'done' : (done === n.step - 1 && P.tier === t - 1) ? 'new' : 'locked'; }
        else if (n.role === 'recruit' || n.role === 'match') {
          var sid = sessionFor(n), s = SESSIONS[sid];
          if (s.enrol && P.tier >= s.enrol && n.role === 'recruit') m = 'done';
          else {
            var club = CLUBS[(s.enrol || s.tier) - 1], st = clubState(club);
            if (s.tier && !s.enrol) m = P.tier >= s.tier ? (cooling(sid) ? 'locked' : 'match') : 'locked';
            else if (s.tier === 2 || s.tier === 4) m = P.tier >= s.tier ? (cooling(sid) ? 'locked' : 'match') : (st.eligible ? 'match' : 'locked');
            else m = st.eligible ? 'new' : 'locked';
          }
        } else if (n.role === 'friend' && n.tier && P.tier < n.tier) m = 'new';
        out[n.id] = m;
      });
      return out;
    }
    function questionEnc(npc, fam, diff, ex) {
      var id = 'enc_' + (++counter), seed = (Date.now() ^ (counter * 2654435761)) >>> 0;
      var built = buildQuestion(fam, diff, seed), q = built.q, kind = 'formula';
      if (npc.role === 'friend' && counter % 4 === 0 && !ex.session) kind = 'value';
      var coins = 12 + 6 * diff + (seed % 7), xp = 20 + 10 * diff;
      if (ex.session && ex.session.big) { coins = Math.round(coins * 2.2); xp = Math.round(xp * 2); }
      var limit = ex.limit || 0;
      var out = { encounterId: id, kind: 'question', npc: npc.name, family: fam, difficulty: diff, say: ex.say || q.story,
        question: { type: kind, prompt: ex.say || q.story, task: kind === 'value' ? q.task + ' Type the VALUE you expect, not the formula.' : q.task, sheet: { cols: 'ABCDEF'.slice(0, Math.max.apply(null, q.rows.map(function (r) { return r.length; })) ).split(''), rows: q.rows, target: { r: q.tr, c: q.tc } }, mustUse: q.mustUse, hint: q.hint, timeLimit: limit },
        reward: { coins: coins, xp: xp }, player: snap() };
      if (ex.session) out.session = ex.session;
      if (ex.checkpoint) out.checkpoint = ex.checkpoint;
      enc[id] = { npc: npc, q: q, expected: built.expected, kind: kind, fam: fam, coins: coins, xp: xp, tries: 0, done: false, grid: q.rows, sid: ex.sid || '', cp: ex.cp || null };
      return out;
    }
    function nextRound(sid, npc) {
      var S = sess[sid], s = SESSIONS[sid];
      var fam = ROLE_FAMILY[(S.round * 3 + counter) % 7];
      var limit = s.secs ? s.secs * (S.relaxed ? 2 : 1) : 0;
      return questionEnc(npc, fam, 3, { sid: sid, limit: limit, session: { id: sid, name: s.name, round: S.round, rounds: s.rounds, passMark: s.pass, correct: S.correct, relaxed: !!S.relaxed, big: !!s.big }, say: 'Over ' + S.round + ' of ' + s.rounds + '. ' });
    }
    function finishSession(sid) {
      var S = sess[sid], s = SESSIONS[sid], passed = S.correct >= s.pass, res = { passed: passed, correct: S.correct, rounds: s.rounds, passMark: s.pass, name: s.name, enrolledTier: null, bonus: { coins: 0, xp: 0 }, levelUp: null };
      if (passed) {
        var b = s.big ? { coins: 140, xp: 220 } : s.enrol ? { coins: 40 + 10 * s.enrol, xp: 60 + 20 * s.enrol } : { coins: 20 + 8 * (s.tier || 1), xp: 30 + 10 * (s.tier || 1) };
        var r = pay(b.coins, b.xp, null); res.bonus = b; res.levelUp = r.levelUp;
        var t = s.enrol || ((s.tier === 2 || s.tier === 4) ? s.tier : 0);
        if (t && P.tier === t - 1 && clubState(CLUBS[t - 1]).eligible) { P.tier = t; res.enrolledTier = t; }
      }
      var club = CLUBS[(s.enrol || s.tier || 1) - 1];
      res.message = passed ? (res.enrolledTier ? 'Selected. Welcome to ' + club.name + '.' : 'Well played. ' + S.correct + ' of ' + s.rounds + ' right.') : 'Not this time. You needed ' + s.pass + ' right and got ' + S.correct + '.' + (s.cooldownH ? ' Come back when the cooldown ends.' : ' You can try again.');
      res.nextAt = P.cool[sid] || 0;
      delete sess[sid];
      return res;
    }
    return {
      name: 'mock',
      world: function (npcs) { return wait(function () { return { config: { levelXp: LEVEL_XP, skillXp: SKILL_XP, families: FAMILIES, items: ITEMS, clubs: CLUBS.map(function (c) { return { id: c.id, tier: c.tier, name: c.name, venue: c.venue }; }), facilities: FACILITY_TIER }, player: snap(), markers: markers(npcs), now: Date.now() }; }); },
      createPlayer: function (look) { return wait(function () { P.look = { name: String(look.name || 'Player').slice(0, 14), gender: look.gender, body: look.body, skin: look.skin, hairStyle: look.hairStyle, hairColor: look.hairColor }; P.created = true; return { ok: true, player: snap() }; }); },
      encounter: function (npc) {
        return wait(function () {
          var id = 'enc_' + (++counter), t = npc.tier || 0;
          if (npc.role === 'store') return { encounterId: id, kind: 'store', npc: npc.name, say: 'Welcome. Everything here is paid for with coins. You can wear it straight away.', items: ITEMS, player: snap() };
          if (npc.role === 'staff') { enc[id] = {}; return { encounterId: id, kind: 'chat', npc: npc.name, say: npc.name + ' nods. "' + TIPS[(counter + npc.id.length) % TIPS.length] + '"', player: snap() }; }
          if (npc.role === 'lesson') {
            if (P.tier < t) return { encounterId: id, kind: 'chat', npc: npc.name, say: 'This is for members only. Join ' + CLUBS[t - 1].name + ' first.', player: snap() };
            enc[id] = { npc: npc, lesson: npc.lesson };
            return { encounterId: id, kind: 'lesson', npc: npc.name, say: 'What would you like to learn today? Pick one.', topics: LESSON_TOPICS[npc.lesson].map(function (f) { var fm = FAMILIES.filter(function (x) { return x.id === f; })[0]; return { id: f, name: fm.name, blurb: fm.blurb }; }), player: snap() };
          }
          if (npc.role === 'checkpoint') {
            var done = P.cp[t] || 0;
            if (P.tier >= t) return { encounterId: id, kind: 'chat', npc: npc.name, say: 'You have already cleared this. Go well.', player: snap() };
            if (P.tier < t - 1) return { encounterId: id, kind: 'chat', npc: npc.name, say: 'Not yet. Finish the earlier club first.', player: snap() };
            if (done >= npc.step) return { encounterId: id, kind: 'chat', npc: npc.name, say: 'Checkpoint cleared. Move on to the next one.', player: snap() };
            if (done < npc.step - 1) return { encounterId: id, kind: 'chat', npc: npc.name, say: 'Checkpoints go in order. Clear checkpoint ' + (done + 1) + ' first.', player: snap() };
            return questionEnc(npc, ROLE_FAMILY[(counter + t) % 7], 3, { cp: { tier: t, step: npc.step }, checkpoint: { tier: t, step: npc.step, of: CHECKPOINTS[t] }, say: 'Checkpoint ' + npc.step + ' of ' + CHECKPOINTS[t] + '. ' });
          }
          if (npc.role === 'recruit' || npc.role === 'match') {
            var sid = sessionFor(npc), s = SESSIONS[sid], ct = s.enrol || s.tier, club = CLUBS[ct - 1], cs = clubState(club), purpose = sessionPurpose(sid);
            var cd = cooling(sid), ready = !cd, canBegin = false, say = '';
            if (purpose === 'joined') { say = 'You already wear our colours. Well played.'; }
            else if (purpose === 'enrol') {
              if (!cs.eligible) say = cs.reason === 'previous' ? 'Join ' + CLUBS[ct - 2].name + ' first. We take players who have come up the ladder.' : 'Not yet. Come back when every item on this list is ticked.';
              else if (!ready) say = 'You have already tried today. The next attempt opens later.';
              else { say = 'You meet every requirement. ' + s.rounds + ' hard questions' + (s.secs ? ', ' + s.secs + ' seconds each' : '') + '. Get ' + s.pass + ' right and you are in.'; canBegin = true; }
            } else {
              if (P.tier < s.tier && !cs.eligible) say = cs.reason === 'previous' ? 'Join ' + CLUBS[ct - 2].name + ' first.' : 'Not yet. Come back when every item on this list is ticked.';
              else if (!ready) say = 'The next match opens later. Rest up.';
              else { say = P.tier >= s.tier ? 'Ready for a match? ' + s.rounds + ' hard questions' + (s.secs ? ', ' + s.secs + ' seconds each.' : '.') : 'You meet every requirement. Win this match to join. ' + s.rounds + ' hard questions' + (s.secs ? ', ' + s.secs + ' seconds each.' : '.'); canBegin = true; }
            }
            enc[id] = { npc: npc, lobby: sid, canBegin: canBegin };
            return { encounterId: id, kind: 'lobby', npc: npc.name, say: say, session: { id: sid, name: s.name, rounds: s.rounds, passMark: s.pass, secondsPerRound: s.secs, cooldownHours: s.cooldownH, ready: ready, nextAt: cd, purpose: purpose }, club: cs, canBegin: canBegin, player: snap() };
          }
          var fam = npc.family || ROLE_FAMILY[(counter + npc.id.length) % 7];
          var diff = Math.max(1, Math.min(3, Math.ceil((P.skills[fam] + 1) / 1.5)));
          if (t >= 7) diff = 3;
          var say = FRIEND_SAY[npc.id] || '';
          if (npc.role === 'practice') { var day = new Date().toDateString(); if (P.practiceDay !== day) say = 'Daily practice bonus is on: your first question today pays double coins. '; }
          var q = questionEnc(npc, fam, diff, { say: say ? say + ' ' : '' });
          if (npc.role === 'practice') { var day2 = new Date().toDateString(); if (P.practiceDay !== day2) { enc[q.encounterId].coins *= 2; q.reward.coins *= 2; enc[q.encounterId].practice = day2; } }
          return q;
        });
      },
      sessionBegin: function (encounterId, o) {
        return wait(function () {
          var e = enc[encounterId];
          if (!e || !e.lobby) throw { code: 'EXPIRED', message: 'That lobby has closed. Talk to them again.' };
          var sid = e.lobby, s = SESSIONS[sid];
          if (!e.canBegin) throw { code: 'NOT_ELIGIBLE', message: 'You do not meet the requirements yet.' };
          if (cooling(sid)) throw { code: 'COOLDOWN', message: 'Not yet. The next attempt is still locked.' };
          sess[sid] = { round: 1, correct: 0, relaxed: !!(o && o.relaxed) };
          if (s.cooldownH) P.cool[sid] = Date.now() + s.cooldownH * HOUR;
          return nextRound(sid, e.npc);
        });
      },
      answer: function (encounterId, answer) {
        return wait(function () {
          var e = enc[encounterId];
          if (!e || !e.q) throw { code: 'EXPIRED', message: 'That question has expired. Ask again.' };
          if (e.done) return { correct: true, feedback: 'You already collected this one.', rewards: { coins: 0, xp: 0 }, player: snap() };
          e.tries++;
          var ok = false, fb = '', timeout = answer === null;
          if (timeout) fb = 'Time is up for this over.';
          else {
            try {
              if (e.kind === 'value') { var v = String(answer).trim(); ok = F.same(isNaN(Number(v)) || v === '' ? v : Number(v), e.expected); fb = ok ? '' : 'That value is not right. Work it out from the sheet.'; }
              else {
                var a = String(answer).trim();
                if (a[0] !== '=') fb = 'Formulas start with an equals sign.';
                else {
                  var got = F.evaluate(a, e.grid), used = F.usedFns(a), miss = e.q.mustUse.filter(function (m) { return used.indexOf(m) < 0; });
                  if (miss.length) fb = 'This one needs ' + miss.join(' and ') + '. Check the hint.';
                  else if (F.same(got, e.expected)) ok = true;
                  else fb = 'Your formula gives ' + got + '. That is not the answer. Check your range.';
                }
              }
            } catch (er) { fb = er.message === '#NAME?' ? 'Excel would show #NAME? here. Check spelling, quotes and brackets.' : /^#/.test(er.message) ? 'Excel would show ' + er.message + ' here.' : 'That formula could not be worked out. Check the brackets and ranges.'; }
          }
          var S = e.sid ? sess[e.sid] : null;
          function advance(extra) {
            if (!S) return extra;
            S.round++;
            if (S.round > SESSIONS[e.sid].rounds) extra.sessionResult = finishSession(e.sid); else extra.next = nextRound(e.sid, e.npc);
            extra.player = snap();
            return extra;
          }
          if (!ok) {
            if (S && (timeout || e.tries >= 2)) { e.done = true; return advance({ correct: false, roundOver: true, feedback: fb + ' That over is lost.', player: snap() }); }
            return { correct: false, feedback: fb, attempt: e.tries, player: snap() };
          }
          e.done = true;
          if (S) S.correct++;
          var r = pay(e.coins, e.xp, e.fam);
          if (e.practice) P.practiceDay = e.practice;
          if (e.cp) P.cp[e.cp.tier] = Math.max(P.cp[e.cp.tier] || 0, e.cp.step);
          P.cool[e.npc.id] = Date.now() + 15000;
          var out = { correct: true, feedback: 'Correct.', explanation: e.q.explain, rewards: { coins: e.coins, xp: e.xp, skill: { family: e.fam, level: P.skills[e.fam], up: r.skillUp } }, levelUp: r.levelUp, player: snap() };
          if (e.cp) out.checkpointCleared = { tier: e.cp.tier, step: e.cp.step, of: CHECKPOINTS[e.cp.tier] };
          return advance(out);
        });
      },
      trial: function (encounterId) { return wait(function () { throw { code: 'GONE', message: 'Trials are now sessions. Use Begin.' }; }); },
      lessonTopic: function (encounterId, fam) {
        return wait(function () {
          var e = enc[encounterId];
          if (!e || !e.lesson) throw { code: 'EXPIRED', message: 'That lesson has ended.' };
          var L = LESSONS[fam], r = pay(0, 8, fam);
          return { title: L.title, steps: L.steps, example: L.example, rewards: { coins: 0, xp: 8 }, levelUp: r.levelUp, player: snap() };
        });
      },
      facility: function (id) {
        return wait(function () {
          var t = FACILITY_TIER[id];
          if (!t) throw { code: 'NOT_FOUND', message: 'No such facility.' };
          if (P.tier < t) return { ok: false, locked: true, message: 'Members only. Join ' + CLUBS[t - 1].name + ' to use this.', player: snap() };
          if (Date.now() - P.lastFac < 7000) return { ok: true, tooSoon: true, player: snap() };
          P.lastFac = Date.now();
          var r = pay(2, 6, null);
          return { ok: true, rewards: { coins: 2, xp: 6 }, message: '+2 coins, +6 XP', levelUp: r.levelUp, player: snap() };
        });
      },
      buy: function (itemId) {
        return wait(function () {
          var it = itemOf(itemId);
          if (!it) throw { code: 'NOT_FOUND', message: 'No such item.' };
          if (P.owned[it.id]) throw { code: 'OWNED', message: 'You already own that.' };
          if (P.coins < it.price) throw { code: 'FUNDS', message: 'Not enough coins. Solve more questions at the Nets.' };
          P.coins -= it.price; P.owned[it.id] = 1; P.eq[it.slot] = it.id; return { ok: true, player: snap() };
        });
      },
      equip: function (itemId) { return wait(function () { var it = itemOf(itemId); if (!it || !P.owned[it.id]) throw { code: 'NOT_OWNED', message: 'You do not own that.' }; P.eq[it.slot] = it.id; return { ok: true, player: snap() }; }); },
      /* prototype only */
      debugBoost: function () { return wait(function () { P.coins += 600; P.xp += 700; P.level = levelFor(P.xp); FAMILIES.forEach(function (f) { P.skillXp[f.id] += 200; P.skills[f.id] = skillFor(P.skillXp[f.id]); }); P.cool = {}; return { ok: true, player: snap() }; }); },
      debugTier: function (t) { return wait(function () { P.tier = t; P.level = Math.max(P.level, t + 1); P.xp = Math.max(P.xp, LEVEL_XP[P.level - 1]); P.cool = {}; return { ok: true, player: snap() }; }); },
      debugCooldowns: function () { return wait(function () { P.cool = {}; return { ok: true, player: snap() }; }); },
      clubs: function () { return wait(function () { return CLUBS.map(clubState); }); }
    };
  }

  /* ---------- HttpAdapter skeleton: same method names, same return shapes ---------- */
  function HttpAdapter(opts) {
    var base = (opts && opts.baseUrl) || '', headers = (opts && opts.headers) || {};
    function call(method, path, body) {
      return fetch(base + path, { method: method, headers: Object.assign({ 'Content-Type': 'application/json' }, headers), body: body ? JSON.stringify(body) : undefined, credentials: 'include' })
        .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw { code: j.code || 'HTTP_' + r.status, message: j.message || 'The server said no.' }; return j; }); })
        .catch(function (e) { if (e && e.code) throw e; throw { code: 'NETWORK', message: 'Could not reach the server.' }; });
    }
    var id = encodeURIComponent;
    return {
      name: 'http',
      world: function () { return call('GET', '/api/world'); },
      createPlayer: function (look) { return call('POST', '/api/player', look); },
      encounter: function (npc) { return call('POST', '/api/npcs/' + id(npc.id) + '/encounter'); },
      sessionBegin: function (encId, o) { return call('POST', '/api/encounters/' + id(encId) + '/begin', o || {}); },
      answer: function (encId, answer) { return call('POST', '/api/encounters/' + id(encId) + '/answer', { answer: answer }); },
      lessonTopic: function (encId, topic) { return call('POST', '/api/encounters/' + id(encId) + '/lesson', { topic: topic }); },
      facility: function (fid) { return call('POST', '/api/facilities/' + id(fid) + '/visit'); },
      buy: function (itemId) { return call('POST', '/api/store/buy', { itemId: itemId }); },
      equip: function (itemId) { return call('POST', '/api/avatar/equip', { itemId: itemId }); },
      clubs: function () { return call('GET', '/api/clubs'); }
    };
  }

  var current = MockAdapter();
  function dbg(name) { return function (a) { return current[name] ? current[name](a) : Promise.reject({ code: 'NOPE', message: 'Not available.' }); }; }
  root.CCApi = {
    use: function (kind, opts) { current = kind === 'http' ? HttpAdapter(opts) : MockAdapter(opts); return current.name; },
    get name() { return current.name; },
    world: function (n) { return current.world(n); },
    createPlayer: function (l) { return current.createPlayer(l); },
    encounter: function (n) { return current.encounter(n); },
    sessionBegin: function (id, o) { return current.sessionBegin(id, o); },
    answer: function (id, a) { return current.answer(id, a); },
    lessonTopic: function (id, t) { return current.lessonTopic(id, t); },
    facility: function (f) { return current.facility(f); },
    buy: function (i) { return current.buy(i); },
    equip: function (i) { return current.equip(i); },
    clubs: function () { return current.clubs(); },
    debugBoost: dbg('debugBoost'), debugTier: dbg('debugTier'), debugCooldowns: dbg('debugCooldowns'),
    _test: { buildQuestion: buildQuestion, CLUBS: CLUBS, FAMILIES: FAMILIES, SESSIONS: SESSIONS, MockAdapter: MockAdapter }
  };
  if (typeof module !== 'undefined') module.exports = root.CCApi;
})(typeof window !== 'undefined' ? window : globalThis);
