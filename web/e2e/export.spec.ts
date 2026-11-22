import { readFile } from "node:fs/promises";
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "./notebook";

test("F3: export a notebook and download it", async ({ notebook, page }) => {
  await notebook.seedPage("Text for the paper");
  await page.goto("/");
  await notebook.actionsOf("Research").click();
  await page.getByRole("menuitem", { name: "Export as PDF" }).click();
  await expect(page.getByText("Preparing “Research”")).toBeVisible();

  await page.getByRole("link", { name: "Exports" }).click();
  const link = page.getByRole("link", { name: "Download Research" });
  await expect(link).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: "/reports/screens/exports-light.png" });
  const { violations } = await new AxeBuilder({ page }).analyze();
  expect(violations).toEqual([]);

  const downloading = page.waitForEvent("download");
  await link.click();
  const download = await downloading;
  expect(download.suggestedFilename()).toBe("Research.pdf");
  const content = await readFile(await download.path());
  expect(content.subarray(0, 5).toString()).toBe("%PDF-");
});

test("an empty notebook is explained instead of exported", async ({ notebook, page }) => {
  await notebook.seed("notebook", "Blank");
  await page.goto("/");
  await notebook.actionsOf("Blank").click();
  await page.getByRole("menuitem", { name: "Export as PDF" }).click();

  await expect(page.getByText("There is no page to export.")).toBeVisible();
});
