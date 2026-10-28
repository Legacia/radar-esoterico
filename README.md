# Radar Esotérico — MVP 0.1

Ferramenta local de inteligência comercial da Tenda da Bruxa 2.0: login, fornecedores, produtos,
cotações, mercado, margem, planejamento de compras, kits e painel. Interface em React, servida pela
própria API (FastAPI) no computador servidor; os outros computadores da casa só usam o navegador.

## Instalar no servidor (Windows, Python 3.13 e Node.js LTS)

Abra o PowerShell e execute uma linha de cada vez:

```powershell
cd E:\Projetos\RadarEsoterico
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd web
npm.cmd ci
npm.cmd run build
cd ..
```

Os comandos usam o Python do ambiente diretamente, sem precisar ativar scripts no PowerShell.
No PowerShell, use `npm.cmd` (e `npx.cmd`) em vez de `npm`: o PowerShell bloqueia o atalho `npm`
por padrão, e `npm.cmd` funciona sem mudar a segurança do Windows. O Node.js só é necessário no
servidor, para montar a interface (`web/dist`, fora do Git). Depois de cada `git pull`, rode de novo
`npm.cmd run build` dentro de `web`.

## Criar conta e abrir

```powershell
cd E:\Projetos\RadarEsoterico
.\.venv\Scripts\python.exe -m radar.usuarios criar
.\.venv\Scripts\python.exe -m radar.servidor
```

Informe nome, e-mail e uma senha de pelo menos 8 caracteres. A senha é solicitada duas vezes,
sem aparecer na tela. Não passe senhas como argumentos. O comando só é necessário para a
**primeira** conta: depois, quem já entrou cria as outras na tela **Contas** (Visão geral). Não há
cadastro aberto (quem não tem conta não consegue se cadastrar sozinho) nem envio de e-mails.

Abra http://localhost:8501 no navegador, entre com a conta criada e veja o Painel. Para desligar o
servidor, aperte `Ctrl + C` na janela do PowerShell. Para aceitar só este computador, use
`--endereco 127.0.0.1`; para outra porta, `--porta 8502`.

O botão **Sair** encerra a sessão. O login dura no máximo **8 horas desde a entrada**, sem
prorrogação pelo uso. A sessão fica guardada no servidor; o navegador recebe só um código num
cookie `HttpOnly` e `SameSite=Strict`. Reiniciar o servidor exige novo login. Cada navegador entra
separadamente.

Para trocar uma senha, use **Contas → Trocar senha**. As sessões abertas com a senha antiga
(em outros navegadores) são encerradas na hora; quem trocou a própria senha continua conectado.
Se ninguém conseguir entrar, redefina no servidor:

```powershell
.\.venv\Scripts\python.exe -m radar.usuarios redefinir
```

Pelo comando, a senha anterior deixa de funcionar para novos logins, mas sessões já abertas
continuam até sair ou completar as 8 horas. Para encerrá-las imediatamente, reinicie o servidor.

## Usar em outro computador da casa

1. Deixe o servidor ligado, com o Radar rodando.
2. No PowerShell do servidor, execute `ipconfig` e procure o endereço IPv4 da conexão ativa.
3. No outro computador, abra `http://ENDERECO_IPV4:8501` (exemplo: `http://192.168.0.10:8501`).
4. Entre com sua conta. Todos os usuários têm o mesmo acesso.

Se o Windows pedir permissão de firewall, libere **somente rede privada**.
Não exponha a porta à internet nem configure redirecionamento no roteador.
A conexão doméstica usa HTTP, sem criptografia. Use apenas a rede de casa protegida.
O banco existe somente no servidor: nunca o copie para os computadores que acessam o Radar.

## Testes

```powershell
cd E:\Projetos\RadarEsoterico
.\.venv\Scripts\python.exe -m pytest
cd web
npm.cmd test
```

`pytest` testa as regras de negócio e a API (inclusive que toda rota, exceto entrar, exige login);
`npm.cmd test` testa as telas React. Os testes usam bancos temporários e contas fictícias; não
alteram `data/radar.db`.

Teste de ponta a ponta: abre um navegador de verdade contra a API, com banco temporário e conta
fictícia (`tests/servidor_e2e.py`), e percorre entrar, o caso da margem (R$ 14,33 e 23,9%),
fornecedor, produto, cotação, plano de compra e saída.

```powershell
cd web
npx.cmd playwright install chromium
npm.cmd run build
npm.cmd run e2e
```

O GitHub roda os três (Python, interface e ponta a ponta) em cada pull request.

## Dados e manutenção

`data/radar.db` é criado automaticamente na primeira execução ou criação de conta.
SQLite usa WAL, espera de até 5 segundos em disputas de escrita e chaves estrangeiras.
Dinheiro no banco é armazenado em centavos inteiros; percentuais em texto decimal.
`PRAGMA user_version` controla o esquema; alterações futuras devem acrescentar migrações,
sem editar as já publicadas. Migrações e gravações falhas são revertidas.

