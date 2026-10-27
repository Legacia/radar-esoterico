# Radar Esotérico

Ferramenta local de inteligência comercial para a **Tenda da Bruxa 2.0**: venda de produtos esotéricos em marketplaces (Mercado Livre, Shopee etc.), com estoque próprio, como renda extra.

Este arquivo é a fonte única de regras do projeto. Vale para o Claude Code, para o Codex e para qualquer pessoa que mexa no código. Em caso de dúvida entre este arquivo e uma instrução solta, siga este arquivo e avise o responsável.

## Quem decide o quê

- **Legacia** cuida do Radar, da inteligência comercial, da negociação e do acompanhamento financeiro.
- **Anna** cuida da curadoria, da avaliação de qualidade, da identidade da loja e da composição de kits. Ela já teve a Tenda da Bruxa (incensos, amuletos, colares, cristais, caldeirões).
- Os dois aprovam fornecedores, definem o estoque e decidem os investimentos.
- Nenhum agente de IA decide compra, fornecedor ou investimento. A ferramenta mostra dados e critérios; a decisão é humana.

## Decisões já tomadas

- Modelo operacional: estoque próprio.
- Projeto em paralelo ao trabalho atual dos dois.
- Critérios do mix inicial: boa margem por unidade e produtos fáceis de enviar e armazenar.
- Orçamento do primeiro lote de estoque: até R$ 1.000.
- Radar: rodando localmente, "nada muito complexo". Cada funcionalidade nova deve servir a uma decisão comercial real.
- Meta do primeiro mês: três produtos com fornecedores verificados, margem defensável e potencial de venda sustentado por evidências. Não é meta ter 100 produtos cadastrados nem muitos gráficos.

## Escopo do MVP 0.1

Dentro:

- Cadastro e controle de **fornecedores** (ver ciclo abaixo)
- **Produtos** e **SKUs** de fornecedor
- Histórico de **anúncios** e preços observados
- **Importação CSV**
- **Calculadora de margem**
- **Decisão de compra** (checklist de critérios)
- **Painel** inicial
- **Acesso pela rede local** (servidor que aceita outros computadores da rede, SQLite em modo WAL, instruções de uso)
- **Login simples** com e-mail e senha, obrigatório antes de abrir qualquer tela (ver "Acesso pela rede")
- Testes automatizados

Fora (não implementar sem pedido explícito):

- Nuvem, aplicativo mobile, múltiplos usuários com perfis, integração com IA em tempo real
- Perfis e permissões diferentes por usuário, cadastro aberto de novos usuários, recuperação de senha por e-mail e login social (Google etc.). O login simples com e-mail e senha está **dentro** do escopo.
- Coleta automática agressiva de marketplaces

## Stack

- Python, aplicação única com módulos bem separados
- Interface: **React + TypeScript**, montada com **Vite** (decisão do Legacia em 27/10/2026, substituindo o Streamlit antes do início do uso real)
- API: **FastAPI** em Python, servida por Uvicorn. A mesma aplicação entrega a API (`/api/...`) e os arquivos já montados da interface, numa porta só
- Coleta e tratamento: `requests` + `pandas`
- Banco: SQLite (arquivo único em `data/`, com modo WAL ligado)
- Gráficos: SVG desenhado nos próprios componentes React, sem biblioteca de gráficos, cada um com tabela alternativa (padrão da referência visual)
- Execução: local, pelo navegador. **O acesso por outros computadores da mesma rede entra na primeira versão** (decisão do Legacia): o Radar roda num computador "servidor" e os outros abrem o endereço dele no navegador (algo como `http://192.168.0.10:8501`; a porta 8501 foi mantida). Continua sem nuvem. Detalhes na seção "Acesso pela rede".
- Agendamento: agendador do sistema operacional, só depois

## Estrutura de pastas

A pasta raiz do projeto, no computador do Legacia, é `E:\Projetos\RadarEsoterico` (repositório `radar-esoterico` no GitHub). A divisão interna abaixo é a proposta vigente; a entrada da API é `radar/api/` e a da interface é `web/src/main.tsx`. Mudanças na estrutura devem ser registradas aqui.

