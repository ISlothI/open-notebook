import { expect, test } from "./notebook";

test("F4: delete and recover a notebook", async ({ notebook, page }) => {
  await notebook.open(await notebook.seedPage("Precious"));
  await notebook.actionsOf("Research").click();
  await page.getByRole("menuitem", { name: "Move to trash" }).click();
  await expect(notebook.library.getByText("Research")).toBeHidden();

  await page.getByRole("link", { name: "Trash" }).click();
  await page.getByRole("button", { name: "Restore Research" }).click();
  await expect(page.getByText("The trash is empty")).toBeVisible();

  await notebook.library.getByRole("link", { name: "Ideas" }).click();
  await page.getByRole("link", { name: "First page" }).click();
  await expect(notebook.text).toHaveText("Precious");
});

test("F4: an item whose parent is in the trash can go elsewhere", async ({ notebook, page }) => {
  await notebook.seedPage();
  await notebook.seed("notebook", "Archive");
  await page.goto("/");
  for (const title of ["Ideas", "Research"]) {
    await notebook.actionsOf(title).click();
    await page.getByRole("menuitem", { name: "Move to trash" }).click();
    await expect(notebook.library.getByText(title)).toBeHidden();
  }

  await page.getByRole("link", { name: "Trash" }).click();
  await page.getByRole("button", { name: "Restore Ideas" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Archive" }).click();

  await expect(notebook.library.getByRole("link", { name: "Ideas" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Restore Ideas" })).toBeHidden();
});

test("items can be renamed, reordered and moved", async ({ notebook, page }) => {
  await notebook.seed("folder", "Work");
  await notebook.seed("notebook", "Alpha");
  await notebook.seed("notebook", "Beta");
  await page.goto("/");

  await notebook.actionsOf("Alpha").click();
  await page.getByRole("menuitem", { name: "Rename" }).click();
  await notebook.name("Gamma");
  await expect(notebook.library.getByText("Gamma")).toBeVisible();

  await notebook.actionsOf("Beta").click();
  await page.getByRole("menuitem", { name: "Move up" }).click();
  await expect(notebook.library.locator(".tree-label")).toHaveText(["Work", "Beta", "Gamma"]);

  await notebook.actionsOf("Gamma").click();
  await page.getByRole("menuitem", { name: "Move to…" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Work" }).click();
  await expect(notebook.library.locator(".tree-label")).toHaveText(["Work", "Gamma", "Beta"]);
});

test("items can be dragged to another place", async ({ notebook, page }) => {
  await notebook.seed("folder", "Work");
  await notebook.seed("notebook", "Alpha");
  await page.goto("/");

  await notebook.library
    .getByText("Alpha")
    .dragTo(notebook.library.getByText("Work", { exact: true }));

  await expect(notebook.library.locator("li li").getByText("Alpha")).toBeVisible();
});
