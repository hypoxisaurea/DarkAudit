import { expect, test } from "@playwright/test";

test("landing page opens the audit dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /금융상품 UX를/ })).toBeVisible();
  await page.getByRole("link", { name: "Audit 시작하기" }).first().click();
  await expect(page.getByRole("heading", { name: "Insurance Signup Flow v1" })).toBeVisible();
});

test("user creates an audit and completes analysis", async ({ page }) => {
  await page.goto("/app/audits/new");
  await page.getByLabel("Audit 이름").fill("Playwright 가입 Flow");
  await page.locator('input[type="file"]').setInputFiles({
    name: "option-screen.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await page.getByRole("button", { name: "분석 시작하기" }).click();
  await expect(page.getByRole("heading", { name: "금융 UX를 분석하고 있습니다" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Audit 분석이 완료되었습니다" })).toBeVisible({
    timeout: 15_000,
  });
});

test("finding can be marked as resolved", async ({ page }) => {
  await page.goto("/app/overview?finding=finding-preselected-option");
  await expect(page.getByText("Needs Review").first()).toBeVisible();
  await page.getByRole("button", { name: "해결됨으로 표시" }).click();
  await expect(page.getByText("Resolved").first()).toBeVisible();
});
