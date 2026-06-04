test.describe("Recording 2/6/2026 at 10:48:45", () => {
  test("tests Recording 2/6/2026 at 10:48:45", async ({ page }) => {
    await page.setViewportSize({
          width: 1304,
          height: 911
        })
    await page.goto("http://localhost:5173/workspaces");
    await page.locator("input").click()
    await page.locator("input").type("Test");
    await page.locator("textarea").type("T");
    await page.locator("textarea").type("Test");
    await page.locator("#root > div > div button").click()
    await page.locator("li:nth-of-type(1) a").click()
    await page.locator("input").click()
    await page.locator("input").type("C:\\fakepath\\MODELOS_ANEXOS_PLIEGOS..pdf");
    await page.locator("section.workspace-detail-grid button").click()
    await page.locator("#root > div > div a").click()
    await page.locator("form > div:nth-of-type(1) button").click()
    await page.locator("textarea").click()
    await page.locator("textarea").type("Ge");
    await page.locator("textarea").type("Genera un contrato como el que te he pasado, pero rellenalo con datos, inventatelos");
    await page.locator("div.generate-actions > button").click()
    await page.locator("aside li:nth-of-type(2) > a").click()
    await page.locator("li:nth-of-type(3) > a").click()
    await page.locator("li:nth-of-type(4) > a").click()
    await page.locator("li:nth-of-type(5) > a").click()
    await page.locator("div > div > aside button").click()
    await page.locator("label:nth-of-type(1) > input").click()
    await page.locator("label:nth-of-type(1) > input").type("B");
    await page.locator("label:nth-of-type(1) > input").type("Bloque nuevo test");
    await page.locator("select").click()
    await page.locator("select").click()
    await page.locator("main > div textarea").click()
    await page.locator("main > div textarea").type("Te");
    await page.locator("main > div textarea").type("Test");
    await page.locator("main button.btn-dark").click()
    await page.locator("aside textarea").click()
    await page.locator("aside textarea").type("Re");
    await page.locator("aside textarea").type("Revisa los otros bloques, y genera un grafico con los datos que encuentres y metelo aqui");
    await page.locator("button:nth-of-type(2)").click()
    await page.locator("aside > section button:nth-of-type(2)").click()
    await page.locator("span.impact-suggestion-summary").click()
    await page.locator("article button:nth-of-type(2)").click()
    await page.locator("nav > a").click()
    await page.locator("article:nth-of-type(2) a").click()
    await page.locator("section.workspace-detail-grid a:nth-of-type(1)").click()
    await page.locator("li:nth-of-type(6) > a").click()
    await page.locator("section.page-head button").click()
  });
});
