import { expect, test } from "@playwright/test";

test("landing visual", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveScreenshot("landing.png", { fullPage: true, animations: "disabled" });
});

test("overview visual", async ({ page }) => {
  await page.goto("/app/overview");
  await page.getByRole("heading", { name: "보험 가입 흐름 v1" }).waitFor();
  await expect(page).toHaveScreenshot("overview.png", { fullPage: true, animations: "disabled" });
});