```
web/            interface React + TypeScript (Vite); uma página por tela em web/src/paginas/
  dist/         interface montada para uso (gerada pelo build, fora do Git)
radar/          regras de negócio, sem código de interface
  api/          FastAPI: rotas finas que só chamam as regras, login e sessão por cookie
  banco/        conexão, criação de tabelas, consultas
  margem/       calculadora e parâmetros
  fornecedores/ ciclo de vida e checklist de promoção
  importacao/   leitura de CSV
  conectores/   fontes de dados (desacoplados, nada trava se faltarem)
tests/          testes automatizados (pytest: regras e API)
web/tests/      testes da interface (Vitest para componentes; Playwright para o fluxo no navegador)
exemplos/       CSVs de exemplo, sem dados reais
data/           banco real (fora do Git)
backups/        backups (fora do Git)
```

Regra: a lógica de negócio fica em `radar/`. A API em `radar/api/` só recebe, valida o formato e chama essas funções; a interface em `web/` só chama a API. **Nenhuma conta de dinheiro, margem, critério de compra ou promoção é refeita no React**: a tela mostra o que a API devolveu. Isso permite testar tudo sem abrir a interface e evita duas versões da mesma regra.

Dinheiro entre API e interface trafega como **texto decimal** (`"59.90"`) ou centavos inteiros, nunca como número de ponto flutuante do JavaScript. A formatação `R$ 1.234,56` é feita na tela.

## Telas

1. **Painel**: indicadores, progresso do plano de 30 dias, funil de fornecedores, pendências com responsável.
2. **Fornecedores**: lista por etapa, ficha, SKUs cotados, checklist de promoção, histórico de contatos.
3. **Produtos e SKUs**: catálogo dos candidatos, ligado às cotações.
4. **Pesquisa de oportunidades**: busca, anúncios e preços, margem por anúncio a partir do custo do fornecedor, preço mínimo para atingir a margem-alvo. Abas: Pesquisa, Preços, Margens.
5. **Kits**: composição por produto, estoque controlado por componente.
6. **Decisão de compra**: orçamento, reserva, critérios por produto, quantidade e valor comprometido.
7. **Importar**: CSV.

## Modelo de dados

Tabelas: `fornecedor`, `interacao`, `sku_fornecedor`, `produto`, `anuncio`, `preco_observado`, `kit`, `kit_item`, `cenario_margem`, `usuario`, `tarefa`.

`tarefa` guarda as tarefas do plano de 30 dias para o Painel (aprovada pelo Legacia em 26/10/2026).

`usuario` guarda nome, e-mail (único) e `senha_hash`. Nada além disso.

Pontos que importam:

- `sku_fornecedor` liga `fornecedor` a `produto` e guarda código, custo unitário, quantidade mínima e **data da cotação**. O mesmo produto pode ter cotações de vários fornecedores.
- Toda cotação e todo preço observado guardam a data. Preço de atacado muda; é preciso saber a idade do número.
- `fornecedor` guarda status, CNPJ, contato, pedido mínimo, prazo e condição de pagamento, motivo do descarte e data em que virou oficial.
- `interacao` é o histórico de contatos (data, canal, resumo).
- Kits são montados a partir de produtos (`kit_item` com quantidade), para o estoque ser controlado por componente.

## Ciclo do fornecedor

Etapas: **Descoberto → Em contato → Cotado → Em avaliação → Fornecedor oficial**. Em qualquer etapa pode ir para **Descartado ou pausado**, sempre com motivo.

Promoção a oficial exige tudo isto:

- CNPJ e condições comerciais verificados
- Emissão de nota fiscal
- Especificações, procedência e qualidade conferidas (amostra avaliada pela Anna)
- Margem em cenário conservador positiva, com alvo inicial de 20% de contribuição
- Reposição confirmada

Regra da margem na promoção (decisões do Legacia em 26/10/2026):

- A margem precisa atingir o alvo configurado, nunca abaixo de 20%, em pelo menos **três produtos diferentes** do fornecedor. Vários códigos do mesmo produto contam como um só, pela melhor margem entre eles.
- Vale a cotação mais recente de cada código. Códigos que só diferem em maiúsculas e minúsculas são o mesmo código.
- Cotação mais antiga que o limite configurado gera aviso na tela, mas **não** impede a promoção.

