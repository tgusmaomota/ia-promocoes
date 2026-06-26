"""Estado mestre persistente para os serviços operacionais do Promogg."""

from banco import agora, conectar, inicializar_banco, registrar_evento_sistema


ONLINE = "ONLINE"
MANUTENCAO = "MANUTENCAO"
MANUTENCAO_PARCIAL = "MANUTENCAO_PARCIAL"
OFFLINE = "OFFLINE"
ESTADOS_VALIDOS = {ONLINE, MANUTENCAO, MANUTENCAO_PARCIAL, OFFLINE}


def inicializar_estado_sistema():
    inicializar_banco()
    with conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS estado_sistema (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                estado TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                motivo TEXT
            )
        """)
        conn.execute(
            "INSERT OR IGNORE INTO estado_sistema (id, estado, atualizado_em, motivo) VALUES (1, ?, ?, ?)",
            (ONLINE, agora(), "estado inicial"),
        )


def obter_estado_sistema():
    inicializar_estado_sistema()
    with conectar() as conn:
        row = conn.execute("SELECT estado, atualizado_em, motivo FROM estado_sistema WHERE id = 1").fetchone()
    return dict(row) if row else {"estado": ONLINE, "atualizado_em": "", "motivo": ""}


def definir_estado_sistema(estado, motivo=""):
    estado = str(estado or "").upper().strip()
    if estado not in ESTADOS_VALIDOS:
        raise ValueError("Estado do sistema inválido")
    inicializar_estado_sistema()
    with conectar() as conn:
        conn.execute(
            "UPDATE estado_sistema SET estado = ?, atualizado_em = ?, motivo = ? WHERE id = 1",
            (estado, agora(), str(motivo or "")[:500]),
        )
    registrar_evento_sistema("estado_sistema", "master", "sucesso", f"Estado alterado para {estado}", motivo)
    return obter_estado_sistema()


def automacao_ativa():
    return obter_estado_sistema()["estado"] == ONLINE


def em_manutencao():
    return obter_estado_sistema()["estado"] in {MANUTENCAO, MANUTENCAO_PARCIAL}


def em_offline():
    return obter_estado_sistema()["estado"] == OFFLINE
