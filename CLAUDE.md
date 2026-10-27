@AGENTS.md

# Instruções específicas para o Claude Code

As regras do projeto estão no `AGENTS.md`, importado acima. Aqui ficam só os pontos próprios do Claude Code.

## Papel padrão

Desde 27/10/2026, por decisão do Legacia, os papéis estão invertidos: o Claude Code **constrói** e o Codex **revisa**. O Claude Code:

- Constrói as funcionalidades: regras em `radar/`, API em `radar/api/` e interface React em `web/`.
- Escreve os testes (`tests/` com pytest; `web/tests/` com Vitest e Playwright) junto com cada mudança, não depois.
- Confere o próprio trabalho antes de entregar à revisão: bugs, casos de borda, contas de dinheiro e margem, rotas sem login.
- Trabalha sempre em ramificação própria (`claude/<tarefa>`), nunca direto na `main`. Cada etapa vira um pull request aberto pelo próprio Claude Code (`gh pr create`), com a descrição no modelo `.github/pull_request_template.md`. O Codex revisa automaticamente ao abrir o PR; se não revisar, pedir com um comentário `@codex review` no PR. O Legacia não precisa repassar nada.
- Depois de abrir o PR, vincular o PR à sessão e ligar o Auto-fix do aplicativo, para ser acordado quando chegar a revisão do Codex ou quando os testes do GitHub falharem. Avaliar cada comentário do Codex, corrigir na própria ramificação e responder no PR o que foi aceito ou contestado, em português simples.
- Não altera arquivos de uma ramificação enquanto o Codex a revisa (`codex/revisao-<tarefa>`). Ao receber a revisão, avalia cada apontamento e explica ao Legacia o que aceita ou contesta.
- Mescla sozinho, sem pedir autorização (o Legacia não mescla), seguindo as cinco condições de "Mesclagem pelos agentes" no AGENTS.md: revisão do Codex concluída, apontamentos avaliados, testes passando na versão mesclada, nada de dados ou segredos no diff e nenhuma pergunta de negócio em aberto.
- Depois de mesclar na `main`, conta ao Legacia o que entrou, em linguagem simples.

## Antes de mexer em arquivos

1. Rodar `git status` e `git branch` para saber em que ramificação está e se há alterações pendentes.
2. Partir de uma `main` atualizada e criar a ramificação da tarefa.
3. Em caso de dúvida sobre uma regra de negócio, perguntar em vez de supor. Fornecedor, compra e investimento são decisões humanas.

## Cuidados

- Nunca usar `float` para dinheiro, nem em Python nem no TypeScript (no React, dinheiro chega da API como texto decimal ou centavos inteiros).
- Não reimplementar no React nenhuma regra de margem, compra ou promoção: a tela mostra o que a API calculou.
- Conferir o caso de teste da margem (R$ 14,33 e 23,9%) sempre que mexer na calculadora, na API ou na tela correspondente.
- Toda rota nova da API exige sessão; o teste que percorre as rotas deve continuar passando.
- Se `git status` mostrar banco, CSV, planilha, arquivo `.env`, `node_modules/` ou `web/dist/`, não fazer commit e avisar.
- Antes de dizer que uma tela está pronta, abrir no navegador com dados fictícios em banco temporário e conferir; nunca usar o banco real `data/radar.db` para testes.
- Explicar o que fez em linguagem simples. O Legacia não é programador.
