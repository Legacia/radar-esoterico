import { useState, type FormEvent } from "react";
import { entrar, ErroApi, type Usuario } from "../api";
import { Aviso } from "../componentes/basicos";
import { Dica } from "../componentes/Dica";

export function Entrada({ aoEntrar, aviso }: { aoEntrar: (usuario: Usuario) => void; aviso?: string }) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      aoEntrar(await entrar(email, senha));
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Algo deu errado. Tente de novo.");
      setSenha("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="entrada">
      <div className="entrada-caixa">
        <div className="marca marca-clara">
          <span className="marca-nome">Radar Esotérico</span>
          <span className="marca-sub">Tenda da Bruxa 2.0</span>
        </div>
        <p className="legenda">Inteligência comercial · acesso restrito à rede da casa</p>
        {aviso && <Aviso>{aviso}</Aviso>}
        {erro && <Aviso tipo="erro">{erro}</Aviso>}
        <form onSubmit={enviar} className="formulario">
          <label><span className="rotulo">E-mail<Dica de="E-mail" /></span>
            <input type="email" autoComplete="username" required value={email}
              onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label><span className="rotulo">Senha<Dica de="Senha" /></span>
            <input type="password" autoComplete="current-password" required value={senha}
              onChange={(e) => setSenha(e.target.value)} />
          </label>
          <button type="submit" className="botao botao-principal" disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>
        <p className="legenda">Esqueceu a senha? Peça a quem já tem conta para trocar na tela Contas.</p>
      </div>
    </main>
  );
}
