/**
 * scripts/copy-assets.js
 * ----------------------
 * Post-build script: copies manifest.json, icons/, and assets/ into dist/.
 * Run automatically via `npm run build`.
 */

import { cpSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const dist = resolve(root, "dist");

// Copy manifest
cpSync(resolve(root, "manifest.json"), resolve(dist, "manifest.json"));

// Copy icons
mkdirSync(resolve(dist, "icons"), { recursive: true });
cpSync(resolve(root, "public", "icons"), resolve(dist, "icons"), { recursive: true });

// Copy assets (ARCUS_DOG.png — Vite copies public/ but we ensure it's there)
mkdirSync(resolve(dist, "assets"), { recursive: true });
cpSync(
  resolve(root, "public", "assets", "ARCUS_DOG.png"),
  resolve(dist, "assets", "ARCUS_DOG.png")
);

console.log("✓ Static assets copied to dist/");
