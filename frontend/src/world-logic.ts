/** Pure world-logic: map building, collision, zone unlock. No Phaser dependency. */

export const TILE = {
  GRASS:  0,
  WALL:   1,
  PATH:   2,
  COURT:  3,
} as const;

export type TileKind = (typeof TILE)[keyof typeof TILE];

export const MAP_COLS   = 40;
export const MAP_ROWS   = 20;
export const TILE_SIZE  = 32;
export const ZONE_SPLIT = 20; // column of the divider wall between zones

export interface NpcDef {
  id: string;
  name: string;
  zone: 'nets' | 'clubhouse';
  col: number;
  row: number;
}

export const NPCS: readonly NpcDef[] = [
  { id: 'coach_rao',   name: 'Coach Rao',   zone: 'nets',      col: 12, row: 9 },
  { id: 'scout_mehta', name: 'Scout Mehta', zone: 'clubhouse', col: 30, row: 9 },
] as const;

export const PLAYER_START = { col: 3, row: 15 };

/** Returns true for tiles the player can walk on. */
export function isTileWalkable(tile: number): boolean {
  return tile === TILE.GRASS || tile === TILE.PATH || tile === TILE.COURT;
}

/** Returns true when the named zone is accessible at the given player level. */
export function isZoneUnlocked(zone: 'nets' | 'clubhouse', playerLevel: number): boolean {
  return zone === 'nets' || (zone === 'clubhouse' && playerLevel >= 2);
}

function _getTile(r: number, c: number, clubUnlocked: boolean): TileKind {
  // Outer boundary
  if (r === 0 || r === MAP_ROWS - 1 || c === 0 || c === MAP_COLS - 1) return TILE.WALL;

  // Zone divider: door gap at rows 8-10 if club is unlocked
  if (c === ZONE_SPLIT) {
    return r >= 8 && r <= 10 && clubUnlocked ? TILE.PATH : TILE.WALL;
  }

  // Club House building (cols 23-36, rows 4-15)
  if (c >= 23 && c <= 36 && r >= 4 && r <= 15) {
    const outerWall = r === 4 || r === 15 || c === 23 || c === 36;
    if (outerWall) {
      // Entrance in the west wall at rows 8-10
      return c === 23 && r >= 8 && r <= 10 ? TILE.PATH : TILE.WALL;
    }
    return TILE.PATH; // building interior floor
  }

  // Cricket pitch in the Nets zone (cols 6-13, rows 6-13)
  if (c >= 6 && c <= 13 && r >= 6 && r <= 13) return TILE.COURT;

  return TILE.GRASS;
}

/** Builds the full tile map for a given player level. */
export function buildMap(playerLevel: number): TileKind[][] {
  const clubUnlocked = isZoneUnlocked('clubhouse', playerLevel);
  const map: TileKind[][] = [];
  for (let r = 0; r < MAP_ROWS; r++) {
    map[r] = [];
    for (let c = 0; c < MAP_COLS; c++) {
      map[r][c] = _getTile(r, c, clubUnlocked);
    }
  }
  return map;
}
