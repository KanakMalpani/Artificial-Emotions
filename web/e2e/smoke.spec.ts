import { expect, test } from "@playwright/test";

/**
 * C0 + Wave 4 smoke: shell + C2–C5 surfaces at each viewport (320 / 768 / 1024).
 * Does not require the Python API.
 */
test.describe("shell smoke", () => {
  test("brand and explore controls are visible", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Artificial Emotions" })).toBeVisible();
    await expect(page.getByText("Ask what to investigate")).toBeVisible();
    await expect(page.getByLabel("Domain")).toBeVisible();
    await expect(page.getByLabel("ValueProfile")).toBeVisible();
  });

  test("C2–C5 presentation mounts without API", async ({ page }) => {
    await page.goto("/");

    // C2 stance nav — seven lenses + curiosity
    const nav = page.getByTestId("stance-nav");
    await expect(nav).toBeVisible();
    for (const id of [
      "curiosity",
      "doubt",
      "safety",
      "focus",
      "close",
      "taste",
      "wonder",
      "survey",
    ]) {
      await expect(page.getByTestId(`stance-tab-${id}`)).toBeVisible();
    }
    await page.getByTestId("stance-tab-wonder").click();
    await expect(page.getByTestId("stance-asks")).toContainText("surprising");

    // C3 trajectory map (demo path when no ranks)
    await expect(page.getByTestId("trajectory-map")).toBeVisible();
    await expect(page.getByTestId("trajectory-path")).toBeVisible();
    await expect(page.getByTestId("trajectory-dead-end").first()).toBeVisible();
    await expect(page.getByTestId("trajectory-cost-marker").first()).toBeVisible();
    await page.getByTestId("trajectory-step-1").hover();
    await expect(page.getByTestId("trajectory-appraisal")).toBeVisible();

    // C4 imagination quarantine — permanent label, no scores
    const canvas = page.getByTestId("imagine-canvas");
    await expect(canvas).toBeVisible();
    await expect(page.getByTestId("imagine-quarantine-banner")).toContainText(
      "IMAGINED — NOT RETRIEVED",
    );
    await expect(page.getByTestId("imagine-card").first()).toContainText("imagined");
    await expect(page.getByTestId("imagine-confidence-null").first()).toContainText(
      "null",
    );
    await expect(canvas).not.toContainText("curiosity_score");

    // C5 confession — honesty + cannot-distinguish
    await expect(page.getByTestId("confession-panel")).toBeVisible();
    await expect(page.getByTestId("confession-honesty")).toContainText(
      "not a claim that the system feels",
    );
    await expect(page.getByTestId("confession-cannot-distinguish")).toContainText(
      "can't tell which",
    );
    await expect(page.getByTestId("confession-claims-not")).toBeVisible();
  });
});