**Excluir:** na ficha do fornecedor há **Excluir fornecedor**, e nas tabelas de SKUs (fichas de
fornecedor e de produto) há **Excluir SKU**. Os dois pedem confirmação e não dá para desfazer
(só restaurando um backup). Só some o que não tem histórico ligado: fornecedor com cotações ou
contatos não é excluído (use "Descartado ou pausado"), e SKU usado em kit, plano de compra ou
cenário de margem também não. Excluir um SKU apaga as cotações daquela variação naquele fornecedor.
Fornecedor com item de apoio cadastrado também não é excluído.

### Variações (SKUs) e unidade de venda

Cada produto tem uma ou mais **variações**, e cada variação é um SKU de vocês, com código gerado
pelo Radar (`RAD-000001`, nunca repetido). Na aba **Variações** da ficha do produto você informa
cor e tamanho (opcionais) e a **unidade de venda mínima**: unidade para um caldeirão, caixa para um
incenso. Na cotação, informe o preço como o fornecedor cota e quantas unidades de venda vêm nele:
um pacote com 20 caixas a R$ 60,00 vira custo de R$ 3,00 por caixa, que é o valor usado na margem
(divisões quebradas são arredondadas para cima no centavo). O código do parceiro é opcional.
Produtos já cadastrados ganharam uma variação "unidade" com as cotações que já tinham.

### Itens de apoio e embalagem

Na tela **Itens de apoio** (Fornecimento) ficam caixas, sacolas, papel de seda e outros
materiais de envio, cada um com custo unitário, data da cotação e, se quiser, fornecedor. Na ficha
de cada produto (aba **Embalagem e apoio**) e na tela de cada kit (**Embalagem do kit**), indique
quais itens vão em cada unidade vendida e em que quantidade. A soma substitui a embalagem padrão
da configuração (R$ 2,50) em todas as contas de margem daquele produto: fichas de fornecedor e
de produto, promoção do fornecedor, pendências do Painel, Pesquisa e Decisão de compra. Produto
sem itens indicados continua com a embalagem padrão. O kit usa só os próprios itens, nunca os dos
componentes, porque pode precisar de uma embalagem maior. Mudar o custo de um item muda a margem
de todos os produtos e kits que o usam. Item indicado em algum produto ou kit não é excluído.

Banco, backups, planilhas e segredos ficam fora do Git. `.env.example` está vazio;
esta versão não precisa de variáveis de ambiente. Não há integração real de marketplace.

## Backup

**Automático:** cada vez que o servidor inicia (`python -m radar.servidor`), uma cópia do banco vai
para a pasta `backups/`, com data e hora no nome (ex.: `radar-2026-10-28_093000.db`). Ficam as
**30 cópias mais recentes**; as mais antigas dessa pasta são apagadas sozinhas. Se o backup falhar,
o Radar abre mesmo assim e avisa no terminal. Para iniciar sem a cópia: `--sem-backup`.

**Manual, a qualquer momento, com o Radar aberto ou fechado:**

```powershell
cd E:\Projetos\RadarEsoterico
.\.venv\Scripts\python.exe -m radar.backup
```

Para guardar outra quantidade de cópias: `--manter 60`. A cópia usa o recurso de backup do
próprio SQLite: funciona com as duas pessoas usando o Radar, nunca fica pela metade e é conferida
(`integrity_check`) antes de ser guardada. Não copie o arquivo `data/radar.db` à mão com o Radar
aberto: no modo WAL, parte dos dados recentes fica em outro arquivo.

**Backup diário agendado (opcional):** o Agendador de Tarefas do Windows pode rodar o comando todo
dia. Este comando, rodado uma vez no PowerShell do servidor, cria a tarefa para as 22h:

```powershell
schtasks /Create /SC DAILY /ST 22:00 /TN "Radar Esoterico - backup" /TR "cmd /c cd /d E:\Projetos\RadarEsoterico && .venv\Scripts\python.exe -m radar.backup"
```

A tarefa entra na pasta do projeto antes de rodar (o Agendador começa em outra pasta). Ela só roda
com o computador ligado e a sessão do Windows aberta.

Para remover: `schtasks /Delete /TN "Radar Esoterico - backup"`.

**Cópia fora do computador:** a pasta `backups/` fica no mesmo disco do banco. De tempos em tempos,
copie a pasta para um pen drive ou HD externo guardado em outro lugar; se o disco do servidor
estragar, é essa cópia que salva os dados.

**Restaurar um backup:**

1. Desligue o Radar (`Ctrl + C` na janela do servidor).
2. Na pasta `data`, renomeie `radar.db` para `radar-antes-de-restaurar.db`. Se existirem
   `radar.db-wal` e `radar.db-shm`, renomeie os dois do mesmo jeito (eles pertencem ao banco antigo).
