from datetime import datetime, timedelta
from decimal import Decimal
import sqlite3

import pytest

from radar.backup import fazer_backup, listar_backups, main
from radar.fornecedores import listar_fornecedores, salvar_fornecedor


def test_copia_tem_os_dados_e_passa_na_conferencia(db, conta, tmp_path):
    salvar_fornecedor("Fornecedor fictício", "", "", Decimal("300"), "", "", caminho=db)
    destino = fazer_backup(db, tmp_path / "backups", agora=datetime(2026, 10, 28, 9, 30, 0))
    assert destino.name == "radar-2026-10-28_093000.db"
    with sqlite3.connect(destino) as c:
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # A cópia é um arquivo só, sem depender de arquivos -wal ao lado.
        assert c.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert [f["nome"] for f in listar_fornecedores(destino)] == ["Fornecedor fictício"]


def test_copia_com_o_radar_aberto_e_escrita_pendente(db, conta, tmp_path):
    # Gravação confirmada que ainda está só no arquivo -wal, com uma conexão aberta como a do servidor.
    aberta = sqlite3.connect(db)
    try:
        aberta.execute("PRAGMA wal_autocheckpoint = 0")
        aberta.execute("INSERT INTO tarefa(titulo,semana,responsavel,concluida) VALUES('Tarefa fictícia',1,'Anna',0)")
        aberta.commit()
        assert (db.parent / (db.name + "-wal")).stat().st_size > 0
        destino = fazer_backup(db, tmp_path / "backups")
    finally:
        aberta.close()
    with sqlite3.connect(destino) as copia:
        assert copia.execute("SELECT titulo FROM tarefa").fetchall() == [("Tarefa fictícia",)]


def test_guarda_so_as_mais_recentes(db, tmp_path):
    pasta = tmp_path / "backups"
    inicio = datetime(2026, 10, 1, 8, 0, 0)
    for dia in range(5):
        fazer_backup(db, pasta, manter=3, agora=inicio + timedelta(days=dia))
    assert [b.name for b in listar_backups(pasta)] == [
        "radar-2026-10-03_080000.db", "radar-2026-10-04_080000.db", "radar-2026-10-05_080000.db"]
    assert db.exists()


def test_dois_backups_no_mesmo_segundo_nao_se_sobrescrevem(db, tmp_path):
    agora = datetime(2026, 10, 28, 9, 30, 0)
    a = fazer_backup(db, tmp_path / "b", agora=agora)
    b = fazer_backup(db, tmp_path / "b", agora=agora)
    assert a != b and a.exists() and b.exists()


def test_no_mesmo_segundo_a_limpeza_guarda_a_copia_mais_nova(db, tmp_path):
    agora = datetime(2026, 10, 28, 9, 30, 0)
    pasta = tmp_path / "b"
    for numero in range(1, 12):  # inclui -10 e -11, que como texto ficariam antes de -2
        salvar_fornecedor(f"Fornecedor fictício {numero}", "", "", Decimal(0), "", "", caminho=db)
        ultima = fazer_backup(db, pasta, manter=1, agora=agora)
    assert ultima.exists() and ultima.name == "radar-2026-10-28_093000-11.db"
    assert listar_backups(pasta) == [ultima]
    assert len(listar_fornecedores(ultima)) == 11


def test_ordem_considera_data_antes_da_sequencia(db, tmp_path):
    pasta = tmp_path / "b"
    cedo, tarde = datetime(2026, 10, 28, 9, 0, 0), datetime(2026, 10, 28, 10, 0, 0)
    fazer_backup(db, pasta, agora=cedo)
    fazer_backup(db, pasta, agora=cedo)
    fazer_backup(db, pasta, agora=tarde)
    assert [b.name for b in listar_backups(pasta)] == [
        "radar-2026-10-28_090000.db", "radar-2026-10-28_090000-2.db", "radar-2026-10-28_100000.db"]


def test_outros_arquivos_da_pasta_nao_sao_apagados(db, tmp_path):
    pasta = tmp_path / "backups"
    pasta.mkdir()
    (pasta / "anotacao.txt").write_text("não apagar")
    (pasta / "radar-copia-manual.db").write_text("não apagar")
    for segundo in range(3):
        fazer_backup(db, pasta, manter=1, agora=datetime(2026, 10, 28, 9, 0, segundo))
    assert (pasta / "anotacao.txt").exists() and (pasta / "radar-copia-manual.db").exists()
    assert len(listar_backups(pasta)) == 1