O sistema nunca promove sozinho. O botão fica disponível, mas lista o que falta e não muda o status enquanto o checklist estiver incompleto. A data da promoção é registrada.

## Cálculo de margem

Fórmula, por venda:

```
contribuicao = preco - custo
             - preco * comissao_pct
             - tarifa_fixa
             - embalagem
             - preco * tributo_pct
             - outros
margem_pct = contribuicao / preco
```

Preço mínimo para uma margem-alvo `m`:

```
preco_min = (custo + tarifa_fixa + embalagem + outros)
            / (1 - comissao_pct - tributo_pct - m)
```

Parâmetros de exemplo (todos **editáveis** na tela, nunca fixos no código):

- Comissão: 20% (Shopee, estimativa, sujeita a confirmação na conta)
- Tarifa fixa: R$ 4,50
- Embalagem: R$ 2,50
- Tributo: 6%, provisão ilustrativa. **Não é enquadramento fiscal.** Cada pessoa configura o percentual que valer para ela.
- Outros (publicidade, perdas): R$ 3,00
- Margem-alvo inicial: 20%

Caso de teste obrigatório: kit de 3 incensos + suporte, preço R$ 59,90, custo R$ 20,00, com os parâmetros acima, dá contribuição de **R$ 14,33** e margem de **23,9%**.

Frete e despesas fixas não entram neste cálculo. Vender 100 kits não significa ganhar R$ 1.433 líquidos.

## Critérios para autorizar a compra do primeiro estoque

O Radar mostra, por produto, se cada critério está cumprido:

1. **Fornecedor:** CNPJ e condições verificados, nota fiscal. *(automático)*
2. **Produto:** especificações, procedência e qualidade conferidas. *(automático, a partir do cadastro)*
3. **Margem:** cenário conservador positivo, alvo de 20%. *(automático)*
4. **Demanda:** indícios verificáveis de procura, não só anúncios publicados. *(confirmação manual)*
5. **Concorrência:** preço competitivo sem depender de desconto permanente. *(confirmação manual)*
6. **Estoque:** lote pequeno e capital de reposição preservado. *(automático)*

Regra provisória: não comprometer mais de **20% do orçamento** de estoque (R$ 200 num lote de R$ 1.000) em um produto ainda não validado. Kits são controlados por componente, para não causar ruptura.

Não comprar só porque o fornecedor oferece desconto: antes, descobrir se o preço de aquisição permite competir com os anúncios existentes.

## Coleta de dados e métricas

- Fontes iniciais: recursos oficiais do Mercado Livre (`/trends`, atualizado semanalmente, e `/highlights`, mais vendidos por categoria), cadastro manual e importação de CSV. Antes de qualquer módulo automático, verificar os limites de acesso.
- O conector de API fica **desacoplado**: o sistema inteiro funciona sem ele.
- Não confundir métricas: ranking de buscas indica interesse, não pedidos; ranking de mais vendidos indica posição, sem quantidades; preço anunciado não garante compra; queda de preço não significa queda de demanda. A interface deve mostrar esses sinais separados do cálculo de margem.

## Convenções de código

- Dinheiro: `Decimal` ou centavos inteiros. **Nunca `float`** para valores em reais.
- Percentuais: guardar como fração (0,20) e formatar só na tela.
- Interface em português do Brasil. Valores como `R$ 1.234,56`, datas como `26/10/2026`.
- Nomes de tabelas e colunas em português, sem acento, como no modelo acima.
- Datas no banco em formato ISO (`AAAA-MM-DD`).
- Funções pequenas, com testes. Toda regra de margem e de promoção de fornecedor tem teste automatizado.
- Dados de exemplo só em `exemplos/`, sem informação real de fornecedor.

## Dados e segurança

