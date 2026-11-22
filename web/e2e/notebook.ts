import { test as base, expect, type Locator, type Page } from "@playwright/test";

const PASSWORD = "correct horse battery";

type Item = { id: string; title: string };

/** Speaks the language of the product, so that the tests read like user flows. */
export class Notebook {
  constructor(readonly page: Page) {}

  async register(): Promise<string> {
    const email = `user-${crypto.randomUUID()}@example.test`;
    const response = await this.page.request.post("/api/auth/register", {
      data: { email, password: PASSWORD },
    });
    expect(response.status()).toBe(201);
    return email;
  }

  async signIn(email: string, password = PASSWORD): Promise<void> {
    await this.page.goto("/");
    await this.page.getByLabel("E-mail").fill(email);
    await this.page.getByLabel("Password").fill(password);
    await this.page.getByRole("button", { name: "Sign in", exact: true }).click();
  }

  /** Prepares data through the api when building it is not what the test is about. */
  async seed(kind: string, title: string, parent?: Item): Promise<Item> {
    const response = await this.page.request.post("/api/items", {
      data: { kind, title, parent_id: parent?.id ?? null },
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as Item;
  }

  async seedPage(content = "", title = "First page"): Promise<Item> {
    const notebook = await this.seed("notebook", "Research");
    const section = await this.seed("section", "Ideas", notebook);
    const page = await this.seed("page", title, section);
    if (content) {
      await this.saveElsewhere(page, content, 1);
    }
    return page;
  }

  /** A save from another device. */
  async saveElsewhere(page: Item, content: string, base: number): Promise<void> {
    const response = await this.page.request.put(`/api/pages/${page.id}`, {
      data: { title: page.title, content, base_version: base },
    });
    expect(response.status()).toBe(200);
  }

  async open(page: Item): Promise<void> {
    await this.page.goto(`/page/${page.id}`);
    await expect(this.text).toBeVisible();
  }

  async createFromMenu(menuOf: Locator, kind: string, title: string): Promise<void> {
    await menuOf.click();
    await this.page.getByRole("menuitem", { name: `New ${kind}` }).click();
    await this.name(title);
  }

  async name(title: string): Promise<void> {
    const dialog = this.page.getByRole("dialog");
    await dialog.getByRole("textbox").fill(title);
    await dialog.getByRole("button", { name: /Create|Save/ }).click();
    await expect(dialog).toBeHidden();
  }

  actionsOf(title: string): Locator {
    return this.page.getByRole("button", { name: `Actions for ${title}` });
  }

  get text(): Locator {
    return this.page.getByRole("textbox", { name: "Page content" });
  }

  get library(): Locator {
    return this.page.getByRole("navigation", { name: "Library" });
  }

  get status(): Locator {
    return this.page.locator(".save-status");
  }

  async write(text: string): Promise<void> {
    await this.text.click();
    await this.page.keyboard.press("ControlOrMeta+a");
    await this.page.keyboard.type(text);
    await expect(this.status).toHaveText("Edited");
  }

  async save(): Promise<void> {
    await this.page.keyboard.press("ControlOrMeta+s");
    await expect(this.status).toHaveText("Saved");
  }
}

export const test = base.extend<{ notebook: Notebook }>({
  notebook: async ({ page }, use) => {
    const notebook = new Notebook(page);
    await notebook.register();
    await use(notebook);
  },
});

export { expect };
