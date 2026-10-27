// Carregamento seguro de uma ficha aberta em gaveta (fornecedor, produto...). Junta as proteções
// pedidas na revisão da tela de Fornecedores, para todas as telas usarem as mesmas:
// - só a resposta da consulta mais recente entra na tela, mesmo com o mesmo identificador;
// - cada recarga gera uma versão nova, usada como chave dos formulários, que são recriados
//   com os dados que acabaram de chegar;
// - ficha aberta durante uma gravação fica travada até ela acabar e, se deu certo, até buscar
//   de novo os dados salvos (a ficha que gravou já recarrega dentro da própria gravação);
// - gravação rejeitada não recarrega nada, para manter o que foi digitado e o erro na tela.
import { useCallback, useEffect, useRef, useState } from "react";
import { pedir } from "../api";
import { mensagemDeErro, type Executar } from "./gravacao";
import { useNotificar } from "./Notificacoes";

export function useFicha<T extends { id: number }>({ caminho, id, executar, ocupado, gravacoes, aoMudar }: {
  caminho: string;
  id: number;
  executar: Executar;
  ocupado: boolean;
  gravacoes: number;
  aoMudar: () => Promise<unknown>;
}) {
  const [ficha, setFicha] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const notificar = useNotificar();

  const ultimaConsulta = useRef(0);
  const carregar = useCallback(() => {
    const consulta = ++ultimaConsulta.current;
    return pedir<T>(caminho).then(
      (f) => {
        if (consulta !== ultimaConsulta.current || f.id !== id) return;
        setFicha(f); setVersao((v) => v + 1); setErro(null);
      },
      (e) => { if (consulta === ultimaConsulta.current) setErro(mensagemDeErro(e)); });
  }, [caminho, id]);
  useEffect(() => { setFicha(null); carregar(); }, [carregar]);

  const abertaDuranteGravacao = useRef(ocupado);
  const gravacoesNaAbertura = useRef(gravacoes);
  const [atualizando, setAtualizando] = useState(ocupado);
  useEffect(() => {
    if (ocupado || !abertaDuranteGravacao.current) return;
    abertaDuranteGravacao.current = false;
    if (gravacoes === gravacoesNaAbertura.current) setAtualizando(false);
    else carregar().finally(() => setAtualizando(false));
  }, [ocupado, gravacoes, carregar]);

  /** Grava, recarrega a ficha e a lista da tela, e só então libera a trava. */
  const gravar = (acao: () => Promise<unknown>, sucesso: string) => executar(async () => {
    await acao();
    notificar(sucesso);
    await Promise.all([carregar(), aoMudar()]);
  });

  const recarregarTudo = () => Promise.all([carregar(), aoMudar()]).then(() => {});

  return { ficha, erro, versao, bloqueado: ocupado || atualizando, gravar, recarregarTudo };
}
