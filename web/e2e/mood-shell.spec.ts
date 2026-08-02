import { expect, test } from "@playwright/test";

/**
 * C1 MoodShell: CSS tokens derive from affect payload; visual coverage for
 * three distinct moods; steady + reduced-motion pin affect styling off.
 */

async function readAeVar(page: import("@playwright/test").Page, name: string) {
  return page.evaluate((n) => {
    return getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  }, name);
}

test.describe("mood shell (C1)", () => {
  test("tokens derive from affect payload, not hardcoded neutrals", async ({
    page,
  }) => {
    await page.goto("/?mood=anxious");
    await expect(page.getByTestId("affect-readout")).toBeVisible();

    const valence = await readAeVar(page, "--ae-valence");
    const temp = await readAeVar(page, "--ae-color-temperature");
    const sat = await readAeVar(page, "--ae-saturation");
    const enabled = await readAeVar(page, "--ae-affect-enabled");

    expect(Number(valence)).toBeLessThan(-0.5);
    expect(temp).toMatch(/-/); // cool (negative hue)
    expect(Number(sat)).toBeLessThan(1);
    expect(enabled).toBe("1");

    // Switch preset via UI — tokens must move with payload
    await page.getByTestId("affect-preset-pleasant").click();
    await expect(page.getByTestId("affect-valence")).not.toHaveText(
      valence.slice(0, 5),
    );

    const warmValence = await readAeVar(page, "--ae-valence");
    const warmTemp = await readAeVar(page, "--ae-color-temperature");
    expect(Number(warmValence)).toBeGreaterThan(0.5);
    expect(warmTemp).not.toMatch(/^-/);
  });

  test("steady mode disables affect styling", async ({ page }) => {
    await page.goto("/?mood=pleasant");
    await expect(page.getByTestId("affect-enabled-flag")).toContainText(
      "affect on",
    );

    await page.getByTestId("affect-steady-toggle").click();
    await expect(page.getByTestId("affect-enabled-flag")).toContainText(
      "affect off",
    );
    await expect(page.getByTestId("affect-enabled-flag")).toContainText(
      "steady",
    );

    expect(await readAeVar(page, "--ae-affect-enabled")).toBe("0");
    expect(await readAeVar(page, "--ae-color-temperature")).toBe("0deg");
    expect(await readAeVar(page, "--ae-saturation")).toBe("1");
    expect(await page.locator("html")).toHaveAttribute("data-ae-steady", "1");
  });

  test("reduced-motion disables affect styling", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/?mood=anxious");

    await expect(page.getByTestId("affect-enabled-flag")).toContainText(
      "affect off",
    );
    await expect(page.getByTestId("affect-enabled-flag")).toContainText(
      "reduced-motion",
    );
    expect(await readAeVar(page, "--ae-affect-enabled")).toBe("0");
    expect(await readAeVar(page, "--ae-motion-duration")).toBe("0ms");
    expect(await page.locator("html")).toHaveAttribute(
      "data-ae-reduced-motion",
      "1",
    );
  });

  test("honesty copy does not claim phenomenal feeling", async ({ page }) => {
    await page.goto("/");
    const readout = page.getByTestId("affect-readout");
    await expect(readout).toContainText("not a claim that the system feels");
    await expect(readout).not.toContainText(/I feel|feels curiosity|emotion recognition/i);
  });
});

test.describe("mood visual regression", () => {
  for (const mood of ["pleasant", "bored", "anxious"] as const) {
    test(`shell looks distinct at mood=${mood}`, async ({ page }) => {
      await page.goto(`/?mood=${mood}`);
      await expect(page.getByTestId("mood-shell")).toBeVisible();
      await expect(page.getByTestId("affect-enabled-flag")).toContainText(
        "affect on",
      );
      // Full-viewport capture so body filter / temperature is in frame
      await expect(page).toHaveScreenshot(`mood-${mood}.png`, {
        animations: "disabled",
        maxDiffPixelRatio: 0.04,
      });
    });
  }
});
