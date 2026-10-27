import { useCallback, useEffect, useState } from "react";
import { quandoPerderSessao, quemSou, sair, type Usuario } from "./api";
import { ProvedorNotificacoes } from "./componentes/Notificacoes";
import { Entrada } from "./paginas/Entrada";
import { Shell } from "./paginas/Shell";

type Estado =
  | { tipo: "carregando" }
  | { tipo: "fora"; aviso?: string }
  | { tipo: "dentro"; usuario: Usuario };

export function App() {
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });

  useEffect(() => {
    // Qualquer 401 depois da entrada (sessão de 8 horas vencida, servidor reiniciado) volta à entrada.
    quandoPerderSessao(() => setEstado({ tipo: "fora", aviso: "Sua sessão terminou. Entre novamente." }));
    quemSou().then((usuario) => setEstado({ tipo: "dentro", usuario }), () => setEstado({ tipo: "fora" }));
    return () => quandoPerderSessao(null);
  }, []);

  const aoSair = useCallback(async () => {
    // Mesmo se a sessão já tiver vencido ou o servidor cair, a tela volta para a entrada.
    await sair().catch(() => {});
    setEstado({ tipo: "fora" });
  }, []);

  return (
    <ProvedorNotificacoes>
      {estado.tipo === "carregando" && <p className="carregando">Carregando…</p>}
      {estado.tipo === "fora" && (
        <Entrada aviso={estado.aviso} aoEntrar={(usuario) => setEstado({ tipo: "dentro", usuario })} />
      )}
      {estado.tipo === "dentro" && <Shell usuario={estado.usuario} aoSair={aoSair} />}
    </ProvedorNotificacoes>
  );
}
