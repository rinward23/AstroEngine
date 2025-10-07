import { test, expect } from "@playwright/test";

test.describe("rulepack authoring smoke", () => {
  test("renders the editor shell", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("navigation")).toContainText("Rulepack Studio");
    await expect(page.getByRole("heading", { level: 2, name: /validation/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /format/i })).toBeVisible();
  });
});
