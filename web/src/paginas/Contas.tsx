// Contas: quem já entrou cadastra outra pessoa ou troca uma senha. Não há cadastro aberto:
// a API só aceita estes pedidos com sessão. O hash da senha nunca chega à tela.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Aviso, Painel as Caixa } from "../componentes/basicos";
import { Gaveta } from "../componentes/Gaveta";
import { mensagemDeErro, useGravacao } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { Tabela } from "../componentes/Tabela";

export type Conta = { id: number; nome: string; email: string };

export function Contas() {
  const [contas, setContas] = useState<Conta[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [trocando, setTrocando] = useState<Conta | null>(null);
  const gravacao = useGravacao();
  const notificar = useNotificar();

  const carregar = useCallback(() => pedir<{ contas: Conta[] }>("/contas").then(
    (r) => { setContas(r.contas); setErro(null); },
    (e) => setErro(mensagemDeErro(e)),
  ), []);
  useEffect(() => { carregar(); }, [carregar]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!contas) return <p className="legenda">Carregando contas…</p>;

  return (
    <div className="grade-2">
      <Caixa titulo="Contas com acesso">
        <p className="legenda">Quem tem conta vê todas as telas. Para tirar o acesso de alguém, troque a senha da conta.</p>
        <Tabela titulo="Contas com acesso" linhas={contas} chaveLinha={(c) => c.id} colunas={[
          { chave: "nome", titulo: "Nome", mostrar: (c) => c.nome, ordenar: (c) => c.nome },
          { chave: "email", titulo: "E-mail", mostrar: (c) => c.email, ordenar: (c) => c.email },
          { chave: "senha", titulo: "Senha", mostrar: (c) => (
            <button type="button" className="botao" onClick={() => setTrocando(c)}>Trocar senha</button>
          ) },
        ]} />
      </Caixa>
      <NovaConta ocupado={gravacao.ocupado} aoEnviar={(dados) => gravacao.executar(async () => {
        await pedir("/contas", { corpo: dados });
        notificar(`Conta de ${dados.nome.trim()} criada. Passe a senha para a pessoa pessoalmente.`);
        await carregar();
        return true;
      })} />
      <Gaveta aberta={trocando !== null} titulo={`Trocar senha de ${trocando?.nome ?? ""}`} aoFechar={() => setTrocando(null)}>
        {trocando && (
          <TrocarSenha key={trocando.id} ocupado={gravacao.ocupado} aoEnviar={(senha) => gravacao.executar(async () => {
            await pedir(`/contas/${trocando.id}/senha`, { metodo: "PUT", corpo: { senha } });
            notificar(`Senha de ${trocando.nome} trocada. As sessões abertas com a senha antiga foram encerradas.`);
            setTrocando(null);
          })} />
        )}
      </Gaveta>
    </div>
  );
}

function CamposSenha({ senha, repetir, aoMudar }: { senha: string; repetir: string; aoMudar: (s: string, r: string) => void }) {
  return (
    <div className="campos-2">
      <label>Senha (mínimo 8 caracteres)
        <input required type="password" autoComplete="new-password" minLength={8} value={senha} onChange={(e) => aoMudar(e.target.value, repetir)} />
      </label>
      <label>Repita a senha
        <input required type="password" autoComplete="new-password" value={repetir} onChange={(e) => aoMudar(senha, e.target.value)} />
      </label>
    </div>
  );
}

function NovaConta({ ocupado, aoEnviar }: {
  ocupado: boolean;
  aoEnviar: (dados: { nome: string; email: string; senha: string }) => Promise<unknown>;
}) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [repetir, setRepetir] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    if (senha !== repetir) return setErro("As senhas não coincidem.");
    try {
      // Só limpa o formulário se a conta foi criada (um clique repetido durante a gravação devolve undefined).
      if (await aoEnviar({ nome, email, senha })) { setNome(""); setEmail(""); setSenha(""); setRepetir(""); }
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <Caixa titulo="Nova conta">
      <form className="formulario" onSubmit={enviar}>
        {erro && <Aviso tipo="erro">{erro}</Aviso>}
        <div className="campos-2">
          <label>Nome<input required value={nome} onChange={(e) => setNome(e.target.value)} /></label>
          <label>E-mail<input required type="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        </div>
        <CamposSenha senha={senha} repetir={repetir} aoMudar={(s, r) => { setSenha(s); setRepetir(r); }} />
        <p className="legenda">O e-mail serve só para entrar; o Radar não envia mensagens.</p>
        <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Criar conta"}</button></div>
      </form>
    </Caixa>
  );
}

function TrocarSenha({ ocupado, aoEnviar }: { ocupado: boolean; aoEnviar: (senha: string) => Promise<unknown> }) {
  const [senha, setSenha] = useState("");
  const [repetir, setRepetir] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    if (senha !== repetir) return setErro("As senhas não coincidem.");
    try {
      await aoEnviar(senha);
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <CamposSenha senha={senha} repetir={repetir} aoMudar={(s, r) => { setSenha(s); setRepetir(r); }} />
      <div><button type="submit" className="botao botao-principal" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar senha"}</button></div>
    </form>
  );
}
