// Explicação rápida de cada campo, mostrada no balão do "i" ao lado do nome do campo.
// A chave é o nome do campo como aparece na tela. Textos curtos, em linguagem simples.
export const DICAS = {
  // Entrada e Contas
  "E-mail": "Endereço usado só para identificar quem entra. O Radar não envia e-mails.",
  "Senha": "Senha da sua conta. Se esquecer, outra pessoa com conta troca pela tela Contas.",
  "Nome": "Nome da pessoa, como vai aparecer na barra lateral.",
  "Senha (mínimo 8 caracteres)": "Senha nova da conta. Passe para a pessoa pessoalmente, nunca por mensagem.",
  "Repita a senha": "Digite a mesma senha de novo, para evitar erro de digitação.",

  // Painel
  "Título da tarefa": "O que precisa ser feito, em poucas palavras.",
  "Semana": "Semana do plano de 30 dias em que a tarefa deve ser feita (1 a 4).",
  "Responsável": "Quem vai cuidar da tarefa (por exemplo, Legacia ou Anna).",
  "Tarefa concluída": "Marque quando a tarefa estiver feita. Ela conta no progresso do plano.",

  // Fornecedores
  "Nome do fornecedor": "Nome da empresa ou loja que vende no atacado.",
  "CNPJ": "Número de cadastro da empresa. Confira na Receita Federal antes de marcar como verificado.",
  "Contato": "Telefone, WhatsApp, e-mail ou site para falar com o fornecedor.",
  "Pedido mínimo (R$)": "Menor valor de compra que o fornecedor aceita por pedido.",
  "Prazo": "Quanto tempo o fornecedor leva para entregar depois do pedido.",
  "Condição de pagamento": "Como o fornecedor aceita receber: à vista, Pix, boleto, parcelado etc.",
  "Verificações manuais": "Confirmações que vocês fazem depois de checar as informações. Contam no checklist de promoção.",
  "CNPJ verificado": "Vocês conferiram que o CNPJ existe e está ativo.",
  "Condições comerciais verificadas": "Pedido mínimo, prazo e pagamento foram confirmados com o fornecedor.",
  "Emite nota fiscal": "O fornecedor emite nota fiscal na venda.",
  "Amostra avaliada pela Anna (especificações, procedência e qualidade)": "A Anna recebeu uma amostra e aprovou o produto.",
  "Reposição confirmada": "O fornecedor garantiu que consegue repor o estoque quando precisar.",
  "Etapa de acompanhamento": "Em que ponto está a conversa com o fornecedor. Para virar oficial, use o botão de promoção.",
  "Motivo para descartar ou pausar": "Por que o fornecedor saiu da lista. Obrigatório ao descartar ou pausar.",
  "Data do contato": "Dia em que vocês falaram com o fornecedor.",
  "Canal": "Por onde foi o contato: WhatsApp, e-mail, telefone, site etc.",
  "Situação da resposta": "Se vocês estão esperando resposta. Sem resposta há mais de 5 dias vira pendência no Painel.",
  "Resumo do contato": "O que foi conversado, em poucas linhas.",

  // Produtos e SKUs
  "Nome do produto": "Nome do produto candidato, como vocês o chamam.",
  "Família": "Grupo do produto, por exemplo incensos, cristais ou amuletos.",
  "Status do produto": "Situação do produto para vocês, por exemplo Candidato ou Em teste.",
  "Avaliação do produto": "Conferências feitas no produto. As três contam no critério Produto da compra.",
  "Especificações conferidas": "Tamanho, material e descrição batem com o que o fornecedor informou.",
  "Procedência conferida": "Vocês sabem de onde o produto vem e se ele é legítimo.",
  "Qualidade conferida pela Anna": "A Anna avaliou a qualidade do produto.",
  "Fornecedor da cotação": "Quem passou o preço desta cotação.",
  "Variação (SKU)": "Qual variação do produto foi cotada. Cada variação é um SKU de vocês, com código RAD.",
  "Código do parceiro (opcional)": "Código do item no catálogo do fornecedor, se houver. Ajuda a pedir o item certo.",
  "Preço cotado (R$)": "Preço que o fornecedor passou, na unidade dele (unidade, caixa, pacote…), sem frete.",
  "Unidades de venda na unidade cotada": "Quantas unidades de venda vêm no que foi cotado. Ex.: pacote com 20 caixas = 20. O custo é dividido por esse número.",
  "Quantidade mínima (em unidades cotadas)": "Menor quantidade que o fornecedor vende, na unidade dele (ex.: 2 pacotes).",
  "Preço conservador por unidade de venda (R$), opcional": "Preço pelo qual vocês acham que vendem uma unidade de venda sem desconto. Usado para estimar a margem.",
  "Cor": "Cor desta variação, se fizer diferença (opcional).",
  "Tamanho": "Tamanho desta variação, se fizer diferença (opcional).",
  "Unidade de venda mínima": "Como o item é vendido ao cliente: unidade (caldeirão), caixa (incenso) etc. Custo e margem usam essa unidade.",
  "Custo unitário (R$)": "Quanto vocês pagam por uma unidade, sem frete.",
  "Data da cotação": "Dia em que este preço foi informado. Preço antigo gera aviso.",

  // Itens de apoio e embalagem
  "Nome do item": "Nome do material de envio, por exemplo caixa P ou sacola kraft.",
  "Fornecedor (opcional)": "Quem vende este item, se ele estiver cadastrado em Fornecedores.",
  "Item de apoio": "Material de envio que vai junto em cada venda.",
  "Quantidade por unidade vendida": "Quantos deste item vão em cada venda. A soma substitui a embalagem padrão.",

  // Kits
  "Kit": "Kit que você quer ver ou editar.",
  "Nome do novo kit": "Nome do kit, por exemplo Kit 3 incensos + suporte.",
  "Nome do kit": "Nome do kit, como vocês o chamam.",
  "Kits planejados": "Quantos kits vocês pensam em montar. Zero tira o kit da necessidade conjunta.",
  "Preço conservador de venda do kit (R$), opcional": "Preço pelo qual vocês acham que vendem o kit sem desconto. Usado para calcular a margem do kit.",
  "Componente": "Produto que faz parte do kit.",
  "Cotação de custo do componente": "Qual cotação usar como custo deste componente.",
  "Unidades desse componente por kit": "Quantas unidades deste produto vão em cada kit.",
  "Estoque físico atual do componente": "Quantas unidades vocês têm hoje, contadas na prateleira.",

  // Pesquisa de oportunidades
  "Produto pesquisado": "Produto cujos anúncios você quer comparar.",
  "Cotação usada como custo": "Qual cotação usar como custo para calcular a margem de cada anúncio.",
  "Filtrar marketplace": "Mostra só os anúncios de uma plataforma.",
  "Buscar no título dos anúncios": "Mostra só os anúncios que têm esta palavra no título.",
  "Marketplace": "Plataforma do anúncio, por exemplo Shopee ou Mercado Livre.",
  "Título do anúncio": "Título como aparece no anúncio.",
  "URL do anúncio": "Endereço da página do anúncio, começando com http ou https.",
  "Preço observado (R$)": "Preço que o anúncio mostrava no dia. Preço anunciado não garante venda.",
  "Data da observação": "Dia em que vocês viram esse preço.",
  "Produto do anúncio": "Produto do catálogo a que este anúncio corresponde.",
  "Sinal observado, opcional": "Indício de procura visto no anúncio, por exemplo mais vendido na categoria.",
  "Anúncio para vincular": "Anúncio já registrado que você quer ligar a um produto.",
  "Vínculo do produto": "Produto do catálogo ligado ao anúncio. Sem vínculo, o anúncio não entra na pesquisa.",

  // Importar
  "Arquivo CSV": "Planilha salva em CSV com anúncios e preços observados. O formato está no texto acima.",

  // Calculadora e parâmetros
  "Preço de venda (R$)": "Preço pelo qual o produto seria vendido na plataforma.",
  "Custo do produto (R$)": "Quanto vocês pagam pelo produto ao fornecedor.",
  "Comissão (%)": "Valor cobrado pela plataforma sobre cada venda.",
  "Tributo (%)": "Imposto sobre a venda. Valor ilustrativo: cada pessoa configura o que vale para ela.",
  "Margem-alvo (%)": "Quanto do preço vocês querem que sobre em cada venda. Para comprar e promover fornecedor, o mínimo é 20%.",
  "Tarifa fixa (R$)": "Valor fixo que a plataforma cobra por venda, além da comissão.",
  "Embalagem (R$)": "Custo padrão de embalagem por venda. Vale para produtos e kits sem itens de apoio indicados.",
  "Outros por venda (R$)": "Outros gastos por venda, como publicidade e perdas.",
  "Cotação antiga após quantos dias?": "Depois de quantos dias um preço de fornecedor passa a ser considerado antigo e gera aviso.",

  // Decisão de compra
  "Orçamento do lote (R$)": "Quanto vocês podem gastar no primeiro lote de estoque.",
  "Reserva de reposição (R$)": "Parte do orçamento guardada para repor estoque. Não pode ser usada no lote.",
  "Produto do plano": "Produto que você quer incluir ou editar no plano de compra.",
  "Cotação para o plano": "Qual cotação de fornecedor usar nesta compra.",
  "Quantidade planejada": "Quantas unidades vocês pensam em comprar.",
  "Preço conservador de venda no plano (R$)": "Preço pelo qual vocês acham que vendem sem desconto. Usado no critério de margem.",
  "Confirmações manuais": "Critérios que só vocês podem confirmar. Cada confirmação exige uma justificativa.",
  "Demanda confirmada": "Há indícios verificáveis de procura, não só anúncios publicados.",
  "Justificativa de demanda": "O que mostra que há procura: buscas, mais vendidos, avaliações etc.",
  "Concorrência confirmada": "O preço é competitivo sem depender de desconto permanente.",
  "Justificativa de concorrência": "Por que o preço de vocês consegue competir com os anúncios existentes.",
  "Produto validado": "Produto já testado. Sem validação, a compra fica limitada a 20% do orçamento.",
  "Justificativa da validação": "O que comprova que o produto foi validado.",
} as const;

export type ChaveDica = keyof typeof DICAS;
