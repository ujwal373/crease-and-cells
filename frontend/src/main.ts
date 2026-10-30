import './style.css';
import { getPlayerId } from './player';
import {
  fetchMission,
  submitAnswer,
  getHint,
  askCoach,
  previewFormula,
  getWallet,
  listStore,
  buyItem,
  isApiError,
} from './api';
import { renderGrid } from './grid';
import { initCreator, openCreator } from './creator';
import type { Mission, WalletData, StoreItem, Appearance } from './types';
import type { NpcDef } from './world';

// ── DOM helpers ───────────────────────────────────────────────────────────────

function el<T extends HTMLElement = HTMLElement>(id: string): T {
  const found = document.getElementById(id) as T | null;
  if (!found) throw new Error(`Element #${id} not found`);
  return found;
}

function show(id: string): void {
  el(id).classList.remove('hidden');
}

function hide(id: string): void {
  el(id).classList.add('hidden');
}

function setText(id: string, text: string): void {
  el(id).textContent = text;
}

// ── Module-level state ────────────────────────────────────────────────────────

let playerId = '';
let currentMission: Mission | null = null;
let currentAppearance: Appearance | undefined = undefined;
let previewTimer: ReturnType<typeof setTimeout> | null = null;
let submitting = false;
let worldHandle: { destroy: () => void } | null = null;
let worldActive = false;

// DOM refs — assigned in init() before any other function runs
let formulaInput!: HTMLInputElement;
let submitBtn!: HTMLButtonElement;
let hintBtn!: HTMLButtonElement;
let coachInput!: HTMLInputElement;
let coachBtn!: HTMLButtonElement;

// ── Error handling ─────────────────────────────────────────────────────────────

function errorMessage(err: unknown): string {
  if (isApiError(err)) {
    switch (err.kind) {
      case 'rate_limit':   return err.message ?? "You're sending requests too fast.";
      case 'server_down':  return err.message ?? 'Cannot reach the server. Is the backend running?';
      case 'invalid_input': return err.message ?? 'Invalid request.';
      case 'unknown':      return err.message ?? 'An unexpected error occurred.';
    }
  }
  return 'An unexpected error occurred.';
}

// ── Wallet ─────────────────────────────────────────────────────────────────────

function renderWallet(wallet: WalletData): void {
  setText('stat-coins', `${wallet.coins} coins`);
  setText('stat-xp', `${wallet.xp} XP`);
  setText('stat-level', `Lv ${wallet.level}`);
  if (wallet.appearance) currentAppearance = wallet.appearance;
}

function handleAppearanceSaved(appearance: Appearance): void {
  currentAppearance = appearance;
  void getWallet(playerId).then(renderWallet).catch(() => undefined);
}

// ── Mission ────────────────────────────────────────────────────────────────────

function renderMission(mission: Mission): void {
  setText('npc-badge', mission.npc);
  setText('mission-title', mission.title);
  setText('mission-story', mission.story);
  setText('mission-task', mission.task);
  setText('sheet-name', mission.sheet_name);
  renderGrid(el<HTMLTableElement>('sheet-table'), mission.sheet);
  hide('hint-area');
  hide('result-panel');
  hide('coach-reply');
  hide('preview-status');
  formulaInput.value = '';
  updateSubmitState();
}

function showAllDone(message: string): void {
  const panel = el('mission-panel');
  panel.innerHTML = '';
  const h2 = document.createElement('h2');
  h2.className = 'all-done';
  h2.textContent = 'All done!';
  const p = document.createElement('p');
  p.style.cssText = 'text-align:center;padding:40px 20px;color:var(--text-muted)';
  p.textContent = message;
  panel.appendChild(h2);
  panel.appendChild(p);
  hide('grid-panel');
}

// ── Submit ─────────────────────────────────────────────────────────────────────

function updateSubmitState(): void {
  submitBtn.disabled = submitting || formulaInput.value.trim().length === 0;
}

function showResult(kind: 'pass' | 'fail' | 'error', text: string): void {
  const panel = el('result-panel');
  panel.innerHTML = '';
  panel.className = `result-panel result-${kind}`;
  const msg = document.createElement('div');
  msg.className = 'result-message';
  msg.textContent = text;
  panel.appendChild(msg);
  panel.classList.remove('hidden');
}

