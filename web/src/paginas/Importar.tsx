// Importar CSV: vários anúncios e preços observados de uma vez. O servidor lê, valida cada linha
// e devolve o relatório; a tela só envia o arquivo e mostra o resultado.
import { useRef, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Aviso, Indicador, Painel as Caixa } from "../componentes/basicos";
import { mensagemDeErro, useGravacao } from "../componentes/gravacao";
import { Tabela, type Coluna } from "../componentes/Tabela";
import { enderecoDe } from "../rotas";

type Erro = { linha: number; erro: string };
export type Relatorio = { importadas: number; repetidas: number; erros: Erro[] };

const COLUNAS: Coluna<Erro>[] = [
  { chave: "linha", titulo: "Linha", alinhar: "direita", mostrar: (e) => e.linha, ordenar: (e) => e.linha },
  { chave: "erro", titulo: "Erro", mostrar: (e) => e.erro },
];

export function Importar() {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [relatorio, setRelatorio] = useState<{ nome: string; dados: Relatorio } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const campo = useRef<HTMLInputElement>(null);
  const gravacao = useGravacao();

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!arquivo) return;
    setErro(null);
    try {
      await gravacao.executar(async () => {
        const dados = await pedir<Relatorio>("/importar", { arquivo });
        setRelatorio({ nome: arquivo.name, dados });
        // Limpa a escolha: reenviar o mesmo arquivo exige escolhê-lo de novo, sem clique acidental.
        setArquivo(null);
        if (campo.current) campo.current.value = "";
      });
    } catch (e) {
      setRelatorio(null);
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <>
      <Caixa titulo="Arquivo">
        <p>Selecione um CSV UTF-8 separado por ponto e vírgula, com estas colunas:</p>
        <pre className="codigo">marketplace;titulo;url;preco;data;produto;sinal</pre>
        <p className="legenda">
          Produto e sinal são opcionais. Use o nome do produto cadastrado ou deixe em branco para vincular depois
          na Pesquisa. Preço: 59,90; data: 2026-10-26. Limite de 5 MB por arquivo.
        </p>
        <form className="formulario" onSubmit={enviar}>
          {erro && <Aviso tipo="erro">{erro}</Aviso>}
          <label>Arquivo CSV
            <input ref={campo} type="file" accept=".csv,text/csv" onChange={(e) => setArquivo(e.target.files?.[0] ?? null)} />
          </label>
          <div>
            <button type="submit" className="botao botao-principal" disabled={!arquivo || gravacao.ocupado}>
              {gravacao.ocupado ? "Importando…" : "Importar arquivo"}
            </button>
          </div>
        </form>
        <p className="legenda">Reimportar a mesma observação não a duplica. Confira o relatório e corrija as linhas rejeitadas.</p>
      </Caixa>

      {relatorio && (
        <Caixa titulo={`Última importação: ${relatorio.nome}`}>
          <div className="grade-3">
            <Indicador rotulo="Preços adicionados" valor={relatorio.dados.importadas} tom="verde" />
            <Indicador rotulo="Já existentes" valor={relatorio.dados.repetidas} />
            <Indicador rotulo="Linhas com erro" valor={relatorio.dados.erros.length}
              tom={relatorio.dados.erros.length ? "vermelho" : undefined} />
          </div>
          {relatorio.dados.erros.length > 0 && (
            <div className="resultado">
              <Tabela titulo="Linhas rejeitadas" colunas={COLUNAS} linhas={relatorio.dados.erros} chaveLinha={(e) => e.linha} />
            </div>
          )}
          <p><a href={enderecoDe("pesquisa")}>Vincular e analisar na Pesquisa de oportunidades</a></p>
        </Caixa>
      )}
    </>
  );
}