- O repositório é **privado**, mas mesmo assim: banco, backups, CSVs, planilhas e chaves **nunca** entram no Git. O `.gitignore` já cobre isso. Se um arquivo desses aparecer no `git status`, pare e avise.
- Nunca colocar senha, chave de API ou token no código. Usar arquivo `.env` (fora do Git); só o `.env.example`, em branco, sobe.
- Backup do banco é feito fora do Git.

## Acesso pela rede

Decisão do Legacia: entra na primeira versão. Uso previsto: duas pessoas (Legacia e Anna), em casa, na mesma rede.

- Um computador é o **servidor**: roda o Radar e guarda o arquivo do banco. Os outros só abrem o endereço no navegador. O servidor precisa estar ligado, com o Radar aberto.
- O servidor (Uvicorn) aceita conexões da rede (`0.0.0.0`) na porta fixa 8501, configurável sem segredos. Documentar no README como descobrir o endereço do servidor. No uso normal não roda servidor de desenvolvimento do Vite: a interface montada (`web/dist`) é servida pela própria API.
- O Windows pede liberação no firewall na primeira execução. Liberar **somente para rede privada**, nunca para rede pública.
- SQLite com modo **WAL** ligado e `busy_timeout` configurado, para duas pessoas usarem ao mesmo tempo sem erro de "banco travado". Gravações devem ser curtas.
- O banco **nunca** é copiado para os outros computadores: existe um só, no servidor.
- **Login simples (decisão do Legacia):** e-mail e senha, pedidos antes de qualquer tela. O e-mail serve só como identificador de quem entra; o sistema **não envia e-mails**.
  - Contas são criadas pelo Legacia, por um comando de linha no servidor (por exemplo `python -m radar.usuarios criar`). Não existe tela de cadastro aberto.
  - A senha é guardada **somente como hash** (bcrypt ou argon2), na tabela `usuario`. Nunca em texto, nunca no código, nunca no Git.
  - Senha esquecida: o Legacia redefine pelo mesmo comando no servidor. Sem recuperação por e-mail.
  - Sem bloqueio por tentativas de senha erradas (decisão do Legacia em 27/10/2026).
  - A sessão dura no máximo **8 horas** desde a entrada, sem prorrogação por atividade (aprovado pelo Legacia em 26/10/2026). O valor fica em `radar/sessoes.py`.
  - "Simples" significa sem perfis e sem permissões diferentes: quem tem conta vê tudo. Mas o login é de verdade: sessão por usuário em **cookie `HttpOnly` e `SameSite=Strict`**, com o identificador da sessão aleatório e guardado no servidor. **Toda rota da API**, exceto entrar, verifica a sessão antes de devolver qualquer dado; a interface só esconde telas, quem protege os dados é a API. Sair e expirar invalidam a sessão no servidor.
  - Limite conhecido: na rede local a conexão é HTTP, sem criptografia. Aceitável em rede doméstica protegida; reavaliar se a rede deixar de ser só de vocês.
  - Nenhum agente de IA cria contas reais nem escolhe senhas. Para testes, usar contas fictícias criadas só no banco de teste.
- O endereço do Radar não deve ser exposto à internet (nada de redirecionamento de porta no roteador). O login protege contra quem está na mesma rede, não contra a internet aberta.
- Backup do arquivo do banco continua sendo feito no servidor, fora do Git.

## Como trabalhar com Git

