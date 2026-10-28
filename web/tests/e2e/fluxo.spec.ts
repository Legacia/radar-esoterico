// Fluxo principal, como uma pessoa faria no navegador, contra a API real com banco temporário:
// entrar, conferir o caso obrigatório da margem, cadastrar fornecedor, produto e cotação,
// planejar a compra e sair. Os dados são fictícios.
import { expect, test, type Page } from "@playwright/test";

const EMAIL = "e2e@example.invalid";
const SENHA = "senha-ficticia-e2e";

async function entrar(page: Page) {
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(EMAIL);
  await page.getByLabel("Senha", { exact: true }).fill(SENHA);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("navigation", { name: "Telas" })).toBeVisible();
}

const tela = (page: Page, nome: string) =>
  page.getByRole("navigation", { name: "Telas" }).getByRole("link", { name: nome, exact: true }).click();

test("sem login, nenhuma tela nem dado aparece", async ({ page, request }) => {
  await page.goto("/#/compras");
  await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Telas" })).toHaveCount(0);
  expect((await request.get("/api/painel")).status()).toBe(401);
});

test("senha errada mostra mensagem genérica", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(EMAIL);
  await page.getByLabel("Senha", { exact: true }).fill("senha-errada-ficticia");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("alert")).toHaveText("E-mail ou senha inválidos.");
});