def test_banco_inexistente_nao_cria_banco_vazio(tmp_path):
    origem = tmp_path / "nao-existe.db"
    with pytest.raises(ValueError, match="Banco não encontrado"):
        fazer_backup(origem, tmp_path / "backups")
    assert not origem.exists()


@pytest.mark.parametrize("manter", [0, -1, "3"])
def test_quantidade_invalida(db, tmp_path, manter):
    with pytest.raises(ValueError, match="inteiro maior que zero"):
        fazer_backup(db, tmp_path / "backups", manter=manter)


def test_comando_no_terminal(db, tmp_path, monkeypatch, capsys):
    import radar.backup as backup
    monkeypatch.setattr(backup, "PASTA_PADRAO", tmp_path / "backups")
    assert main(["--manter", "2"]) == 0
    assert "Backup salvo em" in capsys.readouterr().out
    monkeypatch.setattr(backup.banco, "CAMINHO_PADRAO", tmp_path / "sumiu.db")
    assert main([]) == 1
    assert "Banco não encontrado" in capsys.readouterr().out


def test_servidor_faz_backup_ao_iniciar(db, tmp_path, monkeypatch, capsys):
    import radar.backup as backup
    import radar.servidor as servidor
    monkeypatch.setattr(backup, "PASTA_PADRAO", tmp_path / "backups")
    chamadas = []
    monkeypatch.setattr(servidor.uvicorn, "run", lambda app, **opcoes: chamadas.append(opcoes))
    servidor.main(["--porta", "8599"])
    assert len(listar_backups(tmp_path / "backups")) == 1 and chamadas[0]["port"] == 8599
    assert "Backup do banco salvo" in capsys.readouterr().out
    servidor.main(["--sem-backup"])
    assert len(listar_backups(tmp_path / "backups")) == 1


def test_falha_no_backup_nao_impede_o_servidor(db, tmp_path, monkeypatch, capsys):
    import radar.servidor as servidor

    def quebra(**_):
        raise OSError("disco cheio")

    monkeypatch.setattr(servidor, "fazer_backup", quebra)
    monkeypatch.setattr(servidor.uvicorn, "run", lambda app, **opcoes: None)
    servidor.main([])
    assert "backup ao iniciar falhou (disco cheio)" in capsys.readouterr().out


def test_dois_backups_ao_mesmo_tempo_nao_pegam_o_mesmo_nome(db, tmp_path, monkeypatch):
    # Simula outro backup que reservou o primeiro nome no mesmo segundo e ainda está copiando.
    import radar.backup as backup
    pasta = tmp_path / "b"
    pasta.mkdir()
    agora = datetime(2026, 10, 28, 9, 30, 0)
    (pasta / "radar-2026-10-28_093000.parcial").write_text("")
    destino = fazer_backup(db, pasta, agora=agora)
    assert destino.name == "radar-2026-10-28_093000-2.db"
    # E se o outro termina entre a consulta e a reserva, a reserva nota o nome pronto e passa adiante.
    original = backup.Path.open
    terminou = {"feito": False}

    def abre(self, *args, **kwargs):
        modo = args[0] if args else kwargs.get("mode", "r")
        if modo == "x" and self.name == "radar-2026-10-28_093000-3.parcial" and not terminou["feito"]:
            terminou["feito"] = True
            (pasta / "radar-2026-10-28_093000-3.db").write_bytes(destino.read_bytes())
        return original(self, *args, **kwargs)

    monkeypatch.setattr(backup.Path, "open", abre)
    outro = fazer_backup(db, pasta, agora=agora)
    assert outro.name == "radar-2026-10-28_093000-4.db"
    assert (pasta / "radar-2026-10-28_093000-3.db").exists()
    assert not list(pasta.glob("*-3.parcial")) and not list(pasta.glob("*-4.parcial"))


def test_falha_na_copia_libera_a_reserva(db, tmp_path, monkeypatch):
    import radar.backup as backup

    def quebra(origem, temporario):
        raise sqlite3.OperationalError("disco cheio")

    monkeypatch.setattr(backup, "_copiar", quebra)
    with pytest.raises(sqlite3.OperationalError):
        fazer_backup(db, tmp_path / "b")
    assert list((tmp_path / "b").iterdir()) == []
