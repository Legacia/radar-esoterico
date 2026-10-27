## O que muda

<!-- Em linguagem simples, para o Legacia. -->

## Etapa do plano

<!-- Ex.: Migração para React, etapa 1 (API com login). -->

## O que o revisor deve conferir com atenção

<!-- Pontos de risco desta mudança. As regras gerais estão em "Review guidelines" no AGENTS.md. -->

## Como testar

```
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Conferido pelo autor

- [ ] Testes passando localmente
- [ ] Nenhum `float` para dinheiro; caso da margem (R$ 14,33 / 23,9% / R$ 55,56) intacto
- [ ] Toda rota nova da API exige sessão
- [ ] Nenhum banco, CSV real, planilha, `.env`, segredo, `node_modules/` ou `web/dist/` no diff
- [ ] Perguntas de negócio em aberto listadas abaixo (ou "nenhuma")

## Perguntas para o Legacia

Nenhuma.
