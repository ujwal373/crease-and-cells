# Asset Inventory

All visual assets in this project are either drawn in code or use CC0-licensed material.
No copyrighted sprites, textures, or artwork are included.

## Placeholder character art

File: frontend/src/character.ts

All character artwork is drawn procedurally using the Canvas 2D API (rectangles, circles, arcs).
No external image files are loaded. The renderer is the only source of the player sprite.

Licence: project code (MIT, same as the rest of the repository).

## Phaser 3 world tiles and NPC sprites

Files: frontend/src/world.ts, frontend/src/world-logic.ts

All tile colours (grass, wall, court, path) are solid fill rectangles drawn with Phaser
GameObjects.Graphics. NPC sprites are drawn on HTMLCanvasElement using the Canvas 2D API.
No external images, spritesheets, or tilesets are loaded.

Licence: project code (MIT, same as the rest of the repository).

## Future assets

When any CC0 or licensed asset is added, record it here with:
1. Filename or directory
2. Source URL
3. Licence name and version
4. Any attribution requirement from the licence
