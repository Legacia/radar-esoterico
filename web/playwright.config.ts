// Teste de ponta a ponta: sobe a API com a interface montada (web/dist), num banco temporário com
// conta fictícia (tests/servidor_e2e.py), e percorre o fluxo principal num navegador de verdade.
// Antes de rodar: npm run build. Comando: npm run e2e.
import { defineConfig, devices } from "@playwright/test";

const PORTA = 8599;
// Relativo à raiz do projeto, que é a pasta onde o servidor roda (cwd abaixo).
const python = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  retries: 0,
  reporter: "list",
  use: { baseURL: `http://127.0.0.1:${PORTA}`, locale: "pt-BR", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `${process.env.RADAR_PYTHON ?? python} -m tests.servidor_e2e`,
    cwd: "..",
    url: `http://127.0.0.1:${PORTA}/`,
    env: { RADAR_E2E_PORTA: String(PORTA) },
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
