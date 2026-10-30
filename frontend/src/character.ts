/**
 * Placeholder cricket player renderer using Canvas 2D geometry only.
 * No external images. Design space is 200x300; pass any canvas size and
 * the character scales uniformly (keeping the 2:3 aspect ratio).
 * Exported as drawCharacter so Stage 2D can generate a Phaser texture from it.
 */

import type { Appearance } from './types';

export interface CharacterOutfit {
  jersey?: string;   // CSS color; default white kit
  cap?: string;      // CSS color; omit = no cap
  shoes?: string;    // CSS color; default dark
  sleeve?: string;   // CSS color; omit = no sleeve band
}

// Skin tone fills
const SKIN: Record<string, string> = {
  light:        '#FDDBB4',
  medium_light: '#E8B88A',
  medium:       '#C68642',
  medium_dark:  '#8D5524',
  dark:         '#4A2912',
};

// Hair fills
const HAIR: Record<string, string> = {
  black:  '#1a1a2e',
  brown:  '#7B3F00',
  blonde: '#D4AA70',
  red:    '#8B1A1A',
  grey:   '#9B9B9B',
  white:  '#F5F5F5',
};

const RAD = (deg: number): number => (deg * Math.PI) / 180;

// ── Hair helper ──────────────────────────────────────────────────────────────

function _drawHair(
  ctx: CanvasRenderingContext2D,
  hx: number,
  hy: number,
  ps: (ds: number) => number,
  px: (dx: number) => number,
  py: (dy: number) => number,
  style: string,
  color: string,
): void {
  ctx.fillStyle = color;

  switch (style) {
    case 'short': {
      // Small cap covering the top crown
      ctx.beginPath();
      ctx.moveTo(hx, hy);
      ctx.arc(hx, hy, ps(30), RAD(200), RAD(340));
      ctx.closePath();
      ctx.fill();
      break;
    }
    case 'medium': {
      // Wider cap reaching down the sides
      ctx.beginPath();
      ctx.moveTo(hx, hy);
      ctx.arc(hx, hy, ps(30), RAD(185), RAD(355));
      ctx.closePath();
      ctx.fill();
      break;
    }
    case 'long': {
      // Wide cap plus strands hanging to shoulder level
      ctx.beginPath();
      ctx.moveTo(hx, hy);
      ctx.arc(hx, hy, ps(30), RAD(185), RAD(355));
      ctx.closePath();
      ctx.fill();
      ctx.fillRect(px(70), py(55), ps(10), ps(45));
      ctx.fillRect(px(120), py(55), ps(10), ps(45));
      break;
    }
    case 'spiky': {
      // Base cap plus five triangular spikes pointing outward from the crown
      ctx.beginPath();
      ctx.moveTo(hx, hy);
      ctx.arc(hx, hy, ps(28), RAD(200), RAD(340));
      ctx.closePath();
      ctx.fill();
      for (let i = 0; i < 5; i++) {
        const ang = RAD(220 + i * 25);
        const bx1 = hx + ps(28) * Math.cos(ang - RAD(6));
        const by1 = hy + ps(28) * Math.sin(ang - RAD(6));
        const bx2 = hx + ps(28) * Math.cos(ang + RAD(6));
        const by2 = hy + ps(28) * Math.sin(ang + RAD(6));
        const tx  = hx + ps(44) * Math.cos(ang);
        const ty  = hy + ps(44) * Math.sin(ang);
        ctx.beginPath();
        ctx.moveTo(bx1, by1);
        ctx.lineTo(tx, ty);
        ctx.lineTo(bx2, by2);
        ctx.closePath();
        ctx.fill();
      }
      break;
    }
    default:
      // 'bald' and unknown values: draw nothing
      break;
  }
}

// ── Cap helper ───────────────────────────────────────────────────────────────

function _drawCap(
  ctx: CanvasRenderingContext2D,
  hx: number,
  hy: number,
  ps: (ds: number) => number,
  px: (dx: number) => number,
  color: string,
): void {
  ctx.fillStyle = color;
  // Dome wider than the head
  ctx.beginPath();
  ctx.moveTo(hx, hy);
  ctx.arc(hx, hy, ps(33), RAD(185), RAD(355));
  ctx.closePath();
  ctx.fill();
  // Flat brim
  ctx.fillRect(px(68), hy + ps(12), ps(64), ps(7));
}

