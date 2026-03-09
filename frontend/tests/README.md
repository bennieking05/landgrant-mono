# Frontend Tests

## E2E Tests (Playwright)

Browser-based regression tests that validate persona journeys and capture screenshots.

### Prerequisites

1. Install Playwright browsers (first time only):
   ```bash
   cd frontend
   npx playwright install
   ```

2. Start the backend and frontend:
   ```bash
   # Terminal 1: Backend
   cd backend && uvicorn app.main:app --reload --port 8050

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

### Running Tests

```bash
# All tests (headless)
npm run test:e2e

# With visible browser
npm run test:e2e:headed

# Debug mode (step through)
npm run test:e2e:debug

# Specific test file
npx playwright test tests/e2e/landowner.spec.ts

# View HTML report
npm run test:e2e:report
```

### Test Suites

| File | Persona | Journey |
|------|---------|---------|
| `landowner.spec.ts` | Landowner | Invite → Verify → Decision → Upload |
| `agent.spec.ts` | Land Agent | Parcels → Comms → Packet → Title |
| `counsel.spec.ts` | Counsel | Approvals → Templates → Binder → Budget |

### Screenshot Artifacts

Screenshots are saved to `artifacts/e2e/`:

- `landowner-*.png` - Landowner portal steps
- `agent-*.png` - Agent workbench steps
- `counsel-*.png` - Counsel controls steps
- `counsel-flow-*.png` - Full counsel workflow sequence

### Configuration

See `playwright.config.ts` for settings:

- `baseURL`: http://localhost:3050 (frontend)
- `screenshot`: Captured on failure
- `trace`: Recorded on first retry
- `outputDir`: `../artifacts/e2e/test-results`

### CI Integration

Tests run in GitHub Actions CI. On failure:

1. Screenshots uploaded as artifacts
2. HTML report generated
3. Traces available for debugging

### Writing New Tests

```typescript
import { test, expect } from "@playwright/test";
import path from "path";

const ARTIFACTS_DIR = path.resolve(__dirname, "..", "..", "..", "artifacts", "e2e");

test("should do something", async ({ page }) => {
  await page.goto("/some-page");
  
  // Assert visible elements
  await expect(page.locator("text=Expected Text")).toBeVisible();
  
  // Capture screenshot
  await page.screenshot({
    path: path.join(ARTIFACTS_DIR, "test-name-step.png"),
    fullPage: true,
  });
});
```

### Troubleshooting

**Tests fail with connection error**
- Ensure backend is running on port 8050
- Ensure frontend is running on port 3050

**Screenshots not saving**
- Ensure `artifacts/e2e/` directory exists
- Check write permissions

**Flaky tests**
- Add explicit waits: `await page.waitForTimeout(1000)`
- Use `await page.waitForSelector("...")`
- Check if data depends on API response timing