function friendlyReason(reason: string): string {
  if (reason === 'wrong_value') return 'The result is not quite right. Check your formula.';
  if (reason === 'formula_error') return 'Your formula has a syntax error.';
  if (reason === 'empty_formula') return 'No formula entered.';
  if (reason.startsWith('missing_function:'))
    return reason.replace('missing_function:', 'Requires function:').trim();
  if (reason === 'missing_function') return 'The task requires a specific function. Check the task description.';
  return reason;
}

async function handleSubmit(): Promise<void> {
  if (!currentMission) return;
  const formula = formulaInput.value.trim();
  if (!formula) return;

  submitting = true;
  updateSubmitState();
  hide('result-panel');

  try {
    const result = await submitAnswer(playerId, currentMission.id, formula);

    if (result.passed) {
      const parts: string[] = ['Correct!'];
      if (result.coins_awarded != null) {
        parts.push(`+${result.coins_awarded} coins`);
        if (result.no_hint_bonus && result.no_hint_bonus > 0)
          parts.push(`(including +${result.no_hint_bonus} no-hint bonus)`);
      }
      if (result.xp_awarded != null) parts.push(`+${result.xp_awarded} XP`);
      if (result.already_completed) parts.push('(already completed, no reward)');

      showResult('pass', parts.join('  '));

      if (result.wallet) renderWallet(result.wallet);

      const nextBtn = document.createElement('button');
      nextBtn.className = 'btn-primary next-btn';
      nextBtn.textContent = result.next_mission
        ? `Next: ${result.next_mission.title}`
        : 'Continue';
      nextBtn.addEventListener('click', () => { void loadNextMission(); });
      el('result-panel').appendChild(nextBtn);
    } else {
      showResult('fail', friendlyReason(result.reason));
    }
  } catch (err) {
    showResult('error', errorMessage(err));
  } finally {
    submitting = false;
    updateSubmitState();
  }
}

async function loadNextMission(): Promise<void> {
  show('loading-overlay');
  try {
    const [mission, wallet] = await Promise.all([
      fetchMission(playerId),
      getWallet(playerId),
    ]);
    renderWallet(wallet);
    if (mission.done) {
      showAllDone(mission.message ?? 'All missions complete. New zones coming soon!');
    } else {
      currentMission = mission;
      renderMission(mission);
      show('grid-panel');
    }
  } catch (err) {
    showResult('error', errorMessage(err));
  } finally {
    hide('loading-overlay');
  }
}

// ── Hint ──────────────────────────────────────────────────────────────────────

async function handleHint(): Promise<void> {
  if (!currentMission) return;

  hintBtn.disabled = true;
  try {
    const result = await getHint(playerId, currentMission.id);
    const area = el('hint-area');
    area.innerHTML = '';
    const label = document.createElement('div');
    label.className = 'hint-label';
    label.textContent = `Hint ${result.hint_number} of ${result.of}`;
    const text = document.createElement('p');
    text.textContent = result.hint;
    area.appendChild(label);
    area.appendChild(text);
    area.classList.remove('hidden');
  } catch (err) {
    showResult('error', errorMessage(err));
  } finally {
    hintBtn.disabled = false;
  }
}

// ── Preview ────────────────────────────────────────────────────────────────────

async function runPreview(formula: string): Promise<void> {
  if (!currentMission) return;
  try {
    const result = await previewFormula(playerId, currentMission.id, formula);
    const statusEl = el('preview-status');
    if (result.error) {
      statusEl.textContent = `Error: ${result.error}`;
      statusEl.className = 'preview-status preview-error';
    } else {
      statusEl.textContent = `= ${String(result.value ?? '')}`;
      statusEl.className = 'preview-status preview-value';
    }
    statusEl.classList.remove('hidden');
  } catch {
    hide('preview-status');
  }
}

// ── Coach ──────────────────────────────────────────────────────────────────────