3. Copie o backup escolhido de `backups/` para `data/` e renomeie a cópia para `radar.db`.
4. Inicie o Radar de novo e confira os dados. Só apague `radar-antes-de-restaurar.db` depois.

Código de negócio: `radar/`. API: `radar/api/` (toda rota nova entra no roteador protegido).
Interface: `web/` (React + TypeScript), que só chama a API e não refaz contas de negócio.

## Testar o Bloco 2

1. Abra o Radar, entre com sua conta e use a navegação lateral.
2. Em **Calculadora e parâmetros**, simule preço `59,90` e custo `20,00` com os parâmetros
   iniciais: comissão 20%, tributo 6%, tarifa 4,50, embalagem 2,50, outros 3,00 e alvo 20%.
   O resultado deve ser contribuição **R$ 14,33**, margem **23,9%** e preço mínimo **R$ 55,56**.
3. Em **Fornecedores**, cadastre o fornecedor, condições comerciais e verificações manuais.
   Registre contatos e mude a etapa conforme o acompanhamento real.
4. Em **Produtos e SKUs**, cadastre produtos e lance as cotações do fornecedor. Cada cotação
   registra custo, quantidade mínima e data. Informe também seu preço conservador de venda
   para obter a estimativa de margem; em branco, o SKU não conta no checklist.
5. Na ficha do fornecedor, tente **Promover a fornecedor oficial**: as pendências são exibidas
   sem mudar a etapa. A promoção exige todas as verificações e três produtos diferentes
   com margem no alvo configurado, respeitando o piso de 20% aprovado pelo Legacia.
   Várias variações (SKUs) do mesmo produto contam como um só, pela melhor margem entre as
   cotações atuais delas.
   Descartar ou pausar exige motivo. Nenhuma dessas decisões é automática.

Use dados comerciais somente no banco local. Os testes já cobrem o cenário completo com
dados fictícios em bancos temporários. Não cadastre dados fictícios no banco real para testar.

Parâmetros são salvos pela tela e compartilhados entre usuários. Os exemplos iniciais estão
em `radar/margem/padroes.toml` e só são usados quando ainda não existe configuração salva.
Dinheiro aceita vírgula decimal (ex.: `1.234,56`), com no máximo duas casas; percentuais
são informados como `20` para 20%. Contas usam Decimal sem arredondamentos intermediários.
Contribuição é exibida com duas casas, e margem com uma; o checklist compara a margem
antes do arredondamento. O preço mínimo é arredondado para cima até o próximo centavo.

A cotação mais recente por data de cada SKU (variação) no fornecedor é usada nas estimativas.
Se houver duas na mesma data, prevalece a última registrada. Re-cotações preservam o histórico
no banco e não contam como SKUs adicionais. O mesmo produto pode ter vários fornecedores.
A data da última cotação do fornecedor acompanha a mais recente das cotações registradas.
O aviso de cotação antiga ocorre quando a idade ultrapassa o limite configurado (inicial: 15 dias).
O sistema não verifica CNPJ ou qualidade por conta própria: as confirmações são de vocês.

O esquema é atualizado automaticamente para a versão 3 na próxima abertura, preservando
usuários e dados do Bloco 1. Feche o Radar e faça o backup descrito acima antes de atualizar
um banco que já tenha informações importantes.

## Bloco 3: mercado, compras, kits e painel

Todas as telas exigem login. Nenhuma delas faz pedidos, pagamentos ou coleta automática.

### Anúncios e CSV

Na **Pesquisa de oportunidades**, cadastre um anúncio e seus preços datados manualmente.
Em **Importar CSV**, selecione um arquivo UTF-8 (aceita BOM), separado por ponto e vírgula.
Cabeçalho obrigatório: `marketplace;titulo;url;preco;data`. Opcionais: `produto;sinal`.
Preço: `59,90`; data: `2026-10-26`; URL: http/https. A coluna produto recebe o nome exato de
um produto cadastrado, sem diferenciar maiúsculas. Nomes repetidos precisam ser corrigidos
antes da importação. Produto em branco deixa o anúncio sem vínculo para associar na Pesquisa.

O único CSV versionado é `exemplos/anuncios_ficticios.csv`, com dados inteiramente fictícios.
Teste esse arquivo somente em banco de teste; não misture esses exemplos aos seus dados reais.
Cada linha válida é aceita; erros aparecem com número da linha. Aspas ou separadores quebrados
que impeçam ler o restante do arquivo são relatados; corrija a estrutura antes de reimportar.
Repetir marketplace, URL, data e preço não duplica a observação. Preços diferentes ou em datas
diferentes ficam no histórico. Marketplace é normalizado sem diferenciar maiúsculas.

