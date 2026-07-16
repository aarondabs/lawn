// ESLint 9 flat config.
//
// Migrated from .eslintrc.json (legacy) because `next lint` is deprecated in Next 15.5 and removed
// in Next 16 — at which point the old eslintrc format stops being shimmed. eslint-config-next still
// ships eslintrc-style presets (no flat export), so FlatCompat wraps them for the flat format.
//
// Run via `npm run lint` (now `eslint .`, not `next lint`).
import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({ baseDirectory: __dirname });

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
];

export default eslintConfig;