async function handleCoach(): Promise<void> {
  if (!currentMission) return;
  const message = coachInput.value.trim();
  if (!message) return;

  coachBtn.disabled = true;
  try {
    const result = await askCoach(playerId, currentMission.id, message);
    const replyEl = el('coach-reply');
    replyEl.textContent = result.blocked
      ? (result.reply ?? 'Message blocked.')
      : (result.hint ?? 'No response from Coach.');
    replyEl.classList.remove('hidden');
    coachInput.value = '';
  } catch (err) {
    const replyEl = el('coach-reply');
    replyEl.textContent = errorMessage(err);
    replyEl.classList.remove('hidden');
  } finally {
    coachBtn.disabled = false;
  }
}

// ── Store ──────────────────────────────────────────────────────────────────────

async function openStore(): Promise<void> {
  try {
    const items = await listStore(playerId);
    renderStoreItems(items);
    show('store-overlay');
  } catch (err) {
    alert(errorMessage(err));
  }
}

function renderStoreItems(items: StoreItem[]): void {
  const listEl = el('store-list');
  listEl.innerHTML = '';

  for (const item of items) {
    const li = document.createElement('li');
    li.className = 'store-item';

    const info = document.createElement('div');
    info.className = 'store-item-info';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'item-name';
    nameSpan.textContent = item.name;

    const metaSpan = document.createElement('span');
    metaSpan.className = 'item-meta';
    metaSpan.textContent = `${item.slot} · ${item.tier} · ${item.price} coins`;

    info.appendChild(nameSpan);
    info.appendChild(metaSpan);

    const btn = document.createElement('button');
    if (item.owned) {
      btn.textContent = 'Owned';
      btn.disabled = true;
      btn.className = 'btn-secondary';
    } else {
      btn.textContent = `Buy (${item.price})`;
      btn.className = 'btn-primary';
      btn.addEventListener('click', () => { void handleBuy(item.id, item.price, btn); });
    }

    li.appendChild(info);
    li.appendChild(btn);
    listEl.appendChild(li);
  }
}

async function handleBuy(itemId: string, price: number, btn: HTMLButtonElement): Promise<void> {
  btn.disabled = true;
  try {
    const result = await buyItem(playerId, itemId);
    if (result.ok) {
      if (result.wallet) renderWallet(result.wallet);
      btn.textContent = 'Owned';
    } else {
      btn.textContent = result.reason ?? 'Failed';
      setTimeout(() => {
        btn.textContent = `Buy (${price})`;
        btn.disabled = false;
      }, 2000);
    }
  } catch (err) {
    btn.textContent = 'Error';
    setTimeout(() => {
      btn.textContent = `Buy (${price})`;
      btn.disabled = false;
    }, 2000);
    console.error('Purchase failed:', errorMessage(err));
  }
}

// ── World ─────────────────────────────────────────────────────────────────

function _openMissionPanel(): void {
  const layout = document.getElementById('main-layout');
  const backBar = document.getElementById('world-back-bar');
  if (layout) layout.classList.add('mission-visible');
  if (backBar) backBar.classList.remove('hidden');
}

function _closeMissionPanel(): void {
  const layout = document.getElementById('main-layout');
  const backBar = document.getElementById('world-back-bar');
  if (layout) layout.classList.remove('mission-visible');
  if (backBar) backBar.classList.add('hidden');
}

function _handleNpcInteract(_npc: NpcDef): void {
  _openMissionPanel();
}

async function openWorld(): Promise<void> {
  if (worldActive) return;
  worldActive = true;

  const app = document.getElementById('app');
  app?.classList.add('world-active');

  document.getElementById('world-section')?.classList.remove('hidden');
  document.getElementById('main-layout')?.classList.remove('mission-visible');
  document.getElementById('world-back-bar')?.classList.add('hidden');
  el('btn-world').textContent = 'Close World';

  if (!worldHandle) {
    const container = document.getElementById('world-canvas-container');
    if (!container) return;
    // Lazy import keeps Phaser out of the initial bundle
    const { initWorld } = await import('./world');
    const level = (() => {
      const lvText = document.getElementById('stat-level')?.textContent ?? 'Lv 1';
      return parseInt(lvText.replace('Lv ', ''), 10) || 1;
    })();
    worldHandle = await initWorld(
      container,
      { appearance: currentAppearance ?? { display_name: '', body_type: 'medium', skin_tone: 'medium', hair_style: 'short', hair_colour: 'black' }, playerLevel: level },
      _handleNpcInteract,
    );
  }
}

