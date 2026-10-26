// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://danielye.net',
  trailingSlash: 'always',
  // Keep authored whitespace: it is significant between inline elements (chips, pills, separators).
  compressHTML: false,
  build: { format: 'directory' },
  vite: { plugins: [tailwindcss()] },
});
