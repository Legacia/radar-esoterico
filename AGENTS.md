# Radar Esotérico

Ferramenta local de inteligência comercial para a **Tenda da Bruxa 2.0**: venda de produtos esotéricos em marketplaces (Mercado Livre, Shopee etc.), com estoque próprio, como renda extra.

Este arquivo é a fonte única de regras do projeto. Vale para o Codex, para o Claude Code e para qualquer pessoa que mexa no código. Em caso de dúvida entre este arquivo e uma instrução solta, siga este arquivo e avise o responsável.

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
- **Acesso pela rede local** (configuração do Streamlit para aceitar outros computadores, SQLite em modo WAL, instruções de uso)
- **Login simples** com e-mail e senha, obrigatório antes de abrir qualquer tela (ver "Acesso pela rede")
- Testes automatizados

Fora (não implementar sem pedido explícito):

- Nuvem, aplicativo mobile, múltiplos usuários com perfis, integração com IA em tempo real
- Perfis e permissões diferentes por usuário, cadastro aberto de novos usuários, recuperação de senha por e-mail e login social (Google etc.). O login simples com e-mail e senha está **dentro** do escopo.
- Coleta automática agressiva de marketplaces

## Stack

- Python, aplicação única com módulos bem separados
- Interface: Streamlit
- Coleta e tratamento: `requests` + `pandas`
- Banco: SQLite (arquivo único em `data/`, com modo WAL ligado)
- Gráficos: Plotly
- Execução: local, pelo navegador. **O acesso por outros computadores da mesma rede entra na primeira versão** (decisão do Legacia): o Radar roda num computador "servidor" e os outros abrem o endereço dele no navegador (algo como `http://192.168.0.10:8501`). Continua sem nuvem. Detalhes na seção "Acesso pela rede".
- Agendamento: agendador do sistema operacional, só depois

## Estrutura de pastas

A pasta raiz do projeto, no computador do Legacia, é `E:\Projetos\RadarEsoterico` (repositório `radar-esoterico` no GitHub). A divisão interna abaixo é a proposta vigente; o arquivo principal da interface é `app/main.py`. Mudanças na estrutura devem ser registradas aqui.

```
.streamlit/     config.toml (configuração do servidor, vai para o Git); secrets.toml fica fora
app/            interface Streamlit (uma página por tela)
radar/          regras de negócio, sem código de interface
  banco/        conexão, criação de tabelas, consultas
  margem/       calculadora e parâmetros
  fornecedores/ ciclo de vida e checklist de promoção
  importacao/   leitura de CSV
  conectores/   fontes de dados (desacoplados, nada trava se faltarem)
tests/          testes automatizados
exemplos/       CSVs de exemplo, sem dados reais
data/           banco real (fora do Git)
backups/        backups (fora do Git)
```

Regra: a lógica de negócio fica em `radar/`. As páginas em `app/` só chamam essas funções. Isso permite testar a margem e o ciclo do fornecedor sem abrir a interface.

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
- Configuração do Streamlit em `.streamlit/config.toml` (versionado, sem segredos): aceitar conexões da rede (`server.address = "0.0.0.0"`) e porta fixa (padrão 8501). Documentar no README como descobrir o endereço do servidor.
- O Windows pede liberação no firewall na primeira execução. Liberar **somente para rede privada**, nunca para rede pública.
- SQLite com modo **WAL** ligado e `busy_timeout` configurado, para duas pessoas usarem ao mesmo tempo sem erro de "banco travado". Gravações devem ser curtas.
- O banco **nunca** é copiado para os outros computadores: existe um só, no servidor.
- **Login simples (decisão do Legacia):** e-mail e senha, pedidos antes de qualquer tela. O e-mail serve só como identificador de quem entra; o sistema **não envia e-mails**.
  - Contas são criadas pelo Legacia, por um comando de linha no servidor (por exemplo `python -m radar.usuarios criar`). Não existe tela de cadastro aberto.
  - A senha é guardada **somente como hash** (bcrypt ou argon2), na tabela `usuario`. Nunca em texto, nunca no código, nunca no Git.
  - Senha esquecida: o Legacia redefine pelo mesmo comando no servidor. Sem recuperação por e-mail.
  - A sessão dura no máximo **8 horas** desde a entrada, sem prorrogação por atividade (aprovado pelo Legacia em 26/10/2026). O valor fica em `radar/sessoes.py`.
  - "Simples" significa sem perfis e sem permissões diferentes: quem tem conta vê tudo. Mas o login é de verdade: sessão por usuário (`st.session_state`) e todas as páginas verificam se há sessão ativa antes de mostrar qualquer dado.
  - Limite conhecido: na rede local a conexão é HTTP, sem criptografia. Aceitável em rede doméstica protegida; reavaliar se a rede deixar de ser só de vocês.
  - Nenhum agente de IA cria contas reais nem escolhe senhas. Para testes, usar contas fictícias criadas só no banco de teste.
- O endereço do Radar não deve ser exposto à internet (nada de redirecionamento de porta no roteador). O login protege contra quem está na mesma rede, não contra a internet aberta.
- Backup do arquivo do banco continua sendo feito no servidor, fora do Git.

## Como trabalhar com Git

- `main` guarda só código revisado e funcionando. Nada de commit direto na `main`.
- Uma ramificação por tarefa: `codex/<tarefa>` para trabalho do Codex, `claude/<tarefa>` para trabalho do Claude Code.
- Tudo entra por pull request, revisado por uma pessoa.
- **Dois agentes nunca editam os mesmos arquivos ao mesmo tempo.** Divisão sugerida: o Codex constrói módulos; o Claude Code revisa (bugs, testes, qualidade dos dados, erros financeiros) e escreve testes.
- Mensagens de commit curtas, em português, dizendo o que mudou.
- As tarefas do plano de 30 dias viram Issues no GitHub, com responsável e semana.

## Comandos (a confirmar quando o projeto existir)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/main.py
pytest
```

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