test("fluxo principal: margem, fornecedor, produto, cotação, compra e saída", async ({ page }) => {
  await entrar(page);
  await expect(page.getByRole("heading", { level: 1, name: "Painel" })).toBeVisible();

  // Caso obrigatório: kit de R$ 59,90 com custo de R$ 20,00 dá R$ 14,33 e 23,9%.
  await tela(page, "Calculadora e parâmetros");
  const simulacao = page.getByRole("region", { name: "Simular uma venda" });
  await simulacao.getByLabel("Preço de venda (R$)", { exact: true }).fill("59,90");
  await simulacao.getByLabel("Custo do produto (R$)", { exact: true }).fill("20,00");
  await simulacao.getByRole("button", { name: "Calcular margem" }).click();
  await expect(simulacao.getByText("R$ 14,33")).toBeVisible();
  await expect(simulacao.getByText("23,9%")).toBeVisible();
  await expect(simulacao.getByText("R$ 55,56")).toBeVisible();

  // Fornecedor com as verificações feitas.
  await tela(page, "Fornecedores");
  await page.getByRole("button", { name: "Cadastrar fornecedor" }).click();
  const novoFornecedor = page.getByRole("dialog", { name: "Cadastrar fornecedor" });
  await novoFornecedor.getByLabel("Nome do fornecedor", { exact: true }).fill("Fornecedor fictício E2E");
  await novoFornecedor.getByLabel("CNPJ", { exact: true }).fill("00.000.000/0001-00");
  await novoFornecedor.getByLabel("Prazo", { exact: true }).fill("7 dias");
  await novoFornecedor.getByLabel("Condição de pagamento", { exact: true }).fill("Pix");
  for (const rotulo of ["CNPJ verificado", "Condições comerciais verificadas", "Emite nota fiscal"]) {
    await novoFornecedor.getByLabel(rotulo, { exact: true }).check();
  }
  await novoFornecedor.getByRole("button", { name: "Salvar fornecedor" }).click();
  const fichaFornecedor = page.getByRole("dialog", { name: "Fornecedor fictício E2E" });
  await expect(fichaFornecedor).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("cell", { name: "Fornecedor fictício E2E" })).toBeVisible();

  // Produto com as três conferências.
  await tela(page, "Produtos e SKUs");
  await page.getByRole("button", { name: "Cadastrar produto" }).click();
  const novoProduto = page.getByRole("dialog", { name: "Cadastrar produto" });
  await novoProduto.getByLabel("Nome do produto", { exact: true }).fill("Kit fictício 3 incensos + suporte");
  for (const rotulo of ["Especificações conferidas", "Procedência conferida", "Qualidade conferida pela Anna"]) {
    await novoProduto.getByLabel(rotulo, { exact: true }).check();
  }
  await novoProduto.getByRole("button", { name: "Salvar produto" }).click();

  // Cotação do caso obrigatório, em pacote com 2 unidades de venda a R$ 40,00 (custo de R$ 20,00 por
  // unidade de venda); a margem aparece na ficha do produto.
  const fichaProduto = page.getByRole("dialog", { name: "Kit fictício 3 incensos + suporte" });
  await fichaProduto.getByRole("tab", { name: "Registrar cotação" }).click();
  await fichaProduto.getByLabel("Código do parceiro (opcional)", { exact: true }).fill("KIT-E2E");
  await fichaProduto.getByLabel("Preço cotado (R$)", { exact: true }).fill("40,00");
  await fichaProduto.getByLabel("Unidades de venda na unidade cotada", { exact: true }).fill("2");
  await fichaProduto.getByLabel("Quantidade mínima (em unidades cotadas)", { exact: true }).fill("3");
  await fichaProduto.getByLabel("Preço conservador por unidade de venda (R$), opcional", { exact: true }).fill("59,90");
  await fichaProduto.getByRole("button", { name: "Salvar cotação" }).click();
  await expect(page.getByText("Cotação registrada.")).toBeVisible();
  await fichaProduto.getByRole("tab", { name: "Cotações (1)" }).click();
  const linha = fichaProduto.getByRole("row", { name: /KIT-E2E/ });
  await expect(linha).toContainText("RAD-000001");
  await expect(linha).toContainText("R$ 20,00");
  await expect(linha).toContainText("R$ 14,33");
  await expect(linha).toContainText("23,9%");
  await expect(linha).toContainText("R$ 55,56");
  await page.keyboard.press("Escape");

  // Plano de compra: com demanda e concorrência confirmadas, os seis critérios ficam cumpridos.
  await tela(page, "Decisão de compra");
  await page.getByRole("button", { name: "Adicionar produto ao plano" }).click();
  const plano = page.getByRole("dialog", { name: "Adicionar produto ao plano" });
  await expect(plano.getByLabel("Quantidade planejada", { exact: true })).toHaveValue("6");
  await expect(plano.getByLabel("Preço conservador de venda no plano (R$)", { exact: true })).toHaveValue("59,90");
  await plano.getByLabel("Demanda confirmada", { exact: true }).check();
  await plano.getByLabel("Justificativa de demanda", { exact: true }).fill("Evidência fictícia de procura");
  await plano.getByLabel("Concorrência confirmada", { exact: true }).check();
  await plano.getByLabel("Justificativa de concorrência", { exact: true }).fill("Preços fictícios comparáveis");
  await plano.getByRole("button", { name: "Salvar planejamento" }).click();
  const cartao = page.getByRole("article", { name: "Kit fictício 3 incensos + suporte" });
  await expect(cartao).toContainText("Pronto");
  await expect(cartao).toContainText("R$ 120,00 · 12,0% do orçamento");
  await expect(cartao).toContainText("R$ 14,33");
  await expect(cartao).toContainText("23,9%");
  await expect(cartao.getByRole("listitem")).toHaveText([
    "✓ Fornecedor: cumprido", "✓ Produto: cumprido", "✓ Margem: cumprido",
    "✓ Demanda: cumprido", "✓ Concorrência: cumprido", "✓ Estoque: cumprido",
  ]);

  // O Painel reflete o plano.
  await tela(page, "Painel");
  await expect(page.getByText("Prontos para comprar").locator("..")).toContainText("1");
  await expect(page.getByText("Orçamento comprometido").locator("..")).toContainText("R$ 120,00");

  // Sair encerra a sessão no servidor.
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
  expect((await page.request.get("/api/painel")).status()).toBe(401);
});
