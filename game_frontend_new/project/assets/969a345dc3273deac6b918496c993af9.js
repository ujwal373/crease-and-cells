/* Crease and Cells: tiny spreadsheet formula evaluator.
   Used ONLY by the mock adapter, so the prototype can check unique questions by value.
   Your real backend replaces this. CC0 dedication, written for this project. */
(function (root) {
  'use strict';
  var FN = {};
  function num(v) { if (v === '' || v == null) return 0; if (typeof v === 'boolean') return v ? 1 : 0; var d = typeof v === 'string' ? dateSerial(v) : null; if (d !== null) return d; var n = Number(v); return isNaN(n) ? NaN : n; }
  function flat(args) { var o = []; args.forEach(function (a) { if (Array.isArray(a)) a.forEach(function (x) { if (Array.isArray(x)) o = o.concat(x); else o.push(x); }); else o.push(a); }); return o; }
  function nums(args) { return flat(args).filter(function (v) { return typeof v === 'number' && !isNaN(v); }); }
  function dateSerial(s) { var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s)); if (!m) return null; return Math.round(Date.UTC(+m[1], +m[2] - 1, +m[3]) / 86400000) + 25569; }
  function serialDate(n) { return new Date(Math.round((n - 25569) * 86400000)); }
  function crit(c) {
    if (typeof c === 'number') return function (v) { return v === c; };
    var s = String(c), m = /^(>=|<=|<>|>|<|=)?(.*)$/.exec(s), op = m[1] || '=', rhs = m[2], n = rhs !== '' && !isNaN(Number(rhs)) ? Number(rhs) : null;
    return function (v) {
      if (n !== null) { if (typeof v !== 'number') return op === '<>'; return op === '=' ? v === n : op === '<>' ? v !== n : op === '>' ? v > n : op === '<' ? v < n : op === '>=' ? v >= n : v <= n; }
      var a = String(v).toLowerCase(), b = rhs.toLowerCase();
      if (b.indexOf('*') >= 0) { var re = new RegExp('^' + b.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$'); return op === '<>' ? !re.test(a) : re.test(a); }
      return op === '<>' ? a !== b : a === b;
    };
  }
  FN.SUM = function (a) { return nums(a).reduce(function (x, y) { return x + y; }, 0); };
  FN.AVERAGE = function (a) { var n = nums(a); if (!n.length) throw new Error('#DIV/0!'); return FN.SUM(n) / n.length; };
  FN.MIN = function (a) { var n = nums(a); return n.length ? Math.min.apply(null, n) : 0; };
  FN.MAX = function (a) { var n = nums(a); return n.length ? Math.max.apply(null, n) : 0; };
  FN.COUNT = function (a) { return nums(a).length; };
  FN.COUNTA = function (a) { return flat(a).filter(function (v) { return v !== '' && v != null; }).length; };
  FN.MEDIAN = function (a) { var n = nums(a).sort(function (x, y) { return x - y; }), k = n.length; if (!k) throw new Error('#NUM!'); return k % 2 ? n[(k - 1) / 2] : (n[k / 2 - 1] + n[k / 2]) / 2; };
  FN.LARGE = function (a) { var n = nums([a[0]]).sort(function (x, y) { return y - x; }); return n[num(a[1]) - 1]; };
  FN.SMALL = function (a) { var n = nums([a[0]]).sort(function (x, y) { return x - y; }); return n[num(a[1]) - 1]; };
  FN.RANK = function (a) { var n = nums([a[1]]), v = num(a[0]), asc = num(a[2]) !== 0; return n.filter(function (x) { return asc ? x < v : x > v; }).length + 1; };
  FN.ROUND = function (a) { var p = Math.pow(10, num(a[1] || 0)), v = num(a[0]); return Math.sign(v) * Math.round(Math.abs(v) * p + 1e-9) / p; };
  FN.ABS = function (a) { return Math.abs(num(a[0])); };
  FN.INT = function (a) { return Math.floor(num(a[0])); };
  FN.IF = function (a) { return a[0] ? a[1] : (a.length > 2 ? a[2] : false); };
  FN.AND = function (a) { return flat(a).every(Boolean); };
  FN.OR = function (a) { return flat(a).some(Boolean); };
  FN.NOT = function (a) { return !a[0]; };
  FN.COUNTIF = function (a) { var f = crit(a[1]); return flat([a[0]]).filter(f).length; };
  FN.SUMIF = function (a) { var f = crit(a[1]), r = flat([a[0]]), s = a[2] ? flat([a[2]]) : r, t = 0; r.forEach(function (v, i) { if (f(v) && typeof s[i] === 'number') t += s[i]; }); return t; };
  FN.COUNTUNIQUE = function (a) { var o = {}; flat(a).forEach(function (v) { o[typeof v + ':' + v] = 1; }); return Object.keys(o).length; };
  FN.SUMPRODUCT = function (a) { var A = flat([a[0]]), B = flat([a[1]]), t = 0; A.forEach(function (v, i) { t += num(v) * num(B[i]); }); return t; };
  FN.LEN = function (a) { return String(a[0]).length; };
  FN.LEFT = function (a) { return String(a[0]).slice(0, a.length > 1 ? num(a[1]) : 1); };
  FN.RIGHT = function (a) { var s = String(a[0]), n = a.length > 1 ? num(a[1]) : 1; return n ? s.slice(-n) : ''; };
  FN.MID = function (a) { var s = num(a[1]) - 1; return String(a[0]).slice(s, s + num(a[2])); };
  FN.UPPER = function (a) { return String(a[0]).toUpperCase(); };
  FN.LOWER = function (a) { return String(a[0]).toLowerCase(); };
  FN.PROPER = function (a) { return String(a[0]).toLowerCase().replace(/(^|[^a-z])([a-z])/g, function (m, p, c) { return p + c.toUpperCase(); }); };
  FN.TRIM = function (a) { return String(a[0]).replace(/\s+/g, ' ').trim(); };
  FN.CONCAT = function (a) { return flat(a).join(''); };
  FN.CONCATENATE = FN.CONCAT;
  FN.TEXTJOIN = function (a) { return flat(a.slice(2)).filter(function (v) { return !a[1] || v !== ''; }).join(String(a[0])); };
  FN.VLOOKUP = function (a) { var t = a[1], k = a[0], c = num(a[2]) - 1, exact = a.length > 3 && !a[3]; for (var i = 0; i < t.length; i++) { if (String(t[i][0]).toLowerCase() === String(k).toLowerCase()) return t[i][c]; } if (!exact) { var best = null; for (var j = 0; j < t.length; j++) { if (typeof t[j][0] === 'number' && t[j][0] <= k) best = t[j][c]; } if (best !== null) return best; } throw new Error('#N/A'); };
  FN.MATCH = function (a) { var r = flat([a[1]]); for (var i = 0; i < r.length; i++) { if (String(r[i]).toLowerCase() === String(a[0]).toLowerCase()) return i + 1; } throw new Error('#N/A'); };
  FN.INDEX = function (a) { var t = a[0], r = num(a[1]), c = a.length > 2 ? num(a[2]) : 1; if (!Array.isArray(t[0])) return t[r - 1]; return t[r - 1][c - 1]; };
  FN.XLOOKUP = function (a) { var L = flat([a[1]]), R = flat([a[2]]); for (var i = 0; i < L.length; i++) { if (String(L[i]).toLowerCase() === String(a[0]).toLowerCase()) return R[i]; } if (a.length > 3) return a[3]; throw new Error('#N/A'); };
  FN.DATE = function (a) { return Math.round(Date.UTC(num(a[0]), num(a[1]) - 1, num(a[2])) / 86400000) + 25569; };
  FN.YEAR = function (a) { return serialDate(num(a[0])).getUTCFullYear(); };
  FN.MONTH = function (a) { return serialDate(num(a[0])).getUTCMonth() + 1; };
  FN.DAY = function (a) { return serialDate(num(a[0])).getUTCDate(); };
  FN.DAYS = function (a) { return num(a[0]) - num(a[1]); };

  function tokenize(s) {
    var t = [], i = 0, m;
    while (i < s.length) {
      var c = s[i];
      if (/\s/.test(c)) { i++; continue; }
      if (c === '"') { var j = i + 1, o = ''; while (j < s.length) { if (s[j] === '"') { if (s[j + 1] === '"') { o += '"'; j += 2; continue; } break; } o += s[j++]; } if (j >= s.length) throw new Error('#NAME?'); t.push({ k: 's', v: o }); i = j + 1; continue; }
      m = /^(>=|<=|<>)/.exec(s.slice(i, i + 2)); if (m) { t.push({ k: 'o', v: m[1] }); i += 2; continue; }
      if ('+-*/^&=<>(),:%'.indexOf(c) >= 0) { t.push({ k: 'o', v: c }); i++; continue; }
      m = /^\d+\.?\d*(?:[eE][+-]?\d+)?|^\.\d+/.exec(s.slice(i)); if (m) { t.push({ k: 'n', v: parseFloat(m[0]) }); i += m[0].length; continue; }
      m = /^\$?[A-Za-z]{1,2}\$?\d+/.exec(s.slice(i)); if (m && !/^[A-Za-z]/.test(s.slice(i + m[0].length, i + m[0].length + 1))) { t.push({ k: 'c', v: m[0].replace(/\$/g, '').toUpperCase() }); i += m[0].length; continue; }
      m = /^[A-Za-z_][A-Za-z0-9_.]*/.exec(s.slice(i)); if (m) { t.push({ k: 'f', v: m[0].toUpperCase() }); i += m[0].length; continue; }
      throw new Error('#NAME?');
    }
    return t;
  }
  function colN(L) { var n = 0; for (var i = 0; i < L.length; i++) n = n * 26 + (L.charCodeAt(i) - 64); return n - 1; }
  function parseRef(r) { var m = /^([A-Z]+)(\d+)$/.exec(r); return { c: colN(m[1]), r: +m[2] - 1 }; }

  /* grid: array of rows, each an array of raw values (numbers, strings, '' or "2026-01-05" dates stay strings) */
  function evaluate(formula, grid) {
    var src = String(formula).trim();
    if (src[0] !== '=') throw new Error('NOFORMULA');
    var toks = tokenize(src.slice(1)), p = 0;
    function cell(ref) { var q = parseRef(ref), row = grid[q.r]; var v = row ? row[q.c] : ''; return v === undefined ? '' : v; }
    function peek() { return toks[p]; }
    function eat(v) { var t = toks[p]; if (t && t.k === 'o' && t.v === v) { p++; return true; } return false; }
    function cmp() {
      var l = concat();
      for (;;) { var t = peek(); if (t && t.k === 'o' && ['=', '<>', '<', '>', '<=', '>='].indexOf(t.v) >= 0) { p++; var r = concat(); l = compare(t.v, l, r); } else return l; }
    }
    function compare(op, a, b) {
      if (typeof a === 'string' && typeof b === 'string') { a = a.toLowerCase(); b = b.toLowerCase(); }
      return op === '=' ? a === b : op === '<>' ? a !== b : op === '<' ? a < b : op === '>' ? a > b : op === '<=' ? a <= b : a >= b;
    }
    function concat() { var l = add(); while (eat('&')) { l = String(l) + String(add()); } return l; }
    function add() { var l = mul(); for (;;) { if (eat('+')) l = num(l) + num(mul()); else if (eat('-')) l = num(l) - num(mul()); else return l; } }
    function mul() { var l = pow(); for (;;) { if (eat('*')) l = num(l) * num(pow()); else if (eat('/')) { var d = num(pow()); if (d === 0) throw new Error('#DIV/0!'); l = num(l) / d; } else return l; } }
    function pow() { var l = unary(); while (eat('^')) l = Math.pow(num(l), num(unary())); return l; }
    function unary() { if (eat('-')) return -num(unary()); if (eat('+')) return unary(); var v = atom(); while (eat('%')) v = num(v) / 100; return v; }
    function atom() {
      var t = toks[p++];
      if (!t) throw new Error('#NAME?');
      if (t.k === 'n') return t.v;
      if (t.k === 's') { var ds = dateSerial(t.v); return t.v; }
      if (t.k === 'o' && t.v === '(') { var v = cmp(); if (!eat(')')) throw new Error('#NAME?'); return v; }
      if (t.k === 'c') {
        if (eat(':')) { var e = toks[p++]; if (!e || e.k !== 'c') throw new Error('#NAME?'); var a = parseRef(t.v), b = parseRef(e.v), out = []; for (var r = Math.min(a.r, b.r); r <= Math.max(a.r, b.r); r++) { var row = []; for (var c = Math.min(a.c, b.c); c <= Math.max(a.c, b.c); c++) { var x = grid[r] ? grid[r][c] : ''; row.push(x === undefined ? '' : x); } out.push(row); } return out; }
        var cv = cell(t.v); return cv;
      }
      if (t.k === 'f') {
        if (t.v === 'TRUE') return true;
        if (t.v === 'FALSE') return false;
        if (!eat('(')) throw new Error('#NAME?');
        var fn = FN[t.v]; if (!fn) throw new Error('#NAME?');
        var args = [];
        if (!eat(')')) { for (;;) { args.push(cmp()); if (eat(',')) continue; if (eat(')')) break; throw new Error('#NAME?'); } }
        if (t.v === 'IF') return args[0] ? args[1] : (args.length > 2 ? args[2] : false);
        return fn(args);
      }
      throw new Error('#NAME?');
    }
    var res = cmp();
    if (p < toks.length) throw new Error('#NAME?');
    if (Array.isArray(res)) res = res[0][0];
    return res;
  }
  /* which functions does a formula use? */
  function usedFns(formula) { var o = []; try { tokenize(String(formula).slice(1)).forEach(function (t, i, a) { if (t.k === 'f' && a[i + 1] && a[i + 1].v === '(' && o.indexOf(t.v) < 0) o.push(t.v); }); } catch (e) { } return o; }
  function same(a, b) {
    if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) < 1e-6 * Math.max(1, Math.abs(b));
    if (typeof a === 'boolean' || typeof b === 'boolean') return a === b;
    return String(a) === String(b);
  }
  root.CCFormula = { evaluate: evaluate, usedFns: usedFns, same: same, FUNCTIONS: Object.keys(FN), dateSerial: dateSerial };
  if (typeof module !== 'undefined') module.exports = root.CCFormula;
})(typeof window !== 'undefined' ? window : globalThis);
