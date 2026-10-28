import type {
  Mission,
  SubmitResult,
  HintResult,
  CoachResult,
  PreviewResult,
  WalletData,
  StoreItem,
  BuyResult,
  ApiError,
} from './types';

// In development, Vite proxies /api/* to localhost:8000.
// In production, set VITE_API_URL to the backend origin.
const BASE: string = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

export function isApiError(value: unknown): value is ApiError {
  return (
    typeof value === 'object' &&
    value !== null &&
    'kind' in value &&
    typeof (value as Record<string, unknown>)['kind'] === 'string'
  );
}

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE + url, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
  } catch {
    const err: ApiError = { kind: 'server_down', message: 'Cannot reach the server. Is the backend running?' };
    throw err;
  }

  if (response.status === 429) {
    const err: ApiError = { kind: 'rate_limit', message: "You're sending requests too fast. Please wait a moment." };
    throw err;
  }

  if (response.status === 400) {
    let msg = 'Invalid request.';
    try {
      const body = await response.json() as { detail?: { error?: string } };
      if (body.detail?.error) msg = body.detail.error;
    } catch { /* ignore JSON parse failure */ }
    const err: ApiError = { kind: 'invalid_input', message: msg };
    throw err;
  }

  if (!response.ok) {
    const err: ApiError = {
      kind: 'unknown',
      status: response.status,
      message: `Server returned ${response.status}.`,
    };
    throw err;
  }

  return response.json() as Promise<T>;
}

export function fetchMission(playerId: string, name?: string): Promise<Mission> {
  const params = new URLSearchParams({ player_id: playerId });
  if (name) params.set('name', name);
  return apiFetch<Mission>(`/api/mission?${params.toString()}`);
}

export function submitAnswer(
  playerId: string,
  missionId: string,
  formula: string,
): Promise<SubmitResult> {
  return apiFetch<SubmitResult>(`/api/mission/${encodeURIComponent(missionId)}/submit`, {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId, formula }),
  });
}

export function getHint(playerId: string, missionId: string): Promise<HintResult> {
  return apiFetch<HintResult>(`/api/mission/${encodeURIComponent(missionId)}/hint`, {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId }),
  });
}

export function askCoach(
  playerId: string,
  missionId: string,
  message: string,
): Promise<CoachResult> {
  return apiFetch<CoachResult>(`/api/mission/${encodeURIComponent(missionId)}/coach`, {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId, message }),
  });
}

export function previewFormula(
  playerId: string,
  missionId: string,
  formula: string,
): Promise<PreviewResult> {
  return apiFetch<PreviewResult>(`/api/mission/${encodeURIComponent(missionId)}/preview`, {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId, formula }),
  });
}

export function getWallet(playerId: string): Promise<WalletData> {
  return apiFetch<WalletData>(`/api/wallet?player_id=${encodeURIComponent(playerId)}`);
}

export function listStore(playerId: string): Promise<StoreItem[]> {
  return apiFetch<StoreItem[]>(`/api/store?player_id=${encodeURIComponent(playerId)}`);
}

export function buyItem(playerId: string, itemId: string): Promise<BuyResult> {
  return apiFetch<BuyResult>('/api/store/buy', {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId, item_id: itemId }),
  });
}