// ── Main export ──────────────────────────────────────────────────────────────

/**
 * Draw a layered cricket player figure onto ctx.
 * width/height define the canvas dimensions; the character scales to fit
 * while preserving the 2:3 design ratio. Drawn from a 200x300 design space.
 */
export function drawCharacter(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  appearance: Appearance,
  outfit: CharacterOutfit = {},
): void {
  ctx.clearRect(0, 0, width, height);

  // Uniform scale from design height (300). cx centres horizontally.
  const scale = height / 300;
  const cx    = width / 2;

  // Design-space coordinate mappers
  const px = (dx: number): number => cx + (dx - 100) * scale;
  const py = (dy: number): number => dy * scale;
  const ps = (ds: number): number => ds * scale;   // uniform size

  // Resolve appearance values, falling back to safe defaults
  const skinColor   = SKIN[appearance.skin_tone]    ?? SKIN.medium;
  const hairColor   = HAIR[appearance.hair_colour]  ?? HAIR.black;
  const jerseyColor = outfit.jersey ?? '#F0F0F0';
  const shoesColor  = outfit.shoes  ?? '#3a3a3a';
  const capColor    = outfit.cap;
  const sleeveColor = outfit.sleeve;

  const bodyW    = appearance.body_type === 'lean'   ? 50
                 : appearance.body_type === 'stocky' ? 72
                 : 60;
  const bodyLeft = 100 - bodyW / 2;

  // Drawing order: back layers first
  // 1. Trousers (always white cricket trousers)
  ctx.fillStyle = '#F8F8F8';
  ctx.fillRect(px(73),  py(173), ps(22), ps(60));   // left leg
  ctx.fillRect(px(105), py(173), ps(22), ps(60));   // right leg

  // 2. Waistband
  ctx.fillStyle = '#cccccc';
  ctx.fillRect(px(72), py(170), ps(56), ps(6));

  // 3. Jersey body
  ctx.fillStyle = jerseyColor;
  ctx.fillRect(px(bodyLeft), py(98), ps(bodyW), ps(75));

  // 4. Arms
  ctx.fillStyle = jerseyColor;
  ctx.fillRect(px(bodyLeft - 14), py(103), ps(14), ps(42));
  ctx.fillRect(px(bodyLeft + bodyW), py(103), ps(14), ps(42));

  // 5. Sleeve bands (if item equipped in that slot)
  if (sleeveColor) {
    ctx.fillStyle = sleeveColor;
    ctx.fillRect(px(bodyLeft - 14), py(120), ps(14), ps(10));
    ctx.fillRect(px(bodyLeft + bodyW), py(120), ps(14), ps(10));
  }

  // 6. Shoes
  ctx.fillStyle = shoesColor;
  ctx.fillRect(px(70),  py(233), ps(26), ps(15));
  ctx.fillRect(px(104), py(233), ps(26), ps(15));

  // 7. Neck
  ctx.fillStyle = skinColor;
  ctx.fillRect(px(92), py(83), ps(16), ps(15));

  // 8. Head
  ctx.fillStyle = skinColor;
  ctx.beginPath();
  ctx.arc(px(100), py(55), ps(28), 0, Math.PI * 2);
  ctx.fill();

  // 9. Hair (before cap so cap draws over it)
  if (appearance.hair_style !== 'bald') {
    _drawHair(ctx, px(100), py(55), ps, px, py, appearance.hair_style, hairColor);
  }

  // 10. Cap (store item)
  if (capColor) {
    _drawCap(ctx, px(100), py(55), ps, px, capColor);
  }

  // 11. Eyes
  ctx.fillStyle = '#2a2020';
  ctx.beginPath();
  ctx.arc(px(91), py(51), ps(3), 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(px(109), py(51), ps(3), 0, Math.PI * 2);
  ctx.fill();

  // 12. Mouth
  ctx.strokeStyle = '#3a2020';
  ctx.lineWidth = ps(1.5);
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.arc(px(100), py(58), ps(6), 0.15, Math.PI - 0.15);
  ctx.stroke();
}
