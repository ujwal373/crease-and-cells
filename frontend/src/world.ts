/**
 * Phaser 3 open world. Lazily imported so the mission UI loads without it.
 * Call initWorld() to start; the returned handle has destroy().
 */

import { drawCharacter } from './character';
import type { Appearance } from './types';
import {
  TILE,
  TILE_SIZE,
  MAP_COLS,
  MAP_ROWS,
  ZONE_SPLIT,
  NPCS,
  PLAYER_START,
  NpcDef,
  buildMap,
  isTileWalkable,
  isZoneUnlocked,
} from './world-logic';

export type { NpcDef };

export interface WorldConfig {
  appearance: Appearance;
  playerLevel: number;
}

const TILE_COLORS: Record<number, number> = {
  [TILE.GRASS]:  0x3a6644,
  [TILE.WALL]:   0x2d3436,
  [TILE.COURT]:  0x7d6545,
  [TILE.PATH]:   0xb89a72,
};

const INTERACT_DIST = TILE_SIZE * 2.2;
const PLAYER_SPEED  = 128;

function _drawNpcCanvas(color: number): HTMLCanvasElement {
  const c = document.createElement('canvas');
  c.width = 32; c.height = 48;
  const ctx = c.getContext('2d')!;
  // Head
  ctx.fillStyle = '#e8c49a';
  ctx.beginPath(); ctx.arc(16, 10, 8, 0, Math.PI * 2); ctx.fill();
  // Body (jersey using passed colour)
  const r = (color >> 16) & 0xff;
  const g = (color >> 8)  & 0xff;
  const b =  color        & 0xff;
  ctx.fillStyle = `rgb(${r},${g},${b})`;
  ctx.fillRect(8, 18, 16, 18);
  // Trousers
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(8, 35, 7, 13);
  ctx.fillRect(17, 35, 7, 13);
  return c;
}