- `main` guarda só código revisado e funcionando. Nada de commit direto na `main`.
- **Papéis invertidos (decisão do Legacia em 27/10/2026):** o **Claude Code constrói** (regras, API, interface React e os testes de cada mudança); o **Codex revisa** (bugs, casos de borda, erros em contas de dinheiro e margem, rotas sem login, qualidade dos dados) e acrescenta testes que faltarem. As mesclagens são feitas pelos agentes, conforme as regras abaixo.
- Ramificações: `claude/<tarefa>` para construção. Na revisão automática o Codex só comenta no pull request, e as correções são feitas pelo Claude Code na própria `claude/<tarefa>`. Se o Codex for chamado para corrigir algo (comentário `@codex` no pull request), ele usa `codex/revisao-<tarefa>`, criada a partir da ramificação revisada e enviada como pull request contra ela. As ramificações `codex/mvp-...` antigas são só histórico.
- Tudo entra por pull request revisado pelo Codex.
- **Mesclagem pelos agentes (decisão do Legacia em 27/10/2026: "eu não vou mesclar nada, façam isso vocês").** O Legacia não mescla; os agentes mesclam sozinhos, sem pedir autorização a cada vez, desde que:
  1. O Codex tenha concluído a revisão e registrado o relato no pull request (revisão automática do GitHub, ver "Review guidelines"). Os testes automáticos do GitHub (Actions) também precisam ter passado no pull request.
  2. O Claude Code tenha avaliado cada apontamento: os erros confirmados estão corrigidos e os pontos contestados estão explicados no pull request.
  3. Todos os testes passem (`pytest`, e os testes da interface quando existirem), `pip check` não acuse problema e `git diff --check` esteja limpo, na versão já mesclada.
  4. Nenhum banco, CSV real, planilha, `.env`, segredo, `node_modules/` ou `web/dist/` esteja no diff.
  5. Nenhuma pergunta de regra de negócio esteja em aberto. Perguntas de negócio continuam sendo do Legacia; enquanto houver uma sem resposta, a parte afetada não entra na `main`.
- Quem mescla: o **Claude Code** mescla a `codex/revisao-<tarefa>` na `claude/<tarefa>` depois de avaliar a revisão, e depois a `claude/<tarefa>` na `main`. O Codex não mescla na `main`.
- Depois de cada mesclagem na `main`, o Claude Code conta ao Legacia, em linguagem simples, o que entrou e o que mudou para ele.
- Nunca usar força (`--force`) na `main`, nunca apagar histórico e nunca mesclar algo com teste falhando para "resolver depois".
- **Dois agentes nunca editam os mesmos arquivos ao mesmo tempo.** Enquanto o Codex revisa uma ramificação, o Claude Code não altera os mesmos arquivos; correções pequenas da revisão ficam na `codex/revisao-<tarefa>`; correções maiores são feitas pelo Claude Code depois que a revisão termina.
- O revisor relata o que encontrou em linguagem simples no pull request. Mudança de regra de negócio nunca é feita na revisão: vira pergunta para o Legacia.
- Mensagens de commit curtas, em português, dizendo o que mudou.
- As tarefas do plano de 30 dias viram Issues no GitHub, com responsável e semana.

