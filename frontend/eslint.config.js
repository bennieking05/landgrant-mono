// ESLint flat config for the Vite + React + TypeScript frontend.
// Run with ``npm run lint:eslint``. The existing ``npm run lint`` still
// performs a ``tsc --noEmit`` type check; the two are complementary.
import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

export default tseslint.config(
  {
    ignores: [
      "dist",
      "node_modules",
      "tsconfig.tsbuildinfo",
      "playwright-report",
      "test-results",
      "tests/**",
    ],
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      // The codebase uses ``any`` in a handful of adapter seams that are
      // slated for refactoring in Phase 4. Downgrade to warning so the lint
      // gate stays green while we chip away at them.
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-console": ["warn", { allow: ["warn", "error", "debug"] }],
    },
  },
);
