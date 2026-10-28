export interface Mission {
  id: string;
  level: number;
  zone: string;
  npc: string;
  title: string;
  story: string;
  task: string;
  hints_available: number;
  sheet_name: string;
  sheet: (string | number | null)[][];
  reward: { coins: number; xp: number };
  done?: boolean;
  message?: string;
}

export interface SubmitResult {
  passed: boolean;
  reason: string;
  your_value?: unknown;
  already_completed?: boolean;
  coins_awarded?: number;
  no_hint_bonus?: number;
  xp_awarded?: number;
  wallet?: WalletData;
  next_mission?: { id: string; title: string } | null;
}

export interface HintResult {
  hint: string;
  hint_number: number;
  of: number;
  no_hint_bonus_lost: boolean;
}

export interface CoachResult {
  hint?: string;
  hint_number?: number;
  of?: number;
  no_hint_bonus_lost?: boolean;
  blocked?: boolean;
  reply?: string;
}

export interface PreviewResult {
  value?: unknown;
  error?: string;
}

export interface WalletData {
  id: string;
  name: string;
  coins: number;
  xp: number;
  level: number;
  outfit: Record<string, string>;
}

export interface StoreItem {
  id: string;
  name: string;
  slot: string;
  tier: string;
  price: number;
  owned: boolean;
}

export interface BuyResult {
  ok: boolean;
  reason?: string;
  item?: string;
  wallet?: WalletData;
}

export interface ApiError {
  kind: 'rate_limit' | 'server_down' | 'invalid_input' | 'unknown';
  message?: string;
  status?: number;
}
