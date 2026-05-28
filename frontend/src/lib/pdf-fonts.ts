// Side-effect module: registers fonts for @react-pdf/renderer.
// Import this file at the top of any react-pdf document component for its side effects.
// Do NOT add "use client" — this is a plain module, not a React component.

import { Font } from "@react-pdf/renderer";

const INTER_CDN =
  "https://cdn.jsdelivr.net/npm/@fontsource/inter@5.2.8/files/";

const ETHIOPIC_CDN =
  "https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-ethiopic@5.2.9/files/";

Font.register({
  family: "Inter",
  fonts: [
    {
      src: INTER_CDN + "inter-latin-400-normal.woff2",
      fontWeight: 400,
    },
    {
      src: INTER_CDN + "inter-latin-600-normal.woff2",
      fontWeight: 600,
    },
  ],
});

Font.register({
  family: "NotoSerifEthiopic",
  fonts: [
    {
      src: ETHIOPIC_CDN + "noto-serif-ethiopic-ethiopic-400-normal.woff2",
      fontWeight: 400,
    },
    {
      src: ETHIOPIC_CDN + "noto-serif-ethiopic-ethiopic-600-normal.woff2",
      fontWeight: 600,
    },
  ],
});
