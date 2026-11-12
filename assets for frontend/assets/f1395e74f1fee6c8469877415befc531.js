/* Crease and Cells: world data. Pure data and small helpers, no game rules.
   World is a 5600 by 5600 square. The backend never sees positions. CC0 dedication.
   Layout rule: people stand south or east of buildings, never north of them, because the
   isometric camera hides anything standing behind a tall building. */
(function (root) {
  'use strict';
  var N = root.CCNames || { people: {}, clubs: [] };
  var W = 5600, H = 5600;
  var START = { x: 1250, y: 4700 };

  var SKINS = ['#C68A5E', '#A66B43', '#7A4A2E', '#E8B98F', '#8D5A3B', '#D9A577'];
  var HAIRC = ['#1B1410', '#4A2E1E', '#B9B5AA', '#7A3B1D', '#2B2B33'];
  var JER = ['j_white', 'j_sunrise', 'j_teal', 'j_terra'];
  var CAP = ['c_white', 'c_sun', 'c_hat', 'c_helm'];
  var SHO = ['s_white', 's_gold', 's_teal', 's_night'];
  var SLV = ['a_white', 'a_teal', 'a_gold', 'a_terra'];
  var BODY = ['slim', 'regular', 'broad'];
  var HAIR = ['short', 'curly', 'long', 'bun', 'none'];
  function hero(i, o) {
    var h = { body: BODY[i % 3], skin: SKINS[i % 6], hairStyle: HAIR[(i + 1) % 5], hairColor: HAIRC[(i + 2) % 5], jersey: JER[(i + 1) % 4], cap: CAP[(i + 2) % 4], shoes: SHO[(i + 3) % 4], sleeve: SLV[i % 4] };
    for (var k in (o || {})) h[k] = o[k];
    return h;
  }
  function fem(o) { o = o || {}; o.body = 'slim'; o.hairStyle = o.hairStyle || 'long'; return o; }

  /* the whole file builds with a movable origin so a block can be authored in its own corner */
  var OX = 0, OY = 0;
  function at(dx, dy) { OX = dx; OY = dy; }

  var FLOORS = [], BOXES = [], SIGNS = [], NPCS = [], TREES = [];
  var PLAZAS = [], DISCS = [], DECO = false;
  var SAND = '#E8D3A2', PAVE = '#F3E6C8', CLAY = '#D9B77E', WATER = '#4F9BB0', RUB = '#8A93A0', WOOD = '#A8774A';
  var STRIPE = 'repeating-linear-gradient(0deg,#7CB950 0 120px,#86C259 120px 240px)';
  var STRIPE2 = 'repeating-linear-gradient(90deg,#86C259 0 100px,#7CB950 100px 200px)';
  var CUT = 'repeating-linear-gradient(90deg,#5FA542 0 40px,#6FB04C 40px 80px)';
  var RAD = 'repeating-radial-gradient(circle at center,#7CB950 0 46px,#88C35C 46px 92px)';
  var STAND = ['#8A93A0', '#4F5B66', '#3C4650'], CREAM = ['#D9CBA8', '#F3E6C8', '#D9CBA8'], HEDGE = ['#2E6A3B', '#2E6A3B', '#25562F'];
  var MESH = ['rgba(255,255,255,0.14)', 'rgba(255,255,255,0.18)', 'rgba(255,255,255,0.1)'];

  function F(x, y, w, h, bg, z, r, css) { FLOORS.push({ x: x + OX, y: y + OY, w: w, h: h, bg: bg, z: z || 0, r: r || 0, css: css || '', deco: DECO }); }
  function disc(cx, cy, R, bg, z, css) { F(cx - R, cy - R, 2 * R, 2 * R, bg, z, R, css); }
  function Bx(id, x, y, w, d, h, c, o) {
    var b = { id: id, x: x + OX, y: y + OY, w: w, d: d, h: h, top: c[0], south: c[1], east: c[2] || c[1], kind: 'bld' };
    for (var k in (o || {})) b[k] = o[k];
    BOXES.push(b); return b;
  }
  function Sg(x, y, t, bg, fg, w, o) { var s = { x: x + OX, y: y + OY, t: t, bg: bg, fg: fg, w: w }; for (var k in (o || {})) s[k] = o[k]; SIGNS.push(s); }

  /* ---- base grass: 800 unit tiles so only the near ones are drawn ---- */
  for (var gx = 0; gx < 7; gx++) for (var gy = 0; gy < 7; gy++) F(gx * 800, gy * 800, 800, 800, (gx + gy) % 2 ? '#7CB950' : '#80BC54', 0);

  /* ---- a cricket ground: round outfield, rope, circle, a proper pitch, horseshoe of stands behind ---- */
  var GROUNDS = [];
  function ground(id, cx, cy, R, o) {
    o = o || {};
    GROUNDS.push({ id: id, cx: cx, cy: cy, R: R });
    disc(cx, cy, R + 70, SAND, 1);
    disc(cx, cy, R, RAD, 2, 'box-sizing:border-box;border:7px solid #FBF6E9');
    disc(cx, cy, R * 0.58, 'transparent', 3, 'box-sizing:border-box;border:3px dashed rgba(255,255,255,0.8)');
    var ph = Math.round(R * 0.62);
    F(cx - 38, cy - ph / 2, 76, ph, CLAY, 3, 10);
    F(cx - 38, cy - ph / 2 + 36, 76, 4, '#FBF6E9', 4);
    F(cx - 38, cy + ph / 2 - 40, 76, 4, '#FBF6E9', 4);
    F(cx - 8, cy - ph / 2 + 14, 16, 16, '#F4F1E8', 4, 3); F(cx - 8, cy + ph / 2 - 30, 16, 16, '#F4F1E8', 4, 3);
    if (o.stands !== false) {
      var Rs = R + 62, size = o.size || 64, a0 = 135, a1 = 315, arc = (a1 - a0) * Math.PI / 180 * Rs, n = Math.floor(arc / (size * 0.92));
      for (var i = 0; i < n; i++) {
        var th = (a0 + (a1 - a0) * (i + 0.5) / n) * Math.PI / 180, hh = 36 + (o.hMax || 70) * Math.sin(Math.PI * (i + 0.5) / n);
        Bx(id + 's' + i, Math.round(cx + Rs * Math.cos(th) - size / 2), Math.round(cy + Rs * Math.sin(th) - size / 2), size, size, Math.round(hh), o.colors || STAND, { kind: 'stand' });
      }
    }
  }

  /* ================= HOME: nets, store, town square, home maidan, park ================= */
  at(150, 4000);
  F(40, 40, 760, 620, STRIPE, 1, 0);
  F(900, 540, 400, 360, PAVE, 1, 30); F(1000, 600, 200, 200, SAND, 2, 100);
  F(60, 370, 740, 70, SAND, 2); F(760, 370, 60, 250, SAND, 2); F(760, 560, 160, 60, SAND, 2);
  F(1030, 440, 60, 110, PAVE, 2); F(1290, 770, 130, 60, PAVE, 2); F(920, 880, 60, 140, PAVE, 2);
  F(100, 980, 800, 340, '#6FB04C', 1, 40); F(300, 1060, 260, 140, WATER, 2, 70);
  /* the home maidan is a round practice ground */
  ground('hm', 1850, 1040, 290, { stands: false });
  for (var i = 0; i < 7; i++) Bx('cage' + i, 100 + i * 95, 110, 70, 220, 70, MESH, { mesh: true, line: 'rgba(255,255,255,0.8)', kind: 'cage' });
  Bx('store', 1000, 380, 160, 90, 80, ['#E8967A', '#F3E6C8', '#D9CBA8'], { door: 0.5, win: '#1F7A7A', awning: '#1F7A7A', text: 'KIT STORE' });
  Bx('tea', 1340, 640, 70, 40, 50, ['#1F7A7A', '#F3E6C8', '#D9CBA8'], { awning: '#1F7A7A' });
  Bx('kit', 880, 680, 70, 40, 50, ['#D9805F', '#F3E6C8', '#D9CBA8'], { awning: '#D9805F' });
  Bx('board', 1140, 960, 90, 24, 90, ['#3A4A41', '#26382F', '#1B2822'], { kind: 'board', text: 'NOTICES' });
  Bx('score', 700, 20, 90, 30, 170, ['#3A4A41', '#26382F', '#1B2822'], { kind: 'board', text: '214/5' });
  Bx('pav', 1790, 560, 120, 70, 60, ['#1F7A7A', '#F3E6C8', '#D9CBA8'], { awning: '#1F7A7A' });
  var HOME_POND = [300 + 150, 1060 + 4000, 260, 140];
  Sg(420, 100, 'THE NETS', '#F2B632', '#1F2A24', 130);
  Sg(1080, 380, 'KIT STORE', '#1F7A7A', '#FBF6E9', 140);
  Sg(1100, 600, 'TOWN SQUARE', '#FBF6E9', '#1F2A24', 150);
  Sg(1860, 1000, 'THE MAIDAN', '#F2B632', '#1F2A24', 130);
  Sg(500, 1020, 'ELM PARK', '#6FB04C', '#1F2A24', 110);

  /* ================= UNIVERSITY OF MUMBAI ================= */
  at(0, 0);
  F(380, 3410, 700, 330, '#8CC662', 1, 24); F(400, 3340, 520, 70, SAND, 2); F(640, 3410, 40, 400, PAVE, 2);
  PLAZAS.push([380, 3180, 700, 560]);
  Bx('uni', 480, 3200, 360, 140, 130, ['#8A93A0', '#C9B48A', '#A8946B'], { door: 0.5, win: '#1F2A24', awning: '#7A3B2E', text: 'UNIVERSITY OF MUMBAI' });
  Bx('unitower', 630, 3206, 60, 50, 230, ['#8A93A0', '#B8A27A', '#8F7B55'], { win: '#1F2A24' });
  Bx('unilib', 900, 3240, 90, 90, 90, ['#8A93A0', '#C9B48A', '#A8946B'], { win: '#1F2A24', text: 'LIBRARY' });
  /* the university maidan: round, hedged, with one members gate on the south side */
  ground('um', 1250, 3400, 270, { stands: false });
  (function () {
    var Rh = 300, size = 44, n = Math.floor(2 * Math.PI * Rh / (size * 0.9));
    for (var i = 0; i < n; i++) {
      var th = i / n * 2 * Math.PI, x = 1250 + Rh * Math.cos(th), y = 3400 + Rh * Math.sin(th);
      if (y > 3640 && Math.abs(x - 1250) < 82) continue;
      Bx('uh' + i, Math.round(x - size / 2), Math.round(y - size / 2), size, size, 30, HEDGE, { kind: 'hedge' });
    }
  })();
  var GATES = [{ id: 'gUni', x: 1180, y: 3690, w: 140, d: 20, h: 54, tier: 1, text: 'MEMBERS' }];
  Sg(660, 3500, 'CAMPUS', '#FBF6E9', '#1F2A24', 110);
  Sg(1250, 3730, 'UNIVERSITY MAIDAN', '#6FB04C', '#1F2A24', 190);

  /* ================= SHIELD CUP GROUND ================= */
  ground('sh', 2000, 2900, 380, { hMax: 80 });
  Bx('shScore', 1680, 2480, 90, 30, 140, ['#3A4A41', '#26382F', '#1B2822'], { kind: 'board', text: 'SHIELD' });
  Sg(2250, 3150, 'SHIELD CUP', '#F2B632', '#1F2A24', 140);

  /* ================= BORIVALI DISTRICT CLUB (heritage clubhouse, bar and ground) ================= */
  ground('bo', 1100, 2100, 340, { hMax: 50, colors: ['#C9B48A', '#B8A27A', '#8F7B55'] });
  F(1500, 1900, 420, 330, SAND, 2, 30);
  PLAZAS.push([1500, 1760, 420, 480]);
  Bx('boClub', 1560, 1950, 280, 140, 110, ['#C9B48A', '#F3E6C8', '#B8A27A'], { door: 0.35, win: '#7A2E2E', awning: '#7A2E2E', text: 'DISTRICT CLUB' });
  Bx('boBar', 1600, 1790, 140, 80, 70, ['#7A2E2E', '#A04A3A', '#7A3B2E'], { door: 0.7, win: '#F2B632', awning: '#3A4A41', text: 'CLUB BAR' });
  Bx('boPav', 1860, 2000, 50, 60, 50, ['#7A2E2E', '#A04A3A', '#7A3B2E'], {});
  Sg(1700, 1900, 'BORIVALI DISTRICT CLUB', '#7A2E2E', '#FBF6E9', 240);

  /* ================= STATE CRICKET GROUND (big ground, stands, trophy cabinets, club building) ================= */
  ground('st', 1700, 1150, 400, { hMax: 100, size: 72, colors: ['#8A93A0', '#D9805F', '#B86A4C'] });
  F(2220, 960, 330, 380, PAVE, 2, 30);
  PLAZAS.push([2220, 900, 330, 480]);
  Bx('stClub', 2250, 1000, 200, 130, 130, ['#8A93A0', '#D9805F', '#B86A4C'], { door: 0.5, win: '#1F7A7A', awning: '#1F7A7A', text: 'STATE CLUB' });
  Bx('stCup1', 2270, 1190, 30, 20, 50, ['#F2B632', '#E8C25A', '#C99410'], { kind: 'board', text: 'CUP' });
  Bx('stCup2', 2330, 1190, 30, 20, 50, ['#F2B632', '#E8C25A', '#C99410'], { kind: 'board', text: 'CUP' });
  Bx('stCup3', 2390, 1190, 30, 20, 50, ['#F2B632', '#E8C25A', '#C99410'], { kind: 'board', text: 'CUP' });
  Sg(2350, 1400, 'STATE CRICKET GROUND', '#D9805F', '#1F2A24', 240);

  /* ================= NATIONAL ACADEMY ================= */
  F(2880, 900, 700, 560, PAVE, 1, 36);
  PLAZAS.push([2880, 740, 700, 760]);
  F(2960, 960, 140, 100, RUB, 2, 8); F(3140, 960, 190, 100, WATER, 2, 12);
  Bx('naAcademy', 2980, 760, 260, 120, 120, ['#8A93A0', '#E8E2D0', '#C9C2A8'], { door: 0.5, win: '#1F4F8A', awning: '#1F4F8A', text: 'NATIONAL ACADEMY' });
  Bx('naNets', 2960, 1410, 340, 24, 50, MESH, { mesh: true, line: 'rgba(255,255,255,0.8)', kind: 'cage' });
  Sg(3100, 1480, 'NATIONAL ACADEMY GROUNDS', '#1F4F8A', '#FBF6E9', 260);

  /* ================= NATIONAL STADIUM: a big ground like the franchise grounds, with the national flag at the gate ================= */
  var WALLBLK = [];
  (function () {
    var cx = 4400, cy = 1300, R = 520;
    ground('ns', cx, cy, R, { hMax: 90, size: 80, colors: ['#8A93A0', '#1F4F8A', '#17396A'] });
    F(cx - 160, cy + R + 60, 320, 240, PAVE, 2, 10);
    Bx('nPillarL', cx - 130, cy + R + 70, 40, 40, 150, ['#FBF6E9', '#E8C25A', '#C99410'], { kind: 'stand' });
    Bx('nPillarR', cx + 90, cy + R + 70, 40, 40, 150, ['#FBF6E9', '#E8C25A', '#C99410'], { kind: 'stand' });
    Sg(cx + 110, cy + R + 150, 'NATIONAL XI', '#1F4F8A', '#FBF6E9', 150, { flag: true, poleH: 330, sub: 'Team of the nation', fixed: true });
    Sg(cx - 130, cy + R + 150, 'NATIONAL STADIUM', '#1F4F8A', '#FBF6E9', 220, { sub: 'Huge rewards', fixed: true });
  })();

  /* ================= FRANCHISE TOWN ================= */
  F(2850, 2950, 2650, 1500, '#A9CF86', 1, 36);
  PLAZAS.push([2850, 2950, 2650, 1500]);
  Bx('frShop', 3100, 3190, 160, 90, 70, ['#D9805F', '#F3E6C8', '#D9CBA8'], { awning: '#1F4F8A', text: 'FAN SHOP' });
  Bx('frCafe', 3320, 3200, 120, 80, 60, ['#E3C48C', '#F3E6C8', '#D9CBA8'], { awning: '#D9805F', text: 'CAFE' });
  Bx('frHQ', 3520, 3150, 280, 140, 120, ['#8A93A0', '#1F4F8A', '#17396A'], { door: 0.5, win: '#F3E6C8', awning: '#F2B632', text: 'FRANCHISE HQ' });
  Bx('frHotel', 3900, 3140, 260, 140, 150, ['#8A93A0', '#C9B48A', '#A8946B'], { win: '#1F2A24', text: 'TEAM HOTEL' });
  Bx('frGym', 3100, 3820, 220, 120, 90, ['#4F5B66', '#8A93A0', '#6C7780'], { door: 0.5, win: '#F3E6C8', awning: '#1F7A7A', text: 'GYM' });
  Bx('frAqua', 3450, 3820, 160, 100, 80, ['#2E6A7A', '#4F9BB0', '#3B7F94'], { door: 0.5, win: '#F3E6C8', text: 'AQUA CENTRE' });
  Bx('frSauna', 3720, 3820, 100, 100, 70, ['#8F5F36', '#A8774A', '#7A4F2E'], { door: 0.5, text: 'SAUNA' });
  Bx('frNets', 3920, 3820, 270, 130, 80, MESH, { mesh: true, line: 'rgba(255,255,255,0.8)', kind: 'cage' });
  F(3100, 3960, 220, 76, RUB, 2, 10); F(3450, 3960, 280, 120, WATER, 2, 16); F(3750, 3960, 100, 80, WOOD, 2, 8); F(3920, 3960, 270, 70, RUB, 2, 10);
  ground('ga', 3400, 4900, 380, { hMax: 90, colors: ['#8A93A0', '#1F4F8A', '#17396A'] });
  ground('gb', 4500, 4900, 380, { hMax: 90, colors: ['#8A93A0', '#1F4F8A', '#17396A'] });
  Sg(3180, 3520, 'FRANCHISE TOWN', '#1F4F8A', '#FBF6E9', 190);
  Sg(3550, 4560, 'GROUND A', '#FBF6E9', '#1F2A24', 110);
  Sg(4650, 4560, 'GROUND B', '#FBF6E9', '#1F2A24', 110);

  /* open lakes and parks to roam around */
  F(250, 400, 760, 480, SAND, 1, 240); F(300, 450, 660, 380, WATER, 2, 190);
  F(3100, 1760, 620, 380, SAND, 1, 190); F(3150, 1810, 520, 280, WATER, 2, 140);
  F(4000, 2640, 700, 420, '#6FB04C', 1, 200);
  F(250, 2700, 520, 340, '#6FB04C', 1, 160);
  Sg(620, 610, 'LAKE VIEW', '#4F9BB0', '#FBF6E9', 120);
  Sg(3420, 1950, 'RIVERSIDE WALK', '#6FB04C', '#1F2A24', 170);
  Sg(4350, 2840, 'EAST PARK', '#6FB04C', '#1F2A24', 120);

  /* ---- gates: closed until the server says the player is in that tier ---- */
  var FACILITIES = [
    { id: 'gym', name: 'Gym', x: 3100, y: 3960, w: 220, h: 76, tier: 6 },
    { id: 'pool', name: 'Swimming pool', x: 3450, y: 3960, w: 280, h: 120, tier: 6 },
    { id: 'sauna', name: 'Sauna', x: 3750, y: 3960, w: 100, h: 80, tier: 6 },
    { id: 'machine', name: 'Nets with bowling machine', x: 3920, y: 3960, w: 270, h: 70, tier: 6 },
    { id: 'gymN', name: 'Academy gym', x: 2960, y: 960, w: 140, h: 100, tier: 7 },
    { id: 'poolN', name: 'Academy pool and sauna', x: 3140, y: 960, w: 190, h: 100, tier: 7 }
  ];
  function facilityAt(x, y) { for (var k = 0; k < FACILITIES.length; k++) { var f = FACILITIES[k]; if (x >= f.x && x < f.x + f.w && y >= f.y && y < f.y + f.h) return f; } return null; }

  /* ---- people ---- */
  function nm(key) { var p = N.people[key] || [key, '']; return { name: p[0], tag: p[1] }; }
  function P(key, role, x, y, o, hv) {
    var n = nm(key), r = { id: key, name: n.name, tag: n.tag, role: role, x: x + OX, y: y + OY, hero: hv };
    for (var k in (o || {})) r[k] = o[k];
    if (r.rect) r.rect = { x: r.rect.x + OX, y: r.rect.y + OY, w: r.rect.w, h: r.rect.h };
    NPCS.push(r); return r;
  }
  var FAM = ['maths', 'text', 'logic', 'date', 'lookup', 'stats', 'arrays'];
  var COACH_KEYS = ['mukesh', 'viral', 'asst2', 'asst3', 'asst4', 'asst5', 'asst6'];
  at(150, 4000);
  COACH_KEYS.forEach(function (k, i) { P(k, 'coach', 135 + i * 95, 395, { family: FAM[i] }, i === 3 || i === 5 ? hero(i + 3, fem({ jersey: 'j_teal' })) : hero(i + 3, { jersey: 'j_teal', cap: i % 2 ? 'c_hat' : 'c_white' })); });
  P('akshita', 'store', 1050, 565, {}, hero(1, fem({ skin: '#E8B98F', hairColor: '#1B1410', jersey: 'j_sunrise', cap: 'c_sun', shoes: 's_gold', sleeve: 'a_teal' })));
  P('maya', 'work', 1130, 565, {}, hero(4, fem({ jersey: 'j_teal', hairStyle: 'bun' })));
  P('bholu', 'work', 1375, 775, {}, hero(8, { jersey: 'j_terra', cap: 'c_white' }));
  P('nandini', 'work', 915, 815, {}, hero(9, fem({ jersey: 'j_sunrise', cap: 'c_hat' })));
  P('gill', 'work', 1860, 830, {}, hero(14, { jersey: 'j_teal', cap: 'c_white' }));
  P('sana', 'quest', 1185, 1075, {}, hero(5, fem({ jersey: 'j_terra', cap: 'c_helm', skin: '#7A4A2E' })));
  P('parth', 'friend', 1850, 1040, { rect: { x: 1650, y: 860, w: 400, h: 360 } }, hero(2, { jersey: 'j_white', cap: 'c_white', body: 'regular', skin: '#C68A5E', hairStyle: 'short' }));
  at(0, 0);
  /* University */
  P('dean', 'recruit', 660, 3435, { tier: 1 }, hero(10, { jersey: 'j_terra', cap: 'c_white', skin: '#8D5A3B', hairColor: '#B9B5AA' }));
  [['sahil', 3], ['nikhil', 7], ['rahul', 11], ['nawaz', 13], ['jinal', 15], ['mo', 17]].forEach(function (a, i) {
    P(a[0], 'friend', 520 + i * 80, 3520, { rect: { x: 440, y: 3470, w: 480, h: 220 } }, a[0] === 'jinal' ? hero(a[1], fem({ jersey: 'j_white' })) : hero(a[1], { jersey: 'j_white', cap: 'c_white' }));
  });
  P('practice', 'practice', 1250, 3330, { tier: 1 }, hero(19, { jersey: 'j_teal', cap: 'c_sun' }));
  /* Shield Cup */
  P('shieldSel', 'match', 2150, 3090, { tier: 2, session: 'shield' }, hero(20, { jersey: 'j_sunrise', cap: 'c_white', skin: '#7A4A2E' }));
  /* Borivali District Club */
  P('steward', 'checkpoint', 1900, 2320, { tier: 3, step: 1 }, hero(21, { jersey: 'j_teal', cap: 'c_hat' }));
  P('secretary', 'checkpoint', 1650, 2190, { tier: 3, step: 2 }, hero(22, fem({ jersey: 'j_terra' })));
  P('arjun', 'recruit', 1340, 2230, { tier: 3 }, hero(23, { jersey: 'j_teal', cap: 'c_white', skin: '#A66B43' }));
  P('mishra', 'match', 1180, 2320, { tier: 4, session: 'inter' }, hero(24, { jersey: 'j_terra', cap: 'c_helm', skin: '#8D5A3B', hairColor: '#B9B5AA' }));
  /* State ground */
  P('lad', 'recruit', 2330, 1330, { tier: 5 }, hero(25, { jersey: 'j_terra', cap: 'c_helm', skin: '#7A4A2E', hairColor: '#B9B5AA' }));
  P('curator', 'work', 2250, 1330, {}, hero(26, { jersey: 'j_white', cap: 'c_hat' }));
  P('groundsman', 'work', 1820, 1300, {}, hero(27, { jersey: 'j_sunrise', cap: 'c_hat' }));
  /* Franchise town */
  P('fIcon', 'staff', 3180, 3400, {}, hero(29, { jersey: 'j_sunrise', cap: 'c_sun' }));
  P('fMgr', 'staff', 3380, 3400, {}, hero(31, { jersey: 'j_terra', cap: 'c_white' }));
  P('fDir', 'recruit', 3660, 3400, { tier: 6 }, hero(28, { jersey: 'j_teal', cap: 'c_white', skin: '#A66B43' }));
  P('fData', 'staff', 4030, 3400, {}, hero(30, fem({ jersey: 'j_teal' })));
  P('fMed', 'staff', 3150, 4130, {}, hero(38, { jersey: 'j_white', cap: 'c_white' }));
  P('fSC', 'staff', 3280, 4130, {}, hero(39, { jersey: 'j_teal', cap: 'c_white' }));
  P('fPhys', 'staff', 3560, 4140, {}, hero(40, { jersey: 'j_white', cap: 'c_white' }));
  P('fDev', 'lesson', 3990, 4130, { tier: 6, lesson: 'bowling' }, hero(37, { jersey: 'j_sunrise', cap: 'c_white' }));
  P('fBat', 'lesson', 4090, 4130, { tier: 6, lesson: 'batting' }, hero(34, { jersey: 'j_sunrise', cap: 'c_white' }));
  P('fBowl', 'lesson', 4190, 4130, { tier: 6, lesson: 'bowling' }, hero(35, { jersey: 'j_sunrise', cap: 'c_sun' }));
  P('fField', 'lesson', 4290, 4130, { tier: 6, lesson: 'fielding' }, hero(36, { jersey: 'j_sunrise', cap: 'c_hat' }));
  P('fHead', 'match', 3550, 5040, { tier: 6, session: 'leagueA' }, hero(32, { jersey: 'j_teal', cap: 'c_helm', skin: '#E8B98F' }));
  P('fPerf', 'match', 4650, 5040, { tier: 6, session: 'leagueB' }, hero(33, { jersey: 'j_teal', cap: 'c_white', skin: '#A66B43' }));
  /* National academy and stadium */
  P('nBat', 'lesson', 3000, 1180, { tier: 7, lesson: 'batting' }, hero(46, { jersey: 'j_teal' }));
  P('nBowl', 'lesson', 3140, 1180, { tier: 7, lesson: 'bowling' }, hero(47, { jersey: 'j_teal' }));
  P('nField', 'lesson', 3280, 1180, { tier: 7, lesson: 'fielding' }, hero(48, { jersey: 'j_teal' }));
  P('nFit', 'checkpoint', 3500, 2430, { tier: 7, step: 1 }, hero(41, { jersey: 'j_teal', cap: 'c_white' }));
  P('nSel', 'checkpoint', 3900, 2430, { tier: 7, step: 2 }, hero(42, { jersey: 'j_terra', cap: 'c_helm', hairColor: '#B9B5AA' }));
  P('nMgr', 'checkpoint', 4250, 2430, { tier: 7, step: 3 }, hero(43, { jersey: 'j_teal', cap: 'c_white' }));
  P('nCap', 'recruit', 4330, 1600, { tier: 7 }, hero(44, { jersey: 'j_terra', cap: 'c_helm', skin: '#C68A5E' }));
  P('nCoach', 'match', 4480, 1560, { tier: 7, session: 'national' }, hero(45, { jersey: 'j_terra', cap: 'c_white', skin: '#E8B98F', hairColor: '#B9B5AA' }));
  var SQ = { x: 4150, y: 1090, w: 500, h: 420 };
  ['p1', 'p2', 'p3', 'p4'].forEach(function (k, i) { P(k, 'friend', 4160 + i * 90, 1100 + (i % 2) * 60, { rect: SQ, tier: 7 }, hero(50 + i, { jersey: 'j_terra', cap: 'c_helm' })); });
  ['p5', 'p6', 'p7', 'p8'].forEach(function (k, i) { P(k, 'friend', 4200 + i * 90, 1340 + (i % 2) * 50, { rect: SQ, tier: 7 }, hero(54 + i, { jersey: 'j_terra', cap: 'c_white' })); });

  /* ---- route graph for auto walk. Edges with a third value 0 are not drawn as roads. ---- */
  var NODES = {
    n1: [270, 4405], n4: [580, 4405], n7: [890, 4405], c1: [940, 4405], c2: [940, 4590], sqW: [1080, 4590], sq: [1250, 4720], store: [1230, 4535], sqE: [1450, 4550], kitS: [1110, 4765], sqS: [1350, 4840], s1: [1500, 4800], m1: [1650, 4900], m2: [1970, 5040], pk1: [1100, 4900], pk2: [1100, 5010], pk3: [770, 5140], hE: [1450, 4720],
    A0: [2550, 4720], Aw: [2550, 3800], Af: [2550, 3600], As: [2550, 3150], J: [2550, 2350], Ac: [2550, 1330], At: [2550, 700],
    mgS: [1250, 3800], mgG: [1250, 3745], uPl: [660, 3800], uD: [660, 3420],
    shS: [2150, 3150], shP: [2150, 3110],
    b1: [1650, 2350], b2: [1650, 2230],
    st1: [2330, 1330],
    ac1: [2900, 1330], ac2: [3140, 1250],
    nt1: [3500, 2350], nt2: [4400, 2350], ntG: [4400, 2050], ntI: [4400, 1690],
    f0: [2950, 3600], f1: [3400, 3600], f2: [3660, 3600], f3: [3870, 3600], f4: [4500, 3600], f4b: [5040, 3600], f5: [5400, 3600],
    s2a: [3100, 4080], fa2: [3400, 4080], s2m: [3870, 4080], fb2: [4500, 4080], gaE: [3870, 4960], gbE: [5040, 4960], ga: [3550, 4960], gb: [4650, 4960], bdE: [1440, 4900], bdS: [1440, 5060]
  };
  var EDGES = [
    ['n1', 'n4', 0], ['n4', 'n7', 0], ['n7', 'c1', 0], ['c1', 'c2', 0], ['c2', 'sqW', 0], ['sqW', 'sq', 0], ['sq', 'store', 0], ['sq', 'sqE', 0], ['sq', 'hE', 0], ['sq', 'kitS', 0], ['sq', 'sqS', 0], ['sqS', 'bdE', 0], ['bdE', 'bdS', 0], ['sqS', 's1', 0], ['s1', 'm1', 0], ['m1', 'm2', 0], ['sq', 'pk1', 0], ['pk1', 'pk2', 0], ['pk2', 'pk3', 0],
    ['hE', 'A0'], ['A0', 'Aw'], ['Aw', 'Af'], ['Af', 'As'], ['As', 'J'], ['J', 'Ac'], ['Ac', 'At'],
    ['Aw', 'mgS'], ['mgS', 'uPl'], ['uPl', 'uD'], ['mgS', 'mgG'],
    ['As', 'shS'], ['shS', 'shP'],
    ['J', 'b1'], ['b1', 'b2'], ['Ac', 'st1'], ['Ac', 'ac1'], ['ac1', 'ac2', 0],
    ['J', 'nt1'], ['nt1', 'nt2'], ['nt2', 'ntG'], ['ntG', 'ntI', 0],
    ['Af', 'f0'], ['f0', 'f1'], ['f1', 'f2'], ['f2', 'f3'], ['f3', 'f4'], ['f4', 'f4b'], ['f4b', 'f5'],
    ['f1', 'fa2'], ['fa2', 's2a'], ['fa2', 's2m'], ['s2m', 'fb2'], ['f3', 's2m'], ['f4', 'fb2'], ['s2m', 'gaE'], ['f4b', 'gbE'], ['gaE', 'ga', 0], ['gbE', 'gb', 0]
  ];
  var ADJ = {};
  EDGES.forEach(function (e) { (ADJ[e[0]] = ADJ[e[0]] || []).push(e[1]); (ADJ[e[1]] = ADJ[e[1]] || []).push(e[0]); });
  function nearestNode(x, y) { var best = null, bd = 1e9; for (var k in NODES) { var d = Math.hypot(NODES[k][0] - x, NODES[k][1] - y); if (d < bd) { bd = d; best = k; } } return best; }
  function route(fx, fy, tx, ty) {
    var a = nearestNode(fx, fy), b = nearestNode(tx, ty), prev = {}, q = [a], seen = {};
    seen[a] = 1;
    while (q.length) { var u = q.shift(); if (u === b) break; (ADJ[u] || []).forEach(function (v) { if (!seen[v]) { seen[v] = 1; prev[v] = u; q.push(v); } }); }
    var path = [], c = b;
    while (c) { path.unshift(NODES[c]); c = prev[c]; if (c === a) { path.unshift(NODES[a]); break; } }
    if (a === b) path = [NODES[a]];
    path.push([tx, ty]);
    return path;
  }

  /* roads drawn from the graph: wide, pale, flat */
  EDGES.forEach(function (e) {
    if (e[2] === 0) return;
    var a = NODES[e[0]], b = NODES[e[1]], wd = 74;
    if (a[1] === b[1]) F(Math.min(a[0], b[0]) - wd / 2, a[1] - wd / 2, Math.abs(a[0] - b[0]) + wd, wd, PAVE, 2, 0);
    else if (a[0] === b[0]) F(a[0] - wd / 2, Math.min(a[1], b[1]) - wd / 2, wd, Math.abs(a[1] - b[1]) + wd, PAVE, 2, 0);
  });

  /* ---- trees: scattered, sparse, kept off roads, buildings, grounds and people ---- */
  (function () {
    var seed = 20261101;
    function rnd() { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }
    var segs = [];
    EDGES.forEach(function (e) { var a = NODES[e[0]], b = NODES[e[1]]; segs.push([a[0], a[1], b[0], b[1]]); });
    function distSeg(px, py, s) {
      var dx = s[2] - s[0], dy = s[3] - s[1], L = dx * dx + dy * dy || 1, t = Math.max(0, Math.min(1, ((px - s[0]) * dx + (py - s[1]) * dy) / L));
      return Math.hypot(px - (s[0] + t * dx), py - (s[1] + t * dy));
    }
    var lakes = [[250, 400, 760, 480], [3100, 1760, 620, 380], [HOME_POND[0], HOME_POND[1], HOME_POND[2], HOME_POND[3]]];
    function ok(x, y) {
      if (x < 60 || y < 60 || x > W - 60 || y > H - 60) return false;
      for (var i = 0; i < segs.length; i++) if (distSeg(x, y, segs[i]) < 110) return false;
      for (i = 0; i < BOXES.length; i++) { var b = BOXES[i]; if (x > b.x - 90 && x < b.x + b.w + 90 && y > b.y - 90 && y < b.y + b.d + 90) return false; }
      for (i = 0; i < GROUNDS.length; i++) { var g = GROUNDS[i]; if (Math.hypot(x - g.cx, y - g.cy) < g.R + 160) return false; }
      for (i = 0; i < PLAZAS.length; i++) { var p = PLAZAS[i]; if (x > p[0] - 40 && x < p[0] + p[2] + 40 && y > p[1] - 40 && y < p[1] + p[3] + 40) return false; }
      for (i = 0; i < lakes.length; i++) { var l = lakes[i]; if (x > l[0] - 50 && x < l[0] + l[2] + 50 && y > l[1] - 50 && y < l[1] + l[3] + 50) return false; }
      for (i = 0; i < NPCS.length; i++) if (Math.hypot(x - NPCS[i].x, y - NPCS[i].y) < 130) return false;
      if (x > 190 && x < 2460 && y > 4040 && y < 5330) { if (rnd() < 0.7) return false; }
      return true;
    }
    var vars = ['a', 'b', 'palm'];
    for (var gy = 90; gy < H - 60; gy += 240) for (var gx = 90; gx < W - 60; gx += 240) {
      var x = gx + Math.round(rnd() * 160 - 80), y = gy + Math.round(rnd() * 160 - 80), r = rnd();
      if (r > 0.58) continue;
      if (!ok(x, y)) continue;
      TREES.push({ x: x, y: y, variant: vars[Math.floor(rnd() * 3)], size: 170 + Math.round(rnd() * 60) });
    }
  })();

  var DESTS = [
    { id: 'nets', name: 'The Nets', x: 580, y: 4410, area: 'Home' },
    { id: 'store', name: 'Kit Store', x: 1230, y: 4535, area: 'Home' },
    { id: 'square', name: 'Town Square', x: 1250, y: 4720, area: 'Home' },
    { id: 'board', name: 'Notice board', x: 1335, y: 5100, area: 'Home' },
    { id: 'maidan', name: 'The Maidan', x: 2000, y: 5040, area: 'Home' },
    { id: 'park', name: 'Elm Park', x: 770, y: 5140, area: 'Home' },
    { id: 'uni', name: 'University of Mumbai', x: 660, y: 3420, area: 'Clubs and grounds, in order' },
    { id: 'unim', name: 'University Maidan', x: 1250, y: 3730, area: 'Clubs and grounds, in order' },
    { id: 'shield', name: 'Shield Cup ground', x: 2150, y: 3110, area: 'Clubs and grounds, in order' },
    { id: 'bori', name: 'Borivali District Club', x: 1650, y: 2260, area: 'Clubs and grounds, in order' },
    { id: 'state', name: 'State Cricket Ground', x: 2330, y: 1330, area: 'Clubs and grounds, in order' },
    { id: 'town', name: 'Franchise Town', x: 3660, y: 3470, area: 'Clubs and grounds, in order' },
    { id: 'natl', name: 'National Stadium', x: 4400, y: 1690, area: 'Clubs and grounds, in order' },
    { id: 'gym', name: 'Franchise gym', x: 3210, y: 4040, area: 'Facilities' },
    { id: 'pool', name: 'Pool and sauna', x: 3600, y: 4040, area: 'Facilities' },
    { id: 'machine', name: 'Nets and bowling machine', x: 4050, y: 4040, area: 'Facilities' },
    { id: 'ga', name: 'Ground A', x: 3550, y: 4960, area: 'Facilities' },
    { id: 'gb', name: 'Ground B', x: 4650, y: 4960, area: 'Facilities' },
    { id: 'academy', name: 'National Academy', x: 3140, y: 1250, area: 'Facilities' }
  ];

  var ZONES = [
    { name: 'National Stadium', x: 3560, y: 440, w: 1700, h: 1700, bg: '#1F4F8A', fg: '#FBF6E9' },
    { name: 'National Academy', x: 2850, y: 700, w: 720, h: 800, bg: '#1F4F8A', fg: '#FBF6E9' },
    { name: 'Franchise Town', x: 2850, y: 2950, w: 2750, h: 2650, bg: '#1F4F8A', fg: '#FBF6E9' },
    { name: 'State Cricket Ground', x: 1160, y: 640, w: 1350, h: 1000, bg: '#D9805F', fg: '#1F2A24' },
    { name: 'Borivali District Club', x: 660, y: 1700, w: 1300, h: 960, bg: '#7A2E2E', fg: '#FBF6E9' },
    { name: 'Shield Cup ground', x: 1560, y: 2420, w: 900, h: 920, bg: '#F2B632', fg: '#1F2A24' },
    { name: 'University of Mumbai', x: 340, y: 3100, w: 1260, h: 800, bg: '#8A93A0', fg: '#1F2A24' },
    { name: 'The Nets', x: 150, y: 4000, w: 830, h: 700, bg: '#F2B632', fg: '#1F2A24' },
    { name: 'Town Square', x: 980, y: 4330, w: 610, h: 1270, bg: '#1F7A7A', fg: '#FBF6E9' },
    { name: 'The Maidan', x: 1590, y: 4700, w: 960, h: 900, bg: '#6FB04C', fg: '#1F2A24' },
    { name: 'Elm Park', x: 150, y: 4900, w: 830, h: 700, bg: '#6FB04C', fg: '#1F2A24' },
    { name: 'Open country', x: 0, y: 0, w: 5600, h: 5600, bg: '#6FB04C', fg: '#1F2A24' }
  ];
  function zoneAt(x, y) { for (var k = 0; k < ZONES.length; k++) { var z = ZONES[k]; if (x >= z.x && x < z.x + z.w && y >= z.y && y < z.y + z.h) return z; } return ZONES[ZONES.length - 1]; }

  /* collision rectangles [x,y,w,d]. The locked gate is added by the game. */
  var BLOCKS = [];
  BOXES.forEach(function (b) { BLOCKS.push([b.x, b.y, b.w, b.d]); });
  BLOCKS.push([HOME_POND[0], HOME_POND[1], HOME_POND[2], HOME_POND[3]]);
  WALLBLK.forEach(function (r) { BLOCKS.push(r); });

  /* keep every name board clear of buildings, people and other boards (screen space test) */
  (function () {
    var c = Math.cos(58 * Math.PI / 180), sn = Math.sin(58 * Math.PI / 180), q = Math.SQRT1_2;
    var U = function (x, y) { return (x - y) * q; }, Vv = function (x, y) { return (x + y) * q; };
    var SY = function (x, y, z) { return Vv(x, y) * c - z * sn; };
    var boxBB = BOXES.filter(function (b) { return b.kind !== 'hedge' && b.h >= 30; }).concat(GATES.map(function (g) { return { x: g.x, y: g.y, w: g.w, d: g.d, h: g.h }; })).map(function (b) {
      var cs = [[b.x, b.y], [b.x + b.w, b.y], [b.x, b.y + b.d], [b.x + b.w, b.y + b.d]], us = cs.map(function (k) { return U(k[0], k[1]); }), ys = [];
      cs.forEach(function (k) { ys.push(SY(k[0], k[1], 0), SY(k[0], k[1], b.h)); });
      return { x0: Math.min.apply(null, us), x1: Math.max.apply(null, us), y0: Math.min.apply(null, ys), y1: Math.max.apply(null, ys) };
    });
    var npcPts = [];
    NPCS.forEach(function (n) { npcPts.push([n.x, n.y]); if (n.rect) { npcPts.push([n.rect.x + n.rect.w / 2, n.rect.y + n.rect.h / 2]); } });
    var npcBB = npcPts.map(function (p) { var u = U(p[0], p[1]), f = SY(p[0], p[1], 0); return { x0: u - 40, x1: u + 40, y0: f - 140, y1: f + 12 }; });
    var placed = [];
    var bbOf = function (s, x, y) { var w = Math.max(s.w, 150) / 2 + 8, u = U(x, y), f = SY(x, y, 0); return { x0: u - w, x1: u + w, y0: f - ((s.poleH || 44) + 100), y1: f + 14 }; };
    var ov = function (a, b) { return Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0) > 4 && Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0) > 4; };
    var inBlock = function (x, y) { for (var i = 0; i < BOXES.length; i++) { var b = BOXES[i]; if (x > b.x - 40 && x < b.x + b.w + 40 && y > b.y - 40 && y < b.y + b.d + 40) return true; } return false; };
    var offs = []; for (var dx = -500; dx <= 500; dx += 50) for (var dy = -500; dy <= 500; dy += 50) offs.push([dx, dy]);
    offs.sort(function (a, b) { return Math.hypot(a[0], a[1]) - Math.hypot(b[0], b[1]); });
    var ok = function (s, x, y) {
      if (x < 80 || y < 80 || x > W - 80 || y > H - 80 || inBlock(x, y)) return false;
      var bb = bbOf(s, x, y), i;
      for (i = 0; i < boxBB.length; i++) if (ov(bb, boxBB[i])) return false;
      for (i = 0; i < npcBB.length; i++) if (ov(bb, npcBB[i])) return false;
      for (i = 0; i < placed.length; i++) if (ov(bb, placed[i])) return false;
      return true;
    };
    SIGNS.forEach(function (s) {
      if (s.fixed) { placed.push(bbOf(s, s.x, s.y)); return; }
      for (var k = 0; k < offs.length; k++) {
        var x = s.x + offs[k][0], y = s.y + offs[k][1];
        if (ok(s, x, y)) { s.x = x; s.y = y; placed.push(bbOf(s, x, y)); return; }
      }
      placed.push(bbOf(s, s.x, s.y));
    });
  })();

  function meshBg(line) { return 'repeating-linear-gradient(0deg,' + line + ' 0 2px,transparent 2px 12px),repeating-linear-gradient(90deg,' + line + ' 0 2px,transparent 2px 12px)'; }
  function view(b) {
    var round = b.kind === 'hedge' ? 0.5 : b.kind === 'stand' ? 0.3 : (b.kind === 'cage' || b.kind === 'board') ? 0.08 : 0.14;
    var rr = Math.round(Math.min(b.w, b.d) * round), rh = Math.min(rr, Math.round(b.h / 2));
    var soft = b.kind === 'cage' ? '' : 'radial-gradient(ellipse at 30% 25%,rgba(255,255,255,0.28),rgba(255,255,255,0) 62%),';
    var lite = b.kind === 'cage' ? '' : 'linear-gradient(180deg,rgba(255,255,255,0.16),rgba(0,0,0,0.06)),';
    var bgT = b.mesh ? meshBg(b.line) + ',' + b.top : soft + b.top, bgS = b.mesh ? meshBg(b.line) + ',' + b.south : lite + b.south, bgE = b.mesh ? meshBg(b.line) + ',' + b.east : lite.replace('255,255,255,0.16', '255,255,255,0.08').replace('0,0,0,0.06', '0,0,0,0.14') + b.east;
    b.v = {
      box: 'left:' + b.x + 'px;top:' + b.y + 'px;width:' + b.w + 'px;height:' + b.d + 'px',
      top: 'left:0;top:0;width:' + b.w + 'px;height:' + b.d + 'px;transform:translateZ(' + b.h + 'px);border-radius:' + rr + 'px;box-shadow:inset 0 0 0 3px rgba(255,255,255,0.18);background:' + bgT,
      south: 'left:0;top:' + b.d + 'px;width:' + b.w + 'px;height:' + b.h + 'px;border-radius:' + rh + 'px ' + rh + 'px 0 0;transform:translateZ(' + b.h + 'px) rotateX(-90deg);background:' + bgS + ';' + (b.mesh ? 'border:3px solid rgba(255,255,255,0.9);box-sizing:border-box' : ''),
      east: 'left:' + b.w + 'px;top:' + b.d + 'px;width:' + b.d + 'px;height:' + b.h + 'px;border-radius:' + rh + 'px ' + rh + 'px 0 0;transform:translateZ(' + b.h + 'px) rotateY(90deg) rotateZ(-90deg);background:' + bgE,
      shade: 'left:' + Math.round(b.h * 0.4) + 'px;top:' + Math.round(b.h * 0.4) + 'px;width:' + b.w + 'px;height:' + b.d + 'px;border-radius:' + rr + 'px;transform:translateZ(2px)',
      win: b.win ? 'left:0;top:14%;width:100%;height:30%;background:repeating-linear-gradient(90deg,transparent 0 12px,' + b.win + ' 12px 34px,transparent 34px 52px);opacity:0.85;border-radius:8px' : 'display:none',
      door: b.door ? 'left:' + Math.round(b.w * b.door - 16) + 'px;bottom:0;width:32px;height:50%;background:#26382F;border:2px solid #1F2A24;box-sizing:border-box;border-radius:16px 16px 0 0' : 'display:none',
      awning: b.awning ? 'left:-4px;top:0;width:calc(100% + 8px);height:20%;background:' + b.awning + ';border-bottom:3px solid #1F2A24;box-sizing:border-box;border-radius:' + Math.min(rh, 14) + 'px ' + Math.min(rh, 14) + 'px 10px 10px' : 'display:none',
      label: b.text ? 'display:flex' : 'display:none'
    };
    b.cx = b.x + b.w / 2; b.cy = b.y + b.d / 2;
  }
  BOXES.forEach(view);
  GATES.forEach(function (g) { g.b = { id: g.id, x: g.x, y: g.y, w: g.w, d: g.d, h: g.h, top: '#F2B632', south: 'repeating-linear-gradient(90deg,#F2B632 0 10px,#1F2A24 10px 16px)', east: '#D99A14', text: g.text }; view(g.b); });

  root.CCWorld = { W: W, H: H, START: START, FLOORS: FLOORS, BOXES: BOXES, TREES: TREES, SIGNS: SIGNS, NPCS: NPCS, BLOCKS: BLOCKS, GATES: GATES, GROUNDS: GROUNDS, FACILITIES: FACILITIES, facilityAt: facilityAt, NODES: NODES, EDGES: EDGES, DESTS: DESTS, ZONES: ZONES, zoneAt: zoneAt, route: route };
  if (typeof module !== 'undefined') module.exports = root.CCWorld;
})(typeof window !== 'undefined' ? window : globalThis);
