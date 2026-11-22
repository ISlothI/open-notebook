import { expect, test } from "./notebook";

test("F1: write, version and restore", async ({ notebook, page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New notebook" }).click();
  await notebook.name("Studies");
  await notebook.createFromMenu(notebook.actionsOf("Studies"), "section", "Lectures");
  await expect(page.getByRole("heading", { name: "Lectures" })).toBeVisible();
  await page.getByRole("button", { name: "New page" }).first().click();
  await notebook.name("DevOps");

  await notebook.write("The first thought");
  await notebook.save();
  await notebook.write("A better thought");
  await notebook.save();

  await page.getByRole("button", { name: "Version history" }).click();
  await page.getByRole("button", { name: /more within minutes/ }).click();
  await page.getByRole("button", { name: /Version 2/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.locator("ins").first()).toBeVisible();
  await dialog.getByRole("button", { name: "Restore this version" }).click();

  await expect(notebook.text).toHaveText("The first thought");
  await expect(page.getByText("Restored from version 2")).toBeVisible();
  await page.reload();
  await expect(notebook.text).toHaveText("The first thought");
});

test("text is saved automatically and survives a reload", async ({ notebook, page }) => {
  await notebook.open(await notebook.seedPage());
  await notebook.write("No save button was pressed");
  await expect(notebook.status).toHaveText("Saved", { timeout: 10_000 });

  await page.reload();

  await expect(notebook.text).toHaveText("No save button was pressed");
});

test("opening a page does not create a version", async ({ notebook, page }) => {
  const item = await notebook.seedPage("- notation that the editor\n- would normalise\n");
  await notebook.open(item);
  await page.waitForTimeout(6_000);

  const versions = await (await page.request.get(`/api/pages/${item.id}/versions`)).json();
  expect(versions).toHaveLength(2);
});

test("Markdown can be edited as source", async ({ notebook, page }) => {
  await notebook.open(await notebook.seedPage());
  await page.getByRole("button", { name: "Markdown source" }).click();
  await notebook.text.fill("## Heading\n\n* item\n");
  await notebook.save();
  await page.getByRole("button", { name: "Rich text" }).click();

  await expect(notebook.text.getByRole("heading", { name: "Heading" })).toBeVisible();
});

test("renaming in the page renames it in the list", async ({ notebook, page }) => {
  await notebook.open(await notebook.seedPage());
  await page.getByRole("textbox", { name: "Page title" }).fill("A clearer title");
  await notebook.save();

  await expect(page.getByRole("link", { name: "A clearer title" })).toBeVisible();
});

test("text typed offline is kept and saved later", async ({ notebook, page, context }) => {
  const item = await notebook.seedPage();
  await notebook.open(item);
  await context.route("**/api/pages/**", (route) =>
    route.request().method() === "PUT" ? route.abort() : route.continue(),
  );
  await notebook.write("Written on a train");
  await page.keyboard.press("ControlOrMeta+s");
  await expect(notebook.status).toHaveText("Offline – kept on this device");

  await page.reload();
  await expect(page.getByText("Unsaved text from your last visit")).toBeVisible();
  await expect(notebook.text).toHaveText("Written on a train");

  await context.unrouteAll();
  await notebook.save();
});

for (const [choice, expected] of [
  ["Continue with mine", "Mine"],
  ["Continue with the other", "Theirs"],
] as const) {
  test(`R3: edit conflict, ${choice.toLowerCase()}`, async ({ notebook, page }) => {
    const item = await notebook.seedPage();
    await notebook.open(item);
    await notebook.write("Mine");
    await notebook.saveElsewhere(item, "Theirs", 1);
    await page.keyboard.press("ControlOrMeta+s");

    const dialog = page.getByRole("dialog", { name: "This page was changed elsewhere" });
    await expect(dialog).toContainText("Mine");
    await expect(dialog).toContainText("Theirs");
    await dialog.getByRole("button", { name: choice }).click();

    await expect(dialog).toBeHidden();
    await expect(notebook.text).toHaveText(expected);
    const list = await (await page.request.get(`/api/pages/${item.id}/versions`)).json();
    const texts = await Promise.all(
      list.map(async ({ version }: { version: number }) => {
        const response = await page.request.get(`/api/pages/${item.id}/versions/${version}`);
        return (await response.json()).content.trim();
      }),
    );
    expect(texts).toEqual(expect.arrayContaining(["Mine", "Theirs"]));
  });
}
