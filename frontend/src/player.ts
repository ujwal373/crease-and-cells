export function getPlayerId(): string {
  try {
    const stored = localStorage.getItem('cc_player_id');
    if (stored) return stored;
    const id = crypto.randomUUID();
    localStorage.setItem('cc_player_id', id);
    return id;
  } catch {
    // localStorage unavailable (private browsing restrictions, etc.)
    return crypto.randomUUID();
  }
}
