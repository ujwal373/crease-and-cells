/**
 * Character creator overlay.
 * Call initCreator() once at startup to wire DOM events.
 * Call openCreator() to show the overlay; closeCreator() to hide it.
 */

import { drawCharacter } from './character';
import { saveAppearance } from './api';
import type { Appearance } from './types';

export type OnSaveFn = (appearance: Appearance) => void;

// ── Module state ─────────────────────────────────────────────────────────────

let _playerId = '';
let _onSave: OnSaveFn = () => undefined;
let _draft: Appearance = {
  display_name: 'Ujwal Mojidra',
  body_type:    'medium',
  skin_tone:    'medium',
  hair_style:   'short',
  hair_colour:  'black',
};

// ── DOM helpers ───────────────────────────────────────────────────────────────

function _el<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

function _setSelectValue(id: string, value: string): void {
  const el = _el<HTMLSelectElement>(id);
  if (el) el.value = value;
}

// ── Rendering ─────────────────────────────────────────────────────────────────

function _redrawPreview(): void {
  const canvas = _el<HTMLCanvasElement>('creator-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  drawCharacter(ctx, canvas.width, canvas.height, _draft);
}

// ── Update draft from current form values ─────────────────────────────────────

function _syncDraftFromForm(): void {
  const name     = _el<HTMLInputElement>('creator-name');
  const bodyType = _el<HTMLSelectElement>('creator-body-type');
  const skinTone = _el<HTMLSelectElement>('creator-skin-tone');
  const hairSty  = _el<HTMLSelectElement>('creator-hair-style');
  const hairCol  = _el<HTMLSelectElement>('creator-hair-colour');

  if (name)     _draft.display_name = name.value;
  if (bodyType) _draft.body_type    = bodyType.value;
  if (skinTone) _draft.skin_tone    = skinTone.value;
  if (hairSty)  _draft.hair_style   = hairSty.value;
  if (hairCol)  _draft.hair_colour  = hairCol.value;

  _redrawPreview();
}

// ── Save ──────────────────────────────────────────────────────────────────────

async function _handleSave(): Promise<void> {
  const saveBtn = _el<HTMLButtonElement>('btn-creator-save');
  const errorEl = _el<HTMLElement>('creator-error');

  if (saveBtn) saveBtn.disabled = true;
  if (errorEl) errorEl.classList.add('hidden');

  try {
    const saved = await saveAppearance(_playerId, {
      display_name: _draft.display_name,
      body_type:    _draft.body_type,
      skin_tone:    _draft.skin_tone,
      hair_style:   _draft.hair_style,
      hair_colour:  _draft.hair_colour,
    });
    try { localStorage.setItem('cc_creator_done', '1'); } catch { /* ignore */ }
    _onSave(saved);
    closeCreator();
  } catch (err: unknown) {
    if (saveBtn) saveBtn.disabled = false;
    if (errorEl) {
      const msg = err instanceof Error ? err.message : 'Failed to save. Try again.';
      errorEl.textContent = msg;
      errorEl.classList.remove('hidden');
    }
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

export function closeCreator(): void {
  _el('creator-overlay')?.classList.add('hidden');
}

export function openCreator(
  playerId: string,
  currentAppearance: Appearance | undefined,
  isFirstVisit: boolean,
  onSave: OnSaveFn,
): void {
  _playerId = playerId;
  _onSave   = onSave;

  // Seed the draft with either the saved appearance or sensible defaults
  _draft = currentAppearance
    ? { ...currentAppearance, display_name: currentAppearance.display_name || 'Ujwal Mojidra' }
    : { display_name: 'Ujwal Mojidra', body_type: 'medium', skin_tone: 'medium', hair_style: 'short', hair_colour: 'black' };

  // Populate form controls
  const nameInput = _el<HTMLInputElement>('creator-name');
  if (nameInput) nameInput.value = _draft.display_name;
  _setSelectValue('creator-body-type',  _draft.body_type);
  _setSelectValue('creator-skin-tone',  _draft.skin_tone);
  _setSelectValue('creator-hair-style', _draft.hair_style);
  _setSelectValue('creator-hair-colour', _draft.hair_colour);

  // Adjust cancel/skip label
  const cancelBtn = _el<HTMLButtonElement>('btn-creator-cancel');
  if (cancelBtn) cancelBtn.textContent = isFirstVisit ? 'Skip' : 'Cancel';

  // Clear any previous error
  const errorEl = _el('creator-error');
  if (errorEl) errorEl.classList.add('hidden');

  // Show the overlay and draw the initial preview
  _el('creator-overlay')?.classList.remove('hidden');
  _redrawPreview();
}

/** Wire all DOM event listeners. Call once during init(). */
export function initCreator(): void {
  const ids = [
    'creator-name',
    'creator-body-type',
    'creator-skin-tone',
    'creator-hair-style',
    'creator-hair-colour',
  ];
  for (const id of ids) {
    _el(id)?.addEventListener('input',  _syncDraftFromForm);
    _el(id)?.addEventListener('change', _syncDraftFromForm);
  }

  _el('btn-creator-save')?.addEventListener('click', () => { void _handleSave(); });
  _el('btn-creator-cancel')?.addEventListener('click', closeCreator);

  // Clicking the backdrop closes the creator
  _el('creator-overlay')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeCreator();
  });
}
