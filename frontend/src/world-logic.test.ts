import { describe, it, expect } from 'vitest';
import {
  TILE,
  isTileWalkable,
  isZoneUnlocked,
  buildMap,
  MAP_ROWS,
  MAP_COLS,
  ZONE_SPLIT,
  PLAYER_START,
  NPCS,
} from './world-logic';

describe('isTileWalkable', () => {
  it('grass is walkable', () => { expect(isTileWalkable(TILE.GRASS)).toBe(true); });
  it('path is walkable',  () => { expect(isTileWalkable(TILE.PATH)).toBe(true); });
  it('court is walkable', () => { expect(isTileWalkable(TILE.COURT)).toBe(true); });
  it('wall is not walkable', () => { expect(isTileWalkable(TILE.WALL)).toBe(false); });
  it('unknown tile is not walkable', () => { expect(isTileWalkable(99)).toBe(false); });
});

describe('isZoneUnlocked', () => {
  it('nets is always unlocked',           () => { expect(isZoneUnlocked('nets',      1)).toBe(true); });
  it('nets is unlocked at level 2',       () => { expect(isZoneUnlocked('nets',      2)).toBe(true); });
  it('clubhouse locked below level 2',    () => { expect(isZoneUnlocked('clubhouse', 1)).toBe(false); });
  it('clubhouse unlocked at level 2',     () => { expect(isZoneUnlocked('clubhouse', 2)).toBe(true); });
  it('clubhouse unlocked above level 2',  () => { expect(isZoneUnlocked('clubhouse', 5)).toBe(true); });
});

describe('buildMap', () => {
  it('produces correct dimensions', () => {
    const m = buildMap(1);
    expect(m.length).toBe(MAP_ROWS);
    expect(m[0].length).toBe(MAP_COLS);
  });

  it('outer boundary is walls', () => {
    const m = buildMap(1);
    for (let c = 0; c < MAP_COLS; c++) {
      expect(m[0][c]).toBe(TILE.WALL);
      expect(m[MAP_ROWS - 1][c]).toBe(TILE.WALL);
    }
    for (let r = 0; r < MAP_ROWS; r++) {
      expect(m[r][0]).toBe(TILE.WALL);
      expect(m[r][MAP_COLS - 1]).toBe(TILE.WALL);
    }
  });

  it('zone divider is wall when club is locked', () => {
    const m = buildMap(1);
    for (let r = 1; r < MAP_ROWS - 1; r++) {
      expect(m[r][ZONE_SPLIT]).toBe(TILE.WALL);
    }
  });

  it('zone divider door rows are path when club is unlocked', () => {
    const m = buildMap(2);
    for (const r of [8, 9, 10]) {
      expect(m[r][ZONE_SPLIT]).toBe(TILE.PATH);
    }
  });

  it('zone divider non-door rows stay wall when club is unlocked', () => {
    const m = buildMap(2);
    expect(m[5][ZONE_SPLIT]).toBe(TILE.WALL);
    expect(m[15][ZONE_SPLIT]).toBe(TILE.WALL);
  });

  it('player start position is walkable', () => {
    const m = buildMap(1);
    expect(isTileWalkable(m[PLAYER_START.row][PLAYER_START.col])).toBe(true);
  });

  it('nets NPC position is walkable', () => {
    const npc = NPCS.find(n => n.id === 'coach_rao')!;
    const m = buildMap(1);
    expect(isTileWalkable(m[npc.row][npc.col])).toBe(true);
  });

  it('clubhouse NPC position is walkable when unlocked', () => {
    const npc = NPCS.find(n => n.id === 'scout_mehta')!;
    const m = buildMap(2);
    expect(isTileWalkable(m[npc.row][npc.col])).toBe(true);
  });

  it('cricket pitch area is court tiles', () => {
    const m = buildMap(1);
    expect(m[8][10]).toBe(TILE.COURT);
    expect(m[9][9]).toBe(TILE.COURT);
  });

  it('club house building entrance is path when unlocked', () => {
    const m = buildMap(2);
    expect(m[9][23]).toBe(TILE.PATH); // west wall entrance
  });

  it('club house interior is path when unlocked', () => {
    const m = buildMap(2);
    expect(m[9][30]).toBe(TILE.PATH); // interior floor
  });
});
