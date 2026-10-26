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
- Testes automatizados

Fora (não implementar sem pedido explícito):

- Nuvem, aplicativo mobile, múltiplos usuários com perfis, integração com IA em tempo real
- Login. Se o acesso pela rede interna for ativado e houver risco, uma senha simples pode ser discutida depois.
- Coleta automática agressiva de marketplaces

## Stack

- Python, aplicação única com módulos bem separados
- Interface: Streamlit
- Coleta e tratamento: `requests` + `pandas`
- Banco: SQLite (arquivo único em `data/`, com modo WAL ligado)
- Gráficos: Plotly
- Execução: local, pelo navegador. Acesso por outros computadores da mesma rede é desejado, mas fica para depois da primeira versão.
- Agendamento: agendador do sistema operacional, só depois

## Estrutura de pastas (proposta)

```
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

Tabelas: `fornecedor`, `interacao`, `sku_fornecedor`, `produto`, `anuncio`, `preco_observado`, `kit`, `kit_item`, `cenario_margem`.

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

- Nomes finais das pastas e do arquivo principal
- Se o acesso pela rede local entra na primeira versão
- Lista dos 20 produtos candidatos e dos links de anúncios
- Resposta dos fornecedores. Os cinco listados no planejamento (Brasil Esotérico Atacado, Baú da Bruxa, Mandala Esotérica Atacado, Encantos do Mundo, Flute Incensos) são pontos de partida para cotação, **não** parceiros aprovados, e os dados deles não foram verificados.
