import { AxeBuilder } from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, type Notebook, test } from "./notebook";

const INDEXING_TIMEOUT_MS = 30_000;

async function waitUntilFound(page: Page, query: string): Promise<void> {
  await expect
    .poll(
      async () => {
        const response = await page.request.get("/api/search", { params: { q: query } });
        return (await response.json()).hits.length;
      },
      { timeout: INDEXING_TIMEOUT_MS },
    )
    .toBeGreaterThan(0);
}

async function seedTwoNotebooks(notebook: Notebook): Promise<void> {
  const texts = {
    Kitchen: ["Sourdough", "Knead the dough, let it rest overnight and bake it."],
    Travel: ["Budapest", "Walk across the bridge and visit the thermal baths. Bring bread."],
  };
  for (const [title, [pageTitle, content]] of Object.entries(texts)) {
    const book = await notebook.seed("notebook", title);
    const section = await notebook.seed("section", "Notes", book);
    const item = await notebook.seed("page", pageTitle as string, section);
    await notebook.saveElsewhere(item, content as string, 1);
  }
}

test("F2: find a page by meaning and open it", async ({ notebook, page }) => {
  await seedTwoNotebooks(notebook);
  await waitUntilFound(page, "overnight");
  await waitUntilFound(page, "thermal");
  await page.goto("/");
  await expect(notebook.library).toBeVisible();
  await page.keyboard.press("ControlOrMeta+k");
  const search = page.getByRole("combobox", { name: "Search your notes" });

  await search.fill("sightseeing in a city");
  await expect(page.locator(".search-hit").first()).toContainText("Budapest", { timeout: 15_000 });

  await search.fill("bread");
  await expect(page.locator(".search-hit")).toHaveCount(2);
  await expect(page.locator("mark").first()).toHaveText(/bread/i);
  await page.screenshot({ path: "/reports/screens/search-light.png" });
  const { violations } = await new AxeBuilder({ page }).include(".search-dialog").analyze();
  expect(violations).toEqual([]);

  await page.getByLabel("Search in").selectOption("Kitchen");
  await expect(page.locator(".search-hit")).toHaveCount(1);
  await search.press("Enter");

  await expect(notebook.text).toContainText("Knead the dough");
});

test("nothing found is explained", async ({ page, notebook }) => {
  await notebook.seed("notebook", "Empty");
  await page.goto("/");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("combobox", { name: "Search your notes" }).fill("nonexistent");

  await expect(page.getByText("Nothing found")).toBeVisible();
});

test("degraded search is announced", async ({ page, notebook, context }) => {
  await notebook.seed("notebook", "Empty");
  await context.route("**/api/search**", (route) =>
    route.fulfill({ json: { mode: "fulltext", hits: [] } }),
  );
  await page.goto("/");
  await expect(notebook.library).toBeVisible();
  await page.keyboard.press("ControlOrMeta+k");
  await page.getByRole("combobox", { name: "Search your notes" }).fill("anything");

  await expect(page.getByText("matches by words only")).toBeVisible();
});
