import { execSync } from "child_process";
import path from "path";

/**
 * Optionally truncate business tables before Playwright when CLEAR_GALLERY_DB=1.
 * Never runs against remote staging (PLAYWRIGHT_REMOTE).
 */
export default async function globalSetup(): Promise<void> {
  if (process.env.PLAYWRIGHT_REMOTE === "1") return;
  if (process.env.CLEAR_GALLERY_DB !== "1") return;

  const repoRoot = path.resolve(__dirname, "..", "..", "..");
  const backendDir = path.join(repoRoot, "backend");
  execSync("python3 -m scripts.clear_business_data_for_gallery", {
    cwd: backendDir,
    stdio: "inherit",
    env: { ...process.env, PYTHONPATH: backendDir },
  });
}
