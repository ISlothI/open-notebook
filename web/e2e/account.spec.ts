import { expect, test } from "./notebook";

test("register, sign out and sign in", async ({ page, notebook, context }) => {
  await context.clearCookies();
  const email = `new-${crypto.randomUUID()}@example.test`;
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Password").fill("correct horse battery");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByText("Your library is empty")).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await notebook.signIn(email);
  await expect(page.getByText("Your library is empty")).toBeVisible();
});

test("a wrong password is explained", async ({ page, notebook, context }) => {
  const email = await notebook.register();
  await context.clearCookies();
  await notebook.signIn(email, "not my password");

  await expect(page.getByRole("alert")).toHaveText("The e-mail address or the password is wrong.");
});

test("an outage is explained and can be retried", async ({ page, notebook, context }) => {
  await context.route("**/api/auth/me", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("cannot be reached", { timeout: 15_000 });

  await context.unrouteAll();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(notebook.library).toBeVisible();
});