## Comandos (a confirmar quando o projeto existir)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd web; npm install; npm run build; cd ..
python -m radar.servidor          # sobe API + interface em http://localhost:8501
pytest
cd web; npm test                  # testes da interface
```

Desenvolvimento da interface: `npm run dev` dentro de `web/` (Vite com recarga automática, apontando para a API local). Node.js LTS é necessário só para montar e testar a interface; quem apenas usa o Radar no outro computador precisa só do navegador.

No Windows deste projeto, `py` e `python` funcionam (Python 3.13).

## Pontos em aberto

- Login: quantas contas existirão no início (previsto: Legacia e Anna, cada um com o próprio e-mail e a própria senha).
- Lista dos 20 produtos candidatos e dos links de anúncios
- Resposta dos fornecedores. Os cinco listados no planejamento (Brasil Esotérico Atacado, Baú da Bruxa, Mandala Esotérica Atacado, Encantos do Mundo, Flute Incensos) são pontos de partida para cotação, **não** parceiros aprovados, e os dados deles não foram verificados.

## Estrutura e esquema implementados no Bloco 1

- `radar/banco/esquema.py` contém as migrações; `PRAGMA user_version` controla a versão (inicial: 1). Dinheiro usa colunas `*_centavos` inteiras; percentuais usam texto decimal para futura leitura por `Decimal`.
- `tarefa` guarda `id`, `titulo`, `semana` (1 a 4), `responsavel` e `concluida` (0 ou 1), para o painel do Bloco 3.
- `fornecedor` inclui os campos de verificação `cnpj_verificado`, `condicoes_verificadas`, `emite_nota`, `amostra_avaliada` e `reposicao_confirmada`; `produto` inclui `especificacoes_conferidas`, `procedencia_conferida` e `qualidade_conferida`. São registros para as regras dos próximos blocos, ainda sem promoção ou decisão de compra.
- `radar/usuarios.py` gerencia contas e autenticação; `radar/sessoes.py` controla a duração da sessão. `app/acesso.py` concentra a barreira de login; `app/painel.py` a aplica também diretamente na página.
- `radar/conectores/base.py` define somente o contrato opcional de marketplace; não há implementação de coleta.

## Estrutura e esquema implementados no Bloco 2

- Migração 2 acrescenta `sku_fornecedor.preco_venda_centavos` (opcional): preço conservador informado manualmente para estimar margem, sem se confundir com os preços observados do Bloco 3. Histórico de cotações preservado; a cotação atual é a mais recente por fornecedor e código (sem diferenciar maiúsculas), com desempate por id.
- Nova tabela `configuracao`, com uma linha compartilhada: comissão, tributo e margem-alvo como frações em texto decimal; tarifa fixa, embalagem e outros em centavos inteiros; limite de cotação antiga em dias. Valores iniciais ficam em `radar/margem/padroes.toml`; edição pela tela, sem modificar fórmulas.
- `radar/margem/` implementa fórmulas e configuração; `radar/fornecedores/regras.py` o checklist puro; `radar/fornecedores/__init__.py` as ações persistidas; `radar/produtos.py` catálogo e cotações; `radar/valores.py` validação e apresentação de valores/datas.
- Novas telas protegidas: `app/fornecedores.py`, `app/catalogo.py`, `app/calculadora.py`. Componentes comuns de apresentação em `app/componentes.py`.

## Estrutura e esquema implementados no Bloco 3

- Migração 3 preserva as anteriores. Novas tabelas: `orcamento` (linha única, total e reserva em centavos) e `plano_compra` (uma linha por produto, cotação escolhida, quantidade, preço conservador e confirmações/justificativas de demanda e concorrência).
- `produto` recebe `validado`, `justificativa_validacao` e `estoque_atual` por componente; validação é manual e exige justificativa, conforme decisão do Legacia nesta conversa. `interacao.situacao_resposta` opcional distingue aguardando/recebida; dados antigos ficam sem classificação.
- `kit_item.sku_fornecedor_id` registra a cotação de custo do componente; `kit.quantidade_planejada` permite somar necessidades de componentes compartilhados sem baixa automática de estoque.
- Novos módulos de negócio: `radar/mercado.py`, `radar/compras.py`, `radar/kits.py`, `radar/painel.py` e importador em `radar/importacao/`. Telas protegidas em `app/pesquisa.py`, `app/importar.py`, `app/compras.py`, `app/kits.py`; `app/painel.py` passa a mostrar os indicadores, tarefas e pendências.
- Único CSV de exemplo: `exemplos/anuncios_ficticios.csv`, sem informação real. Formato e decisões confirmadas sobre critérios de compra, estoque e pendências estão documentados no README.

## Interface (revisão visual de 27/10/2026)

- Primeira decisão (manhã de 27/10/2026): manter o Streamlit com o visual da referência. **Substituída no mesmo dia**: o Legacia decidiu migrar para React antes do início do uso real. O visual abaixo continua sendo o padrão e passa a ser aplicado no React.
- Referência: projeto ERT Engagement Monitor (shell com barra lateral escura, painéis, selos, gavetas laterais para detalhes, tabelas ordenáveis, gráficos clicáveis com tabela alternativa, filtros no endereço `#/pagina?filtro=valor`). Textos da interface em português do Brasil.
- Tokens de cor (em CSS no React): fundo `#f3f5f8`, painéis brancos, barra lateral escura `#19222e`, cor principal `#24406f`, fonte IBM Plex Sans (com Segoe UI de reserva, se não houver internet) e cores de selo (verde cumprido, laranja pendente, vermelho crítico, amarelo atenção, cinza neutro).
- Na versão Streamlit, `app/componentes.py` e `app/navegacao.py` implementaram esse padrão; servem de referência até a interface React substituir a pasta `app/`.
- Sem biblioteca de componentes visuais pronta (estilo próprio, como na referência). Acessibilidade: foco visível pelo teclado, Esc fecha gavetas, gráficos com `aria-label` e tabela alternativa.
- Navegação agrupada em seções: Visão geral, Fornecimento, Mercado e Decisão.
- Pesquisa de oportunidades é **simulação livre** (decisão do Legacia em 27/10/2026): usa a margem-alvo configurada, mesmo abaixo de 20%. Promoção de fornecedor, decisão de compra e pendências do Painel continuam exigindo o piso de 20%.