function closeWorld(): void {
  if (!worldActive) return;
  worldActive = false;

  const app = document.getElementById('app');
  app?.classList.remove('world-active');

  document.getElementById('world-section')?.classList.add('hidden');
  const layout = document.getElementById('main-layout');
  if (layout) {
    layout.classList.remove('mission-visible');
  }
  document.getElementById('world-back-bar')?.classList.add('hidden');
  el('btn-world').textContent = 'Open World';
}

// ── Init ──────────────────────────────────────────────────────────────────────

function showInitError(message: string): void {
  const div = document.createElement('div');
  div.className = 'init-error';

  const h2 = document.createElement('h2');
  h2.textContent = 'Could not load the game';

  const p = document.createElement('p');
  p.textContent = message;

  const retryBtn = document.createElement('button');
  retryBtn.className = 'btn-primary';
  retryBtn.textContent = 'Retry';
  retryBtn.addEventListener('click', () => { location.reload(); });

  div.appendChild(h2);
  div.appendChild(p);
  div.appendChild(retryBtn);

  document.body.innerHTML = '';
  document.body.appendChild(div);
}

async function init(): Promise<void> {
  playerId = getPlayerId();

  formulaInput = el<HTMLInputElement>('formula-input');
  submitBtn    = el<HTMLButtonElement>('btn-submit');
  hintBtn      = el<HTMLButtonElement>('btn-hint');
  coachInput   = el<HTMLInputElement>('coach-input');
  coachBtn     = el<HTMLButtonElement>('btn-coach');

  initCreator();

  // Formula input: debounced preview + submit-button gate
  formulaInput.addEventListener('input', () => {
    updateSubmitState();
    const formula = formulaInput.value.trim();
    if (previewTimer !== null) clearTimeout(previewTimer);
    if (!formula) { hide('preview-status'); return; }
    previewTimer = setTimeout(() => { void runPreview(formula); }, 300);
  });

  formulaInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') void handleSubmit();
  });

  submitBtn.addEventListener('click', () => { void handleSubmit(); });
  hintBtn.addEventListener('click', () => { void handleHint(); });
  coachBtn.addEventListener('click', () => { void handleCoach(); });
  coachInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') void handleCoach();
  });

  el('btn-store').addEventListener('click', () => { void openStore(); });
  el('btn-close-store').addEventListener('click', () => { hide('store-overlay'); });
  el('store-overlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) hide('store-overlay');
  });

  el('btn-customize').addEventListener('click', () => {
    openCreator(playerId, currentAppearance, false, handleAppearanceSaved);
  });

  el('btn-world').addEventListener('click', () => {
    if (worldActive) closeWorld(); else void openWorld();
  });

  const backBtn = document.getElementById('btn-back-world');
  if (backBtn) backBtn.addEventListener('click', _closeMissionPanel);

  show('loading-overlay');

  try {
    const [mission, wallet] = await Promise.all([
      fetchMission(playerId),
      getWallet(playerId),
    ]);

    renderWallet(wallet);

    // Show character creator on first visit.
    // Server truth: appearance.display_name is non-empty only after the player
    // has saved their character. localStorage is a secondary cache so the creator
    // does not flash on repeat visits when the server is slow.
    const serverDone = !!(wallet.appearance?.display_name);
    let localDone = false;
    try { localDone = !!localStorage.getItem('cc_creator_done'); } catch { /* ignore */ }
    if (!serverDone && !localDone) {
      openCreator(playerId, wallet.appearance, true, handleAppearanceSaved);
    }

    if (mission.done) {
      showAllDone(mission.message ?? 'All missions complete. New zones coming soon!');
    } else {
      currentMission = mission;
      renderMission(mission);
    }
  } catch (err) {
    showInitError(errorMessage(err));
  } finally {
    hide('loading-overlay');
  }
}

document.addEventListener('DOMContentLoaded', () => { void init(); });
