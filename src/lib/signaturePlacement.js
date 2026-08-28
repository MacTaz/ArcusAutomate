/**
 * signaturePlacement.js
 * ---------------------
 * Single source of truth for signature scaling math.
 *
 * Used by:
 *   - src/options/Options.jsx  (live preview)
 *   - src/lib/saaf.js          (PDF embed)
 *   - src/lib/avr.js           (PDF embed)
 *
 * All values are in PDF points unless noted otherwise.
 */

/**
 * Given the user-configured signatureSize (in pt) and the image's natural
 * pixel dimensions, returns the rendered { width, height } in PDF points
 * using the same scaleToFit logic that pdf-lib uses internally.
 *
 * @param {number} signatureSize  - The slider value (pt)
 * @param {number} naturalW       - Image naturalWidth (px)
 * @param {number} naturalH       - Image naturalHeight (px)
 * @returns {{ width: number, height: number }}
 */
export function computeSignatureDimensions(signatureSize, naturalW, naturalH) {
  const maxW = Number(signatureSize) * 0.85;
  const maxH = maxW * 0.55; // aspect-ratio cap keeps signature from being too tall
  const ratio = naturalW / naturalH;

  let width, height;
  if (ratio > maxW / maxH) {
    // constrained by width
    width = maxW;
    height = maxW / ratio;
  } else {
    // constrained by height
    height = maxH;
    width = maxH * ratio;
  }

  return { width, height };
}
