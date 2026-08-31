/**
 * scripts/copy-assets.js
 * ----------------------
 * Post-build script: copies manifest.json into dist/.
 * Vite automatically handles public/ assets (icons/ & assets/).
 * Run automatically via `npm run build`.
 */

import { cpSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const dist = resolve(root, "dist");

// Copy manifest.json to dist/
cpSync(resolve(root, "manifest.json"), resolve(dist, "manifest.json"));

console.log("✓ Extension manifest copied to dist/");