Na Pesquisa, escolha produto, marketplace e uma cotação com data e fornecedor. O custo vem
dessa cotação. Cada anúncio entra uma vez nos indicadores com seu preço mais recente; a aba
Preços mostra também o histórico. Trocar a cotação muda margens e preço mínimo. Sinais como
“em alta” são informativos e nunca entram nos cálculos. Preço anunciado não comprova demanda.

### Decisão de compra

Configure orçamento (inicial R$ 1.000) e reserva (inicial zero; ajuste antes de planejar).
Cada produto tem uma cotação escolhida, quantidade, preço conservador e justificativas
separadas para demanda e concorrência. “Produto validado” é confirmação manual com justificativa,
independente desses critérios. O total comprometido inclui todos os itens, inclusive os pendentes.

Os seis critérios seguem o AGENTS.md e as decisões do Legacia: fornecedor ativo com CNPJ,
condições e nota confirmados; produto conferido; margem positiva no alvo configurado com piso
de 20%; demanda e concorrência confirmadas com justificativas; estoque com quantidade mínima
da cotação atendida, produto não validado em até 20% do orçamento e total dentro do orçamento
após a reserva. Acima do limite aparece aviso e o critério Estoque falha; nenhuma compra é feita.
Fornecedor não precisa estar na etapa Oficial para cumprir os dados exigidos por esse critério.
O preço e a cotação escolhidos ficam registrados no plano; novas cotações não trocam o custo
silenciosamente. Altere a escolha quando quiser atualizar o cenário.

### Kits e estoque por componente

Cadastre o kit, seus produtos, quantidades e a cotação de custo de cada componente.
Informe o estoque físico por produto e quantos kits deseja planejar (zero tira um kit do plano).
A tela calcula custo e faltas por componente, somando também os componentes compartilhados
entre todos os kits planejados. Com um preço conservador de venda no plano do kit, a tela mostra
a contribuição e a margem por kit; o preço mínimo para a margem-alvo aparece mesmo sem preço. Composição sem cotação não recebe custo inventado.
As quantidades são planejamento: não reservam nem baixam estoque e não entram automaticamente
no orçamento. Registre as compras de componentes na Decisão de compra.

### Painel e plano de 30 dias

O Painel conta fornecedores ativos, produtos cadastrados, produtos prontos no plano e valor
comprometido. Cadastre e edite tarefas por semana (1 a 4), responsável e conclusão.
O funil mostra fornecedores por etapa. Pendências usam as cotações atuais e a data do dia:
cotação acima do limite, margem abaixo do alvo, amostra não avaliada na etapa Em avaliação,
e contato explicitamente marcado Aguardando resposta há mais de 5 dias na etapa Em contato.
Resposta recebida encerra a espera; contatos neutros não alteram essa situação. Contatos antigos
sem classificação não são presumidos sem resposta. Legacia é sugerido para contato, cotação
e margem; Anna para amostra. As sugestões não enviam mensagens a ninguém.

O esquema 3 preserva os dados das versões anteriores. Os testes usam bancos temporários,
inclusive para importar o CSV fictício duas vezes e exercitar critérios de compra e kits.

## API

```powershell
.\.venv\Scripts\python.exe -m radar.servidor --endereco 127.0.0.1
```

- Rotas em `/api`. Só `POST /api/entrar` funciona sem sessão; todas as outras respondem 401 sem login.
- Sem lista pública de rotas (`/docs` e `/openapi.json` desligados).
- Não há bloqueio por senhas erradas (decisão do Legacia); a proteção é a senha, guardada só como hash Argon2id.
- Dinheiro sai como texto decimal (`"55.56"`) ou centavos inteiros; percentuais como fração em texto.
- Dados em formato errado recebem 400 com mensagem em português.
- Rotas: `entrar`, `sair`, `eu`, `painel`, `tarefas`, `configuracao`, `calculadora/simular`, `fornecedores`,
  `produtos`, `pesquisa`, `importar`, `kits`, `estoque/{produto}` e `compras`.

## Interface React

Dez telas, agrupadas em Visão geral, Fornecimento, Mercado e Decisão: **Painel**, **Contas**,
**Fornecedores**, **Produtos e SKUs**, **Kits**, **Itens de apoio**, **Pesquisa de oportunidades**,
**Importar CSV**, **Calculadora e parâmetros** e **Decisão de compra**. Cada tela e filtro tem um
endereço próprio (`#/pagina?filtro=valor`).

Cada campo tem um **i** ao lado do nome: passe o mouse sobre ele para ver uma explicação rápida.
Os textos ficam em `web/src/dicas.ts`, num lugar só, para ajustar a redação sem mexer nas telas.

Para desenvolver com recarga automática: API em `--porta 8502` e `npm.cmd run dev` em `web/`
(abre em `http://localhost:5173`).