## Migração para React (decisão de 27/10/2026)

O Legacia decidiu migrar a interface para React antes de começar o uso real. O Claude Code constrói cada etapa e o Codex revisa. Regras da migração:

- **As regras de negócio em `radar/` não mudam** e seus testes continuam valendo. A migração troca só a interface e acrescenta a API.
- Ordem de trabalho, cada etapa em ramificação e pull request próprios:
  1. API FastAPI com login, sessão por cookie e todas as rotas protegidas, com testes em pytest (inclusive o teste que confere que toda rota exige sessão).
  2. Esqueleto React: shell, tema, login, navegação e componentes comuns (painel, selo, tabela, gaveta, aviso, notificação).
  3. Telas, uma por vez: Painel, Fornecedores, Produtos e SKUs, Calculadora, Pesquisa, Importar, Kits, Decisão de compra.
  4. Teste de ponta a ponta no navegador (Playwright) do fluxo principal e do caso da margem (R$ 14,33 e 23,9%).
  5. Retirar a pasta `app/` e o Streamlit só depois que todas as telas React estiverem aprovadas.
- Enquanto a migração não termina, a versão Streamlit da `main` continua funcionando. O banco é o mesmo; a API não muda o esquema sem nova migração.
- Novas dependências entram fixadas por versão (`requirements.txt` e `package-lock.json`).

## Review guidelines

Seção lida pelo Codex na revisão automática de pull requests no GitHub (processo automatizado decidido pelo Legacia em 27/10/2026). Escreva a revisão em **português do Brasil**, em linguagem simples: o Legacia não é programador.

Como revisar cada pull request do Claude Code:

- Leia a descrição do pull request: ela diz o que mudou, o que conferir e como testar.
- Separe o relato em três grupos: **erros confirmados** (com o arquivo, a linha e um exemplo concreto que falha), **riscos** e **sugestões**. Não marque como erro o que é só preferência de estilo.
- Prioridade máxima (trate como P0/P1):
  - Dinheiro com `float`, em Python ou TypeScript; arredondamento errado; o caso obrigatório da margem deixando de dar R$ 14,33, 23,9% e preço mínimo R$ 55,56.
  - Regra de negócio diferente do AGENTS.md: promoção de fornecedor (três produtos diferentes, piso de 20%, cotação mais recente por código sem diferenciar maiúsculas), critérios de compra, limite de 20% do orçamento para produto não validado, pendências do painel.
  - Regra de margem, compra ou promoção recalculada no React em vez de vir da API.
  - Rota da API que funcione sem sessão (só `POST /api/entrar` pode), cookie sem `HttpOnly`/`SameSite=Strict`, sessão que passe de 8 horas ou que seja prorrogada pelo uso, senha fora de hash, mensagem de login que revele se o e-mail existe.
  - Migração de banco publicada que tenha sido editada, ou mudança de esquema sem migração nova.
  - Banco, CSV real, planilha, `.env`, chave, senha, `node_modules/` ou `web/dist/` no diff.
- Confira também: casos de borda (valores vazios, zero, negativos, datas futuras, textos com acento), mensagens de erro em português, testes que realmente testam o que dizem, telas protegidas por login, acessibilidade básica (foco pelo teclado, rótulos).
- Fora do escopo do MVP (nuvem, perfis de usuário, cadastro aberto, recuperação de senha por e-mail, coleta automática agressiva de marketplaces) é erro, não sugestão.
- Se algum ponto depender de uma decisão de negócio, **não proponha a mudança como correção**: registre como "Pergunta para o Legacia".
- Não aprove nem mescle: quem mescla é o Claude Code, depois de avaliar a revisão (ver "Mesclagem pelos agentes").
