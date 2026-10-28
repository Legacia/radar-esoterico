// Calculadora e parâmetros: simula uma venda e edita os parâmetros compartilhados.
// A conta é feita pela API (POST /api/calculadora/simular); a tela só formata o resultado.
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { pedir } from "../api";
import { Aviso, Indicador, Painel as Caixa } from "../componentes/basicos";
import { mensagemDeErro, useGravacao } from "../componentes/gravacao";
import { useNotificar } from "../componentes/Notificacoes";
import { percentual, reais } from "../formato";
import { Dica } from "../componentes/Dica";
import type { ChaveDica } from "../dicas";

type Campos = { comissao: string; tributo: string; margem_alvo: string; tarifa_fixa: string; embalagem: string; outros: string };
export type Configuracao = { parametros: Record<string, string>; campos: Campos; limite_cotacao_dias: number };
type Resultado = { contribuicao: string; margem_pct: string; preco_minimo: string | null; aviso_preco_minimo: string | null };

export function Calculadora() {
  const [config, setConfig] = useState<Configuracao | null>(null);
  const [versao, setVersao] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  // Última venda simulada: refeita sozinha quando os parâmetros mudam, para não mostrar conta velha.
  const [venda, setVenda] = useState<{ preco: string; custo: string } | null>(null);
  const gravacao = useGravacao();
  const notificar = useNotificar();

  const carregar = useCallback(() => pedir<Configuracao>("/configuracao").then(
    (c) => { setConfig(c); setVersao((v) => v + 1); setErro(null); },
    (e) => setErro(mensagemDeErro(e)),
  ), []);
  useEffect(() => { carregar(); }, [carregar]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!config) return <p className="legenda">Carregando parâmetros…</p>;

  return (
    <div className="grade-2 grade-igual">
      <Simulacao venda={venda} versao={versao} aoSimular={setVenda} />
      <Parametros key={versao} config={config} ocupado={gravacao.ocupado}
        aoEnviar={(dados) => gravacao.executar(async () => {
          await pedir("/configuracao", { metodo: "PUT", corpo: dados });
          notificar("Parâmetros salvos. As estimativas usarão os novos valores.");
          await carregar();
        })} />
    </div>
  );
}

function Simulacao({ venda, versao, aoSimular }: {
  venda: { preco: string; custo: string } | null;
  versao: number;
  aoSimular: (venda: { preco: string; custo: string }) => void;
}) {
  const [preco, setPreco] = useState(venda?.preco ?? "");
  const [custo, setCusto] = useState(venda?.custo ?? "");
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  // Só a resposta da simulação mais recente aparece, mesmo que as respostas cheguem fora de ordem.
  const ultima = useRef(0);

  const simular = useCallback((dados: { preco: string; custo: string }) => {
    const pedido = ++ultima.current;
    setErro(null);
    pedir<Resultado>("/calculadora/simular", { corpo: dados }).then(
      (r) => { if (pedido === ultima.current) setResultado(r); },
      (e) => { if (pedido === ultima.current) { setResultado(null); setErro(mensagemDeErro(e)); } });
  }, []);

  // Parâmetros salvos (nova versão): refaz a última simulação com os valores novos.
  useEffect(() => {
    if (venda && versao > 1) simular(venda);
  }, [versao]); // depende só da versão: refaz uma vez por parâmetro salvo

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    const dados = { preco, custo };
    aoSimular(dados);
    simular(dados);
  }

  return (
    <Caixa titulo="Simular uma venda">
      <form className="formulario" onSubmit={enviar}>
        <div className="campos-2">
          <label><span className="rotulo">Preço de venda (R$)<Dica de="Preço de venda (R$)" /></span><input required inputMode="decimal" value={preco} onChange={(e) => setPreco(e.target.value)} /></label>
          <label><span className="rotulo">Custo do produto (R$)<Dica de="Custo do produto (R$)" /></span><input required inputMode="decimal" value={custo} onChange={(e) => setCusto(e.target.value)} /></label>
        </div>
        <div><button type="submit" className="botao botao-principal">Calcular margem</button></div>
      </form>
      <div className="pilha resultado" aria-live="polite">
        {erro && <Aviso tipo="erro">{erro}</Aviso>}
        {resultado && (
          <>
            <div className="grade-3">
              <Indicador rotulo="Contribuição por venda" valor={reais(resultado.contribuicao)}
                tom={resultado.contribuicao.startsWith("-") ? "vermelho" : undefined} />
              <Indicador rotulo="Margem de contribuição" valor={percentual(resultado.margem_pct)} />
              <Indicador rotulo="Preço mínimo para o alvo" valor={resultado.preco_minimo ? reais(resultado.preco_minimo) : "Inviável"} />
            </div>
            {resultado.aviso_preco_minimo && <Aviso tipo="atencao">{resultado.aviso_preco_minimo}</Aviso>}
          </>
        )}
        <Aviso>Frete e despesas fixas não entram nesta conta. Contribuição não é lucro líquido.</Aviso>
      </div>
    </Caixa>
  );
}

const CAMPOS: [keyof Campos, string][] = [
  ["comissao", "Comissão (%)"], ["tributo", "Tributo (%)"], ["margem_alvo", "Margem-alvo (%)"],
  ["tarifa_fixa", "Tarifa fixa (R$)"], ["embalagem", "Embalagem (R$)"], ["outros", "Outros por venda (R$)"],
];

function Parametros({ config, ocupado, aoEnviar }: {
  config: Configuracao;
  ocupado: boolean;
  aoEnviar: (dados: Campos & { limite_cotacao_dias: number }) => Promise<unknown>;
}) {
  const [campos, setCampos] = useState<Campos>(config.campos);
  const [dias, setDias] = useState(String(config.limite_cotacao_dias));
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    // Dias são um inteiro de calendário, não dinheiro; o servidor confere o limite de novo.
    if (!/^\d{1,4}$/.test(dias.trim())) {
      setErro("O limite de cotação deve estar entre 1 e 3650 dias.");
      return;
    }
    try {
      await aoEnviar({ ...campos, limite_cotacao_dias: Number.parseInt(dias, 10) });
    } catch (e) {
      setErro(mensagemDeErro(e));
    }
  }

  return (
    <Caixa titulo="Parâmetros">
      <p className="legenda">Compartilhados com as estimativas, a pesquisa e o checklist dos fornecedores.</p>
      <form className="formulario" onSubmit={enviar}>
        {erro && <Aviso tipo="erro">{erro}</Aviso>}
        <div className="campos-3">
          {CAMPOS.map(([chave, rotulo]) => (
            <label key={chave}><span className="rotulo">{rotulo}<Dica de={rotulo as ChaveDica} /></span>
              <input required inputMode="decimal" value={campos[chave]} onChange={(e) => setCampos({ ...campos, [chave]: e.target.value })} />
            </label>
          ))}
        </div>
        <label><span className="rotulo">Cotação antiga após quantos dias?<Dica de="Cotação antiga após quantos dias?" /></span>
          <input required inputMode="numeric" value={dias} onChange={(e) => setDias(e.target.value)} />
        </label>
        <div><button type="submit" className="botao" disabled={ocupado}>{ocupado ? "Salvando…" : "Salvar parâmetros"}</button></div>
      </form>
      <p className="legenda">
        Os valores iniciais são ilustrativos. Comissão deve ser confirmada na conta do marketplace; tributo não
        representa enquadramento fiscal. A margem-alvo pode ser simulada livremente, mas promoção de fornecedor e
        decisão de compra exigem pelo menos 20%.
      </p>
    </Caixa>
  );
}
