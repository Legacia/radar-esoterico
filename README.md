# Radar Esotérico — MVP 0.1, Blocos 1 e 2

Ferramenta local de inteligência comercial da Tenda da Bruxa 2.0.
Inclui base, banco, login, fornecedores, produtos, SKUs e calculadora. Indicadores entram no Bloco 3.

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
   sem mudar a etapa. A promoção exige todas as verificações e três códigos de SKU distintos
   com margem no alvo configurado, respeitando o piso de 20% aprovado pelo Legacia.
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

O esquema é atualizado automaticamente para a versão 2 na próxima abertura, preservando
usuários e dados do Bloco 1. Feche o Radar e faça o backup descrito acima antes de atualizar
um banco que já tenha informações importantes.
