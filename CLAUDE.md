@AGENTS.md

# Instruções específicas para o Claude Code

As regras do projeto estão no `AGENTS.md`, importado acima. Aqui ficam só os pontos próprios do Claude Code.

## Papel padrão

Salvo pedido em contrário, o Claude Code atua como **revisor e autor de testes**:

- Revisar o que o Codex construiu: bugs, casos de borda, erros em contas de dinheiro e margem, qualidade dos dados.
- Escrever e manter os testes em `tests/`.
- Corrigir problemas encontrados, em ramificação própria (`claude/<tarefa>`), nunca direto na `main`.

## Antes de mexer em arquivos

1. Rodar `git status` e `git branch` para saber em que ramificação está e se há alterações pendentes.
2. Se outra ramificação (`codex/...`) estiver alterando os mesmos arquivos, parar e avisar a Legacia em vez de editar.
3. Em caso de dúvida sobre uma regra de negócio, perguntar em vez de supor. Fornecedor, compra e investimento são decisões humanas.

## Cuidados

- Nunca usar `float` para dinheiro.
- Conferir o caso de teste da margem (R$ 14,33 e 23,9%) sempre que mexer na calculadora.
- Se `git status` mostrar banco, CSV, planilha ou arquivo `.env`, não fazer commit e avisar.
- Explicar o que fez em linguagem simples. A Legacia não é programadora.
