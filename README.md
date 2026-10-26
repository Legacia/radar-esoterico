# Radar Esotérico — MVP 0.1, Bloco 1

Ferramenta local de inteligência comercial da Tenda da Bruxa 2.0.
Este bloco entrega a base, banco e login. Ainda não há cadastros comerciais ou indicadores.

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
