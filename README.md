# Radar Esotérico — MVP 0.1, Blocos 1, 2 e 3

Ferramenta local de inteligência comercial da Tenda da Bruxa 2.0.
Inteligência comercial local: login, fornecedores, produtos, cotações, mercado, margem, planejamento de compras, kits e painel.

## Instalar no servidor (Windows, Python 3.13)

Abra o PowerShell e execute uma linha de cada vez:

```powershell
cd E:\Projetos\RadarEsoterico
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Os comandos usam o Python do ambiente diretamente, sem precisar ativar scripts no PowerShell.

## Criar conta e abrir

```powershell
cd E:\Projetos\RadarEsoterico
.\.venv\Scripts\python.exe -m radar.usuarios criar
.\.venv\Scripts\python.exe -m streamlit run app/main.py
```

Informe nome, e-mail e uma senha de pelo menos 8 caracteres. A senha é solicitada duas vezes,
sem aparecer na tela. Não passe senhas como argumentos. As contas reais são criadas pelo
responsável no servidor; não há cadastro aberto nem envio de e-mails.

Abra http://localhost:8501 no navegador, entre com a conta criada e veja o Painel.
O botão **Sair** encerra a sessão. O login dura no máximo **8 horas desde a entrada**;
o prazo é conferido em cada interação e a sessão fica apenas na memória do Streamlit.
Reiniciar o servidor exige novo login. Cada sessão de navegador entra separadamente.

Para redefinir uma senha, no servidor:

```powershell
.\.venv\Scripts\python.exe -m radar.usuarios redefinir
```

A senha anterior deixa de funcionar para novos logins. Sessões já abertas continuam até sair
ou completar as 8 horas. Para encerrá-las imediatamente, reinicie o servidor.

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
```

Os testes usam bancos temporários e contas fictícias; não alteram `data/radar.db`.
Também exercitam a interface Streamlit: bloqueio, entrada, saída e expiração.

## Dados e manutenção

`data/radar.db` é criado automaticamente na primeira execução ou criação de conta.
SQLite usa WAL, espera de até 5 segundos em disputas de escrita e chaves estrangeiras.
Dinheiro no banco é armazenado em centavos inteiros; percentuais em texto decimal.
`PRAGMA user_version` controla o esquema; alterações futuras devem acrescentar migrações,
sem editar as já publicadas. Migrações e gravações falhas são revertidas.

Banco, backups, planilhas e segredos ficam fora do Git. `.env.example` está vazio;
este bloco não precisa de variáveis de ambiente. Não há integração real de marketplace.
Para backup manual, pare o Radar e copie a pasta `data` inteira para um local protegido
fora do Git; em WAL, não copie apenas o `.db` enquanto o servidor estiver aberto.

Código de negócio: `radar/`. Interface: `app/`. Novas telas devem chamar
`exigir_login()` antes de mostrar dados, além da barreira na entrada principal.

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
   Vários códigos do mesmo produto contam como um só, pela melhor margem entre as
   cotações atuais desses códigos.
   Descartar ou pausar exige motivo. Nenhuma dessas decisões é automática.

Use dados comerciais somente no banco local. Os testes já cobrem o cenário completo com
dados fictícios em bancos temporários. Não cadastre dados fictícios no banco real para testar.

Parâmetros são salvos pela tela e compartilhados entre usuários. Os exemplos iniciais estão
em `radar/margem/padroes.toml` e só são usados quando ainda não existe configuração salva.
Dinheiro aceita vírgula decimal (ex.: `1.234,56`), com no máximo duas casas; percentuais
são informados como `20` para 20%. Contas usam Decimal sem arredondamentos intermediários.
Contribuição é exibida com duas casas, e margem com uma; o checklist compara a margem
antes do arredondamento. O preço mínimo é arredondado para cima até o próximo centavo.

A cotação mais recente por data de cada código do fornecedor é usada nas estimativas.
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
entre todos os kits planejados. Composição sem cotação não recebe custo inventado.
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

## API (migração para React, etapa 1)

A interface React ainda está em construção; enquanto isso o Streamlit continua sendo a forma de uso.
A API já pode ser iniciada para testes:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m radar.servidor --endereco 127.0.0.1
```

- Rotas em `/api`. Só `POST /api/entrar` funciona sem sessão; todas as outras respondem 401 sem login.
- Sessão em cookie `HttpOnly` e `SameSite=Strict`, guardada no servidor, com até 8 horas desde a entrada. Sair e reiniciar o servidor encerram a sessão.
- Não há bloqueio por senhas erradas (decisão do Legacia); a proteção é a senha, guardada só como hash Argon2id.
- Dinheiro sai como texto decimal (`"55.56"`) ou centavos inteiros; percentuais como fração em texto.
- Rotas: `entrar`, `sair`, `eu`, `painel`, `configuracao`, `calculadora/simular`, `tarefas` (criar) e `tarefas/{id}` (alterar), `fornecedores` (lista, cadastro, ficha, alteração, etapa, promoção e contatos), `produtos` (catálogo, cadastro, ficha, alteração e cotações), `configuracao` (PUT, salvar parâmetros) e `pesquisa` (anúncios, vínculo, cotações do produto e resultado). As demais entram junto com cada tela React.
- Dados em formato errado recebem 400 com mensagem em português.

## Interface React (migração, etapa 2)

Estrutura pronta: entrada com e-mail e senha, barra lateral com as oito telas, tema e componentes comuns.
As telas chegam uma por vez na etapa 3. Já migradas: **Painel** (indicadores, pendências, funil e plano de 30 dias, com cadastro e conclusão de tarefas), **Fornecedores** (lista por etapa, ficha com checklist de promoção, condições, cotações e contatos), **Produtos e SKUs** (catálogo, cotações com margem e registro de nova cotação), **Calculadora e parâmetros** (simulação de venda e edição dos parâmetros) e **Pesquisa de oportunidades** (anúncios, preços observados, vínculo com produto e margem por anúncio). As demais ainda são usadas pelo Streamlit.

Para montar e ver no servidor (precisa do Node.js LTS só neste computador):

```powershell
cd web
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe -m radar.servidor --endereco 127.0.0.1
```

Depois abra `http://127.0.0.1:8501`. Testes da interface: `npm test` dentro de `web/`.
Para desenvolver com recarga automática: API em `--porta 8502` e `npm run dev` em `web/` (abre em `http://localhost:5173`).
