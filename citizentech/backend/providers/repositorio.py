"""Acesso aos dados (SQLite). Pedidos e eventos ficam no servidor, então o
histórico não some quando o cidadão recarrega a página, e o painel mostra a
visão de todos (cuidador / gestor), não só a da sessão atual.

sqlite3 é da biblioteca padrão: zero dependência extra e um arquivo só,
montado num volume do Docker.
"""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocolo TEXT UNIQUE NOT NULL,
    criado_em TEXT NOT NULL,
    texto_mascarado TEXT NOT NULL,
    local TEXT NOT NULL,
    triagem TEXT NOT NULL,          -- JSON devolvido pela IA
    emergencia INTEGER NOT NULL,
    status TEXT NOT NULL,
    categoria TEXT,                 -- valores finais, depois da confirmação humana
    urgencia TEXT,
    util INTEGER
);
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    momento TEXT NOT NULL,
    classe TEXT NOT NULL,
    confianca REAL NOT NULL,
    dispositivo TEXT NOT NULL,
    alerta TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    incerto INTEGER NOT NULL,
    acertou INTEGER
);
CREATE INDEX IF NOT EXISTS ix_eventos_momento ON eventos(momento);
"""


def _bool(v):
    return None if v is None else bool(v)


class Repositorio:
    def __init__(self, caminho: Path | str):
        if str(caminho) != ":memory:":
            Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(caminho), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._trava = threading.Lock()
        with self._tx() as c:
            c.executescript(ESQUEMA)

    @contextmanager
    def _tx(self):
        with self._trava:
            try:
                yield self._con
                self._con.commit()
            except Exception:
                self._con.rollback()
                raise

    def fechar(self):
        self._con.close()

    # ---------- pedidos ----------
    def criar_pedido(self, protocolo, texto_mascarado, local, triagem: dict, emergencia: bool) -> dict:
        agora = datetime.now().isoformat(timespec="seconds")
        with self._tx() as c:
            cur = c.execute(
                "INSERT INTO pedidos (protocolo, criado_em, texto_mascarado, local, triagem, emergencia, status)"
                " VALUES (?,?,?,?,?,?, 'aguardando_confirmacao')",
                (protocolo, agora, texto_mascarado, local, json.dumps(triagem, ensure_ascii=False), int(emergencia)),
            )
            return self._pedido(c, cur.lastrowid)

    def obter_pedido(self, id_: int) -> dict | None:
        with self._tx() as c:
            return self._pedido(c, id_)

    def confirmar_pedido(self, id_: int, categoria: str, urgencia: str, util: bool | None) -> dict | None:
        with self._tx() as c:
            c.execute(
                "UPDATE pedidos SET status='confirmado', categoria=?, urgencia=?, util=? WHERE id=?",
                (categoria, urgencia, None if util is None else int(util), id_),
            )
            return self._pedido(c, id_)

    def listar_pedidos(self, categorias=None, urgencias=None) -> list[dict]:
        sql, args = "SELECT id FROM pedidos WHERE status='confirmado'", []
        if categorias:
            sql += f" AND categoria IN ({','.join('?' * len(categorias))})"; args += categorias
        if urgencias:
            sql += f" AND urgencia IN ({','.join('?' * len(urgencias))})"; args += urgencias
        with self._tx() as c:
            ids = [r[0] for r in c.execute(sql + " ORDER BY criado_em", args)]
            return [self._pedido(c, i) for i in ids]

    @staticmethod
    def _pedido(c, id_) -> dict | None:
        r = c.execute("SELECT * FROM pedidos WHERE id=?", (id_,)).fetchone()
        if r is None:
            return None
        d = dict(r)
        d["triagem"] = json.loads(d["triagem"])
        d["emergencia"] = bool(d["emergencia"])
        d["util"] = _bool(d["util"])
        return d

    # ---------- eventos ----------
    def criar_eventos(self, eventos: list[dict]) -> list[dict]:
        with self._tx() as c:
            ids = []
            for e in eventos:
                cur = c.execute(
                    "INSERT INTO eventos (momento, classe, confianca, dispositivo, alerta, mensagem, incerto)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (e["momento"].isoformat(timespec="seconds"), e["classe"], e["confianca"], e["dispositivo"],
                     e["alerta"], e["mensagem"], int(e["incerto"])),
                )
                ids.append(cur.lastrowid)
            return [self._evento(c, i) for i in ids]

    def eventos_recentes(self, dispositivo: str, classe: str, desde: datetime) -> int:
        with self._tx() as c:
            return c.execute(
                "SELECT COUNT(*) FROM eventos WHERE dispositivo=? AND classe=? AND momento>=?",
                (dispositivo, classe, desde.isoformat(timespec="seconds")),
            ).fetchone()[0]

    def listar_eventos(self, classes=None, confianca_min=0.0, desde=None, limite=500) -> list[dict]:
        sql, args = "SELECT * FROM eventos WHERE confianca>=?", [confianca_min]
        if classes:
            sql += f" AND classe IN ({','.join('?' * len(classes))})"; args += classes
        if desde:
            sql += " AND momento>=?"; args.append(desde.isoformat(timespec="seconds"))
        sql += " ORDER BY momento DESC LIMIT ?"; args.append(limite)
        with self._tx() as c:
            return [self._linha_evento(r) for r in c.execute(sql, args)]

    def feedback_evento(self, id_: int, acertou: bool) -> dict | None:
        with self._tx() as c:
            c.execute("UPDATE eventos SET acertou=? WHERE id=?", (int(acertou), id_))
            return self._evento(c, id_)

    def contar_eventos(self) -> int:
        with self._tx() as c:
            return c.execute("SELECT COUNT(*) FROM eventos").fetchone()[0]

    def _evento(self, c, id_):
        r = c.execute("SELECT * FROM eventos WHERE id=?", (id_,)).fetchone()
        return None if r is None else self._linha_evento(r)

    @staticmethod
    def _linha_evento(r) -> dict:
        d = dict(r)
        d["incerto"] = bool(d["incerto"])
        d["acertou"] = _bool(d["acertou"])
        return d

    # ---------- painel ----------
    def resumo(self) -> dict:
        with self._tx() as c:
            p = c.execute(
                "SELECT COUNT(*) n, SUM(urgencia='alta') alta,"
                " AVG(CASE WHEN categoria != json_extract(triagem,'$.categoria')"
                "  OR urgencia != json_extract(triagem,'$.urgencia') THEN 1.0 ELSE 0.0 END) corr,"
                " AVG(util) util FROM pedidos WHERE status='confirmado'"
            ).fetchone()
            e = c.execute(
                "SELECT COUNT(*) n, SUM(alerta != 'baixa') alerta, AVG(acertou) acerto FROM eventos"
            ).fetchone()
        return {
            "pedidos_confirmados": p["n"], "pedidos_alta": p["alta"] or 0,
            "taxa_correcao": p["corr"], "taxa_util": p["util"],
            "eventos_total": e["n"], "eventos_alerta": e["alerta"] or 0, "acerto_eventos": e["acerto"],
        }
