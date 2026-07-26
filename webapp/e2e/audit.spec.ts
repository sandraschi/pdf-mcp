import { test, expect } from "@playwright/test";

const FE = "http://localhost:11130";

test.describe("Fleet Audit", () => {
    test("Backend health", async ({ request }) => {
        const resp = await request.get("http://127.0.0.1:11131/api/health");
        expect(resp.status()).toBe(200);
    });
    test("Frontend loads", async ({ page }) => {
        await page.goto(FE, { timeout: 15000 });
        await page.waitForTimeout(3000);
        await expect(page.locator("#root")).toBeAttached();
    });
    test("Dashboard has KPIs", async ({ page }) => {
        await page.goto(FE, { timeout: 15000 });
        await page.waitForTimeout(3000);
        await expect(page.locator("[data-testid='dashboard']")).toBeAttached();
    });
});