export async function initWorld(
  container: HTMLElement,
  config: WorldConfig,
  onNpcInteract: (npc: NpcDef) => void,
): Promise<{ destroy: () => void }> {
  // Lazy import keeps Phaser out of the initial bundle
  const Phaser = (await import('phaser') as { default: typeof import('phaser') }).default;

  const containerW = container.clientWidth  || 800;
  const containerH = container.clientHeight || 500;
  const mapData = buildMap(config.playerLevel);
  const clubUnlocked = isZoneUnlocked('clubhouse', config.playerLevel);

  class WorldScene extends Phaser.Scene {
    private player!:          Phaser.GameObjects.Image;
    private cursors!:         Phaser.Types.Input.Keyboard.CursorKeys;
    private wasd!:            Record<string, Phaser.Input.Keyboard.Key>;
    private npcObjects        = new Map<string, { x: number; y: number }>();
    private npcMarkers        = new Map<string, Phaser.GameObjects.Text>();
    private npcNameTags       = new Map<string, Phaser.GameObjects.Text>();
    private lockLabel!:       Phaser.GameObjects.Text;
    private lockLabelVisible  = false;
    private lastTriggered     = '';
    private triggerCooldown   = 0;
    private joystickBase!:    Phaser.GameObjects.Graphics;
    private joystickStick!:   Phaser.GameObjects.Graphics;
    private joystickActive    = false;
    private joystickOrigin    = { x: 0, y: 0 };
    private joystickDir       = { x: 0, y: 0 };
    private joystickPointerId = -1;

    constructor() { super({ key: 'WorldScene' }); }

    preload(): void {
      // Player texture from character renderer
      const pc = document.createElement('canvas');
      pc.width = 48; pc.height = 72;
      const pctx = pc.getContext('2d');
      if (pctx) drawCharacter(pctx, 48, 72, config.appearance);
      this.textures.addCanvas('player_tex', pc);

      // NPC textures
      this.textures.addCanvas('npc_nets', _drawNpcCanvas(0x2563eb));
      this.textures.addCanvas('npc_club', _drawNpcCanvas(0xdc2626));
    }

    create(): void {
      // ── Tile map background ──────────────────────────────────────────────
      const g = this.add.graphics().setDepth(0);
      for (let r = 0; r < MAP_ROWS; r++) {
        for (let c = 0; c < MAP_COLS; c++) {
          g.fillStyle(TILE_COLORS[mapData[r][c]] ?? 0x3a6644);
          g.fillRect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE - 1, TILE_SIZE - 1);
        }
      }

      // Zone labels
      const labelStyle = { fontSize: '11px', color: 'rgba(255,255,255,0.35)', fontFamily: 'system-ui' };
      this.add.text(10 * TILE_SIZE, 17 * TILE_SIZE, 'THE NETS', labelStyle).setDepth(1);
      this.add.text(28 * TILE_SIZE, 17 * TILE_SIZE, 'CLUB HOUSE', labelStyle).setDepth(1);

      // ── Lock indicator at zone divider ────────────────────────────────
      if (!clubUnlocked) {
        const lx = ZONE_SPLIT * TILE_SIZE + TILE_SIZE / 2;
        const ly = 9 * TILE_SIZE;
        this.add.text(lx, ly - 24, '🔒', { fontSize: '18px' }).setOrigin(0.5).setDepth(4);
        this.lockLabel = this.add.text(lx, ly + 8, 'Level 2 required', {
          fontSize: '9px', color: '#fbbf24',
          backgroundColor: '#00000099',
          padding: { x: 4, y: 2 },
        }).setOrigin(0.5).setDepth(4).setVisible(false);
      }

      // ── NPCs ─────────────────────────────────────────────────────────
      for (const npc of NPCS) {
        if (!isZoneUnlocked(npc.zone, config.playerLevel)) continue;
        const wx = npc.col * TILE_SIZE + TILE_SIZE / 2;
        const wy = npc.row * TILE_SIZE + TILE_SIZE / 2;
        const tex = npc.zone === 'nets' ? 'npc_nets' : 'npc_club';
        const sprite = this.add.image(wx, wy, tex).setDepth(5);
        sprite.setInteractive();
        sprite.on('pointerdown', () => { this._triggerNpc(npc); });

        this.npcObjects.set(npc.id, { x: wx, y: wy });

        this.npcMarkers.set(npc.id,
          this.add.text(wx, wy - 30, '!', {
            fontSize: '20px', fontStyle: 'bold', color: '#fbbf24',
            stroke: '#000', strokeThickness: 2,
          }).setOrigin(0.5).setDepth(6));

        this.npcNameTags.set(npc.id,
          this.add.text(wx, wy - 52, npc.name, {
            fontSize: '10px', color: '#fff',
            backgroundColor: '#000000bb',
            padding: { x: 4, y: 2 },
          }).setOrigin(0.5).setDepth(6).setVisible(false));
      }

      // ── Player ────────────────────────────────────────────────────────
      const sx = PLAYER_START.col * TILE_SIZE + TILE_SIZE / 2;
      const sy = PLAYER_START.row * TILE_SIZE + TILE_SIZE / 2;
      this.player = this.add.image(sx, sy, 'player_tex').setDepth(10);

      // ── Camera ────────────────────────────────────────────────────────
      this.cameras.main
        .setSize(containerW, containerH)
        .setBounds(0, 0, MAP_COLS * TILE_SIZE, MAP_ROWS * TILE_SIZE)
        .startFollow(this.player, true, 0.12, 0.12);

      // ── Keyboard ─────────────────────────────────────────────────────
      this.cursors = this.input.keyboard!.createCursorKeys();
      this.wasd = this.input.keyboard!.addKeys('W,A,S,D') as Record<string, Phaser.Input.Keyboard.Key>;

      // ── Touch joystick ────────────────────────────────────────────────
      this._initJoystick();
    }

    update(_time: number, delta: number): void {
      const dt = delta / 1000;
      let vx = 0, vy = 0;

      if (this.cursors.left.isDown  || this.wasd['A'].isDown || this.joystickDir.x < -0.3) vx = -PLAYER_SPEED;
      if (this.cursors.right.isDown || this.wasd['D'].isDown || this.joystickDir.x >  0.3) vx =  PLAYER_SPEED;
      if (this.cursors.up.isDown    || this.wasd['W'].isDown || this.joystickDir.y < -0.3) vy = -PLAYER_SPEED;
      if (this.cursors.down.isDown  || this.wasd['S'].isDown || this.joystickDir.y >  0.3) vy =  PLAYER_SPEED;

      if (vx !== 0 && vy !== 0) { vx *= 0.707; vy *= 0.707; }

      const nx = this.player.x + vx * dt;
      const ny = this.player.y + vy * dt;
      if (this._canMoveTo(nx, this.player.y)) this.player.x = nx;
      if (this._canMoveTo(this.player.x, ny)) this.player.y = ny;

      if (this.triggerCooldown > 0) this.triggerCooldown--;

      this._updateNpcProximity();
      this._updateLockTooltip();
    }

    private _canMoveTo(wx: number, wy: number): boolean {
      const hw = 14, hh = 14;
      for (const [dx, dy] of [[-hw, -hh], [hw, -hh], [-hw, hh], [hw, hh]] as const) {
        const col = Math.floor((wx + dx) / TILE_SIZE);
        const row = Math.floor((wy + dy) / TILE_SIZE);
        if (row < 0 || row >= MAP_ROWS || col < 0 || col >= MAP_COLS) return false;
        if (!isTileWalkable(mapData[row][col])) return false;
      }
      return true;
    }

    private _triggerNpc(npc: NpcDef): void {
      if (this.triggerCooldown > 0 && this.lastTriggered === npc.id) return;
      this.lastTriggered = npc.id;
      this.triggerCooldown = 180;
      onNpcInteract(npc);
    }

    private _updateNpcProximity(): void {
      const px = this.player.x, py = this.player.y;

      for (const [id, pos] of this.npcObjects) {
        const dist = Math.sqrt((px - pos.x) ** 2 + (py - pos.y) ** 2);
        const inRange = dist < INTERACT_DIST;

        this.npcNameTags.get(id)?.setVisible(inRange);

        if (inRange && this.triggerCooldown === 0) {
          const npc = NPCS.find(n => n.id === id);
          if (npc && this.lastTriggered !== id) {
            this._triggerNpc(npc);
          }
        }

        // Reset trigger when player walks away
        if (!inRange && this.lastTriggered === id) {
          this.lastTriggered = '';
        }
      }
    }

    private _updateLockTooltip(): void {
      if (clubUnlocked || !this.lockLabel) return;
      const px = this.player.x, py = this.player.y;
      const lx = ZONE_SPLIT * TILE_SIZE + TILE_SIZE / 2;
      const ly = 9 * TILE_SIZE;
      const dist = Math.sqrt((px - lx) ** 2 + (py - ly) ** 2);
      const shouldShow = dist < TILE_SIZE * 3;
      if (shouldShow !== this.lockLabelVisible) {
        this.lockLabel.setVisible(shouldShow);
        this.lockLabelVisible = shouldShow;
      }
    }

    private _initJoystick(): void {
      const jx = containerW - 72, jy = containerH - 72;
      const baseR = 38, stickR = 16;

      this.joystickBase = this.add.graphics().setScrollFactor(0).setDepth(50);
      this.joystickBase.fillStyle(0xffffff, 0.15);
      this.joystickBase.fillCircle(0, 0, baseR);
      this.joystickBase.setPosition(jx, jy);

      this.joystickStick = this.add.graphics().setScrollFactor(0).setDepth(51);
      this.joystickStick.fillStyle(0xffffff, 0.4);
      this.joystickStick.fillCircle(0, 0, stickR);
      this.joystickStick.setPosition(jx, jy);

      this.input.on('pointerdown', (ptr: Phaser.Input.Pointer) => {
        if (ptr.x > containerW / 2) {
          this.joystickActive    = true;
          this.joystickPointerId = ptr.id;
          this.joystickOrigin    = { x: ptr.x, y: ptr.y };
          this.joystickBase.setPosition(ptr.x, ptr.y);
          this.joystickStick.setPosition(ptr.x, ptr.y);
        }
      });

      this.input.on('pointermove', (ptr: Phaser.Input.Pointer) => {
        if (!this.joystickActive || ptr.id !== this.joystickPointerId) return;
        const dx = ptr.x - this.joystickOrigin.x;
        const dy = ptr.y - this.joystickOrigin.y;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        this.joystickDir = { x: dx / len, y: dy / len };
        const clamp = Math.min(len, baseR);
        const angle = Math.atan2(dy, dx);
        this.joystickStick.setPosition(
          this.joystickOrigin.x + Math.cos(angle) * clamp,
          this.joystickOrigin.y + Math.sin(angle) * clamp,
        );
      });

      this.input.on('pointerup', (ptr: Phaser.Input.Pointer) => {
        if (ptr.id !== this.joystickPointerId) return;
        this.joystickActive    = false;
        this.joystickPointerId = -1;
        this.joystickDir       = { x: 0, y: 0 };
        this.joystickStick.setPosition(this.joystickBase.x, this.joystickBase.y);
      });
    }
  }

  const game = new Phaser.Game({
    type:            Phaser.AUTO,
    parent:          container,
    width:           containerW,
    height:          containerH,
    backgroundColor: '#3a6644',
    scene:           [WorldScene],
    scale: {
      mode:         Phaser.Scale.RESIZE,
      autoCenter:   Phaser.Scale.CENTER_BOTH,
    },
  });

  return { destroy: () => { game.destroy(true); } };
}
