import csv
import json
import os
import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from difflib import SequenceMatcher


DB_PATH = "banco.db"
PLATAFORMAS = ["mercado_livre"]
STATUS_APROVADOS = ("aprovado_auto", "aprovado_manual")
STATUS_CONTROLE = (*STATUS_APROVADOS, "pendente_revisao", "rejeitado", "publicado")


COLUNAS_PRODUTOS_HISTORICO = {
    "categoria_id": "TEXT",
    "categoria_nome": "TEXT",
    "menor_preco": "REAL",
    "maior_preco": "REAL",
    "preco_medio": "REAL",
    "ultima_verificacao": "TEXT",
    "vezes_verificado": "INTEGER NOT NULL DEFAULT 0",
    "variacao_preco": "REAL",
    "status_verificacao": "TEXT",
    "destaque_menor_preco": "INTEGER NOT NULL DEFAULT 0",
    "preco_original": "REAL",
    "desconto_percentual": "REAL",
    "economia_valor": "REAL",
    "categoria_nivel_1": "TEXT",
    "categoria_nivel_2": "TEXT",
    "categoria_nivel_3": "TEXT",
    "categoria_nivel_4": "TEXT",
    "categoria_caminho": "TEXT",
    "origem_categoria": "TEXT",
    "selo_mais_vendido": "INTEGER NOT NULL DEFAULT 0",
    "selo_loja_oficial": "INTEGER NOT NULL DEFAULT 0",
    "avaliacao": "REAL",
    "quantidade_avaliacoes": "INTEGER",
    "melhor_preco": "INTEGER NOT NULL DEFAULT 0",
    "parcelamento": "TEXT",
    "vendedor_nome": "TEXT",
    "vendedor_confiavel": "INTEGER NOT NULL DEFAULT 0",
    "dados_comerciais_origem": "TEXT",
    "dados_comerciais_atualizado_em": "TEXT",
    "percentual_off": "REAL",
    "motivo_indisponivel": "TEXT",
    "data_indisponivel": "TEXT",
    "descricao_curta": "TEXT",
}


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _colunas_tabela(conn, tabela):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({tabela})")}


def _backup_antes_migracao():
    if not os.path.exists(DB_PATH):
        return ""

    os.makedirs("backups", exist_ok=True)
    destino = os.path.join(
        "backups",
        f"banco_antes_historico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
    )
    shutil.copy2(DB_PATH, destino)
    return destino


def _migrar_historico_precos(conn):
    colunas_atuais = _colunas_tabela(conn, "produtos")
    colunas_faltantes = {
        nome: definicao
        for nome, definicao in COLUNAS_PRODUTOS_HISTORICO.items()
        if nome not in colunas_atuais
    }

    if colunas_faltantes:
        backup = _backup_antes_migracao()
        for nome, definicao in colunas_faltantes.items():
            conn.execute(f"ALTER TABLE produtos ADD COLUMN {nome} {definicao}")
        if backup:
            print(f"Backup do banco criado antes da migração: {backup}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            item_id TEXT NOT NULL,
            titulo TEXT NOT NULL,
            plataforma TEXT NOT NULL,
            preco REAL,
            data_verificacao TEXT NOT NULL,
            link_afiliado TEXT,
            categoria_id TEXT,
            categoria_nome TEXT,
            status_verificacao TEXT NOT NULL,
            fonte_preco TEXT,
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    """)
    colunas_historico = _colunas_tabela(conn, "historico_precos")
    if "fonte_preco" not in colunas_historico:
        backup = _backup_antes_migracao()
        conn.execute("ALTER TABLE historico_precos ADD COLUMN fonte_preco TEXT")
        if backup:
            print(f"Backup do banco criado antes da migração de fonte de preço: {backup}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_historico_item_data ON historico_precos(item_id, data_verificacao DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_historico_produto_data ON historico_precos(produto_id, data_verificacao DESC)")


def _migrar_status_aprovacao(conn):
    colunas = _colunas_tabela(conn, "postagens")
    novas_colunas = {
        "aprovado_por": "TEXT",
        "aprovado_em": "TEXT",
        "observacao_interna": "TEXT",
        "atualizado_em": "TEXT",
    }
    faltantes = {nome: definicao for nome, definicao in novas_colunas.items() if nome not in colunas}
    if faltantes:
        backup = _backup_antes_migracao()
        for nome, definicao in faltantes.items():
            conn.execute(f"ALTER TABLE postagens ADD COLUMN {nome} {definicao}")
        if backup:
            print(f"Backup do banco criado antes da migração de aprovação: {backup}")

    conn.execute(
        """
        UPDATE postagens
        SET status = 'aprovado_auto',
            aprovado_por = COALESCE(aprovado_por, 'migracao_legado'),
            aprovado_em = COALESCE(aprovado_em, data_criacao),
            atualizado_em = COALESCE(atualizado_em, ?)
        WHERE status = 'pendente'
        """,
        (agora(),),
    )
    conn.execute(
        """
        UPDATE postagens
        SET status = 'aprovado_manual',
            aprovado_por = COALESCE(aprovado_por, 'migracao_legado'),
            aprovado_em = COALESCE(aprovado_em, data_criacao),
            atualizado_em = COALESCE(atualizado_em, ?)
        WHERE status = 'aprovado'
        """,
        (agora(),),
    )


def _criar_tabela_cliques(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cliques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oferta_id TEXT NOT NULL,
            item_id TEXT,
            titulo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            origem TEXT NOT NULL DEFAULT 'site_publico',
            pagina_origem TEXT NOT NULL DEFAULT '/',
            tipo_evento TEXT NOT NULL DEFAULT 'ver_oferta',
            criado_em TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cliques_oferta ON cliques(oferta_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cliques_data ON cliques(criado_em)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cliques_categoria ON cliques(categoria)")
    colunas = _colunas_tabela(conn, "cliques")
    novas_colunas = {
        "item_id": "TEXT",
        "origem": "TEXT NOT NULL DEFAULT 'site_publico'",
        "pagina_origem": "TEXT NOT NULL DEFAULT '/'",
        "tipo_evento": "TEXT NOT NULL DEFAULT 'ver_oferta'",
    }
    faltantes = {nome: definicao for nome, definicao in novas_colunas.items() if nome not in colunas}
    if faltantes:
        backup = _backup_antes_migracao()
        for nome, definicao in faltantes.items():
            conn.execute(f"ALTER TABLE cliques ADD COLUMN {nome} {definicao}")
        if backup:
            print(f"Backup do banco criado antes da migração de analytics: {backup}")


def _criar_tabelas_assistente(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS perguntas_assistente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pergunta TEXT NOT NULL,
            resposta TEXT NOT NULL,
            produtos_usados TEXT NOT NULL DEFAULT '[]',
            modelo TEXT,
            modo_resposta TEXT NOT NULL,
            criado_em TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback_assistente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pergunta_id INTEGER NOT NULL,
            feedback TEXT NOT NULL CHECK(feedback IN ('util', 'nao_util')),
            observacao TEXT,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (pergunta_id) REFERENCES perguntas_assistente(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memoria_produtos (
            item_id TEXT PRIMARY KEY,
            titulo TEXT NOT NULL,
            resumo_preco TEXT NOT NULL,
            resumo_tendencia TEXT NOT NULL,
            melhor_momento_compra TEXT NOT NULL,
            ultima_atualizacao TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_perguntas_assistente_data ON perguntas_assistente(criado_em DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_assistente_pergunta ON feedback_assistente(pergunta_id)")


def _criar_tabela_sistema_eventos(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sistema_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_evento TEXT NOT NULL,
            origem TEXT NOT NULL,
            status TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            data_evento TEXT NOT NULL,
            detalhes TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sistema_eventos_tipo_data ON sistema_eventos(tipo_evento, data_evento DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sistema_eventos_status_data ON sistema_eventos(status, data_evento DESC)")


def _criar_tabelas_revisora(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analises_revisora (
            postagem_id INTEGER PRIMARY KEY,
            item_id TEXT NOT NULL,
            score_curadoria REAL NOT NULL DEFAULT 0,
            score_revisora REAL NOT NULL,
            parecer TEXT NOT NULL,
            sugestao TEXT NOT NULL,
            modo_resposta TEXT NOT NULL,
            atualizado_em TEXT NOT NULL,
            FOREIGN KEY (postagem_id) REFERENCES postagens(id)
        )
    """)
    if "score_curadoria" not in _colunas_tabela(conn, "analises_revisora"):
        _backup_antes_migracao()
        conn.execute("ALTER TABLE analises_revisora ADD COLUMN score_curadoria REAL NOT NULL DEFAULT 0")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback_revisora (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT NOT NULL,
            sugestao_ia TEXT NOT NULL,
            decisao_usuario TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memoria_revisora (
            categoria TEXT PRIMARY KEY,
            total_feedback INTEGER NOT NULL DEFAULT 0,
            aprovacoes INTEGER NOT NULL DEFAULT 0,
            rejeicoes INTEGER NOT NULL DEFAULT 0,
            cliques INTEGER NOT NULL DEFAULT 0,
            ultima_atualizacao TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_revisora_item ON feedback_revisora(item_id, data DESC)")


def _criar_tabela_saude_coleta_api(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coleta_api_saude (
            chave TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            mensagem TEXT,
            atualizado_em TEXT NOT NULL,
            bloqueado_ate TEXT
        )
    """)


@contextmanager
def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar_banco():
    with conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plataformas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                titulo TEXT NOT NULL,
                preco_atual REAL NOT NULL DEFAULT 0,
                preco_anterior REAL,
                preco_original REAL,
                desconto_percentual REAL,
                economia_valor REAL,
                link_original TEXT NOT NULL,
                link_afiliado TEXT,
                plataforma TEXT NOT NULL,
                categoria TEXT DEFAULT 'ofertas',
                data_coleta TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'coletado',
                vendedor_reputacao REAL,
                avaliacoes REAL,
                quantidade_vendida REAL,
                estoque INTEGER DEFAULT 1,
                imagem TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS promocoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                desconto REAL NOT NULL DEFAULT 0,
                score REAL NOT NULL DEFAULT 0,
                motivo TEXT,
                status TEXT NOT NULL DEFAULT 'pendente',
                criado_em TEXT NOT NULL,
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS postagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                promocao_id INTEGER,
                titulo TEXT NOT NULL,
                preco REAL NOT NULL DEFAULT 0,
                link_afiliado TEXT NOT NULL,
                plataforma TEXT NOT NULL,
                categoria TEXT DEFAULT 'ofertas',
                texto_post TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                data_criacao TEXT NOT NULL,
                data_publicacao TEXT,
                motivo TEXT,
                aprovado_por TEXT,
                aprovado_em TEXT,
                observacao_interna TEXT,
                atualizado_em TEXT,
                FOREIGN KEY (produto_id) REFERENCES produtos(id),
                FOREIGN KEY (promocao_id) REFERENCES promocoes(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                etapa TEXT NOT NULL,
                nivel TEXT NOT NULL DEFAULT 'info',
                mensagem TEXT NOT NULL,
                dados TEXT,
                criado_em TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_item_id ON produtos(item_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_link ON produtos(link_original)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_postagens_status ON postagens(status)")
        _migrar_historico_precos(conn)
        _migrar_status_aprovacao(conn)
        _criar_tabela_cliques(conn)
        _criar_tabelas_assistente(conn)
        _criar_tabela_sistema_eventos(conn)
        _criar_tabelas_revisora(conn)
        _criar_tabela_saude_coleta_api(conn)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS estado_sistema (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                estado TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                motivo TEXT
            )
        """)
        conn.execute(
            "INSERT OR IGNORE INTO estado_sistema (id, estado, atualizado_em, motivo) VALUES (1, 'ONLINE', ?, 'estado inicial')",
            (agora(),),
        )
        for plataforma in PLATAFORMAS:
            conn.execute(
                """
                INSERT OR IGNORE INTO plataformas (nome, ativo, criado_em)
                VALUES (?, 1, ?)
                """,
                (plataforma, agora()),
            )


def registrar_saude_coleta_api(status, mensagem="", bloqueado_ate=None):
    inicializar_banco()
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO coleta_api_saude (chave, status, mensagem, atualizado_em, bloqueado_ate)
            VALUES ('busca', ?, ?, ?, ?)
            ON CONFLICT(chave) DO UPDATE SET
                status=excluded.status, mensagem=excluded.mensagem,
                atualizado_em=excluded.atualizado_em, bloqueado_ate=excluded.bloqueado_ate
            """,
            (str(status), str(mensagem)[:300], agora(), bloqueado_ate),
        )


def obter_saude_coleta_api():
    inicializar_banco()
    with conectar() as conn:
        row = conn.execute(
            "SELECT status, mensagem, atualizado_em, bloqueado_ate FROM coleta_api_saude WHERE chave = 'busca'"
        ).fetchone()
    return dict(row) if row else {
        "status": "sem_registro", "mensagem": "", "atualizado_em": "", "bloqueado_ate": None,
    }

def registrar_log(etapa, mensagem, nivel="info", dados=""):
    inicializar_banco()
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO logs (etapa, nivel, mensagem, dados, criado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (etapa, nivel, mensagem, dados, agora()),
        )
    print(f"[{nivel.upper()}] {etapa}: {mensagem}")


def _sanitizar_evento(valor, limite=1000):
    """Remove URLs e padrões que poderiam carregar credenciais para a visão de saúde."""
    texto = " ".join(str(valor or "").replace("\n", " ").split())
    texto = re.sub(r"https?://\S+", "[url removida]", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b(token|secret|password|senha|api[_-]?key)\s*[:=]\s*\S+", r"\1=[removido]", texto, flags=re.IGNORECASE)
    return texto[:limite]


def registrar_evento_sistema(tipo_evento, origem, status, mensagem, detalhes=""):
    """Registra um evento operacional sem guardar segredos, URLs ou logs brutos."""
    # Os valores antigos continuam aceitos. A classificação detalhada é feita
    # pela camada de saúde, sem perder a semântica original do evento.
    status = {
        "concluido": "sucesso",
        "atencao": "alerta",
        "warning": "alerta",
    }.get(str(status).lower(), str(status).lower())
    inicializar_banco()
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO sistema_eventos (tipo_evento, origem, status, mensagem, data_evento, detalhes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _sanitizar_evento(tipo_evento, 80),
                _sanitizar_evento(origem, 80),
                _sanitizar_evento(status, 40),
                _sanitizar_evento(mensagem, 500),
                agora(),
                _sanitizar_evento(detalhes, 1000),
            ),
        )


def registrar_clique(oferta_id, titulo, categoria, item_id="", origem="site_publico", pagina_origem="/", tipo_evento="ver_oferta"):
    """Persiste apenas dados agregáveis da oferta, sem IP ou identificadores pessoais."""
    oferta_id = str(oferta_id or "").strip()
    item_id = str(item_id or oferta_id).strip().upper()
    titulo = " ".join(str(titulo or "").split())[:300]
    categoria = " ".join(str(categoria or "ofertas").split())[:120] or "ofertas"
    origem = " ".join(str(origem or "site_publico").split())[:40] or "site_publico"
    pagina_origem = str(pagina_origem or "/").strip()[:300] or "/"
    tipo_evento = " ".join(str(tipo_evento or "ver_oferta").split())[:40] or "ver_oferta"
    if not oferta_id or len(oferta_id) > 80 or not item_id or len(item_id) > 80 or not titulo:
        raise ValueError("Evento de clique inválido")
    inicializar_banco()
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO cliques (oferta_id, item_id, titulo, categoria, origem, pagina_origem, tipo_evento, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (oferta_id, item_id, titulo, categoria, origem, pagina_origem, tipo_evento, agora()),
        )


def resumo_cliques(limite=20):
    inicializar_banco()
    with conectar() as conn:
        produtos = [dict(row) for row in conn.execute(
            """
            SELECT COALESCE(NULLIF(item_id, ''), oferta_id) AS item_id, titulo, categoria, COUNT(*) AS total
            FROM cliques WHERE COALESCE(tipo_evento, 'ver_oferta') != 'teste'
            GROUP BY COALESCE(NULLIF(item_id, ''), oferta_id), titulo, categoria
            ORDER BY total DESC, titulo ASC LIMIT ?
            """,
            (limite,),
        ).fetchall()]
        categorias = [dict(row) for row in conn.execute(
            "SELECT categoria, COUNT(*) AS total FROM cliques WHERE COALESCE(tipo_evento, 'ver_oferta') != 'teste' GROUP BY categoria ORDER BY total DESC, categoria ASC"
        ).fetchall()]
        dias = [dict(row) for row in conn.execute(
            "SELECT substr(criado_em, 1, 10) AS periodo, COUNT(*) AS total FROM cliques WHERE COALESCE(tipo_evento, 'ver_oferta') != 'teste' GROUP BY periodo ORDER BY periodo"
        ).fetchall()]
        meses = [dict(row) for row in conn.execute(
            "SELECT substr(criado_em, 1, 7) AS periodo, COUNT(*) AS total FROM cliques WHERE COALESCE(tipo_evento, 'ver_oferta') != 'teste' GROUP BY periodo ORDER BY periodo"
        ).fetchall()]
    return {"produtos": produtos, "categorias": categorias, "dias": dias, "meses": meses}


def registrar_pergunta_assistente(pergunta, resposta, produtos_usados, modelo="", modo_resposta="regras"):
    with conectar() as conn:
        cursor = conn.execute(
            """
            INSERT INTO perguntas_assistente (pergunta, resposta, produtos_usados, modelo, modo_resposta, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(pergunta or "")[:1000],
                str(resposta or "")[:8000],
                json.dumps(produtos_usados or [], ensure_ascii=False),
                str(modelo or "")[:120],
                str(modo_resposta or "regras")[:40],
                agora(),
            ),
        )
        return cursor.lastrowid


def registrar_feedback_assistente(pergunta_id, feedback, observacao=""):
    if feedback not in {"util", "nao_util"}:
        raise ValueError("Feedback inválido")
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO feedback_assistente (pergunta_id, feedback, observacao, criado_em)
            VALUES (?, ?, ?, ?)
            """,
            (int(pergunta_id), feedback, str(observacao or "")[:2000], agora()),
        )


def listar_perguntas_assistente(limite=20):
    with conectar() as conn:
        return [dict(row) for row in conn.execute(
            """
            SELECT id, pergunta, resposta, produtos_usados, modelo, modo_resposta, criado_em
            FROM perguntas_assistente ORDER BY id DESC LIMIT ?
            """,
            (limite,),
        ).fetchall()]


def normalizar_texto(texto):
    return " ".join(str(texto).lower().strip().split())


def titulo_muito_parecido(titulo_a, titulo_b, limite=0.92):
    a = normalizar_texto(titulo_a)
    b = normalizar_texto(titulo_b)

    if not a or not b:
        return False

    return SequenceMatcher(None, a, b).ratio() >= limite


def buscar_duplicado(produto):
    inicializar_banco()
    link = str(produto.get("link_original") or produto.get("link") or "").strip()
    link_afiliado = str(produto.get("link_afiliado") or "").strip()
    item_id = str(produto.get("item_id", "")).strip()
    titulo = str(produto.get("titulo", "")).strip()
    plataforma = str(produto.get("plataforma", "mercado_livre")).strip()

    with conectar() as conn:
        # item_id é a identidade estável fornecida pela API do Mercado Livre.
        if item_id:
            row = conn.execute(
                """
                SELECT * FROM produtos
                WHERE item_id = ? AND plataforma = ?
                LIMIT 1
                """,
                (item_id, plataforma),
            ).fetchone()
            if row:
                return row, "item_id"

        if link:
            row = conn.execute(
                """
                SELECT * FROM produtos
                WHERE link_original = ? AND plataforma = ?
                LIMIT 1
                """,
                (link, plataforma),
            ).fetchone()
            if row:
                return row, "link"

        if link_afiliado:
            row = conn.execute(
                """
                SELECT * FROM produtos
                WHERE link_afiliado = ? AND plataforma = ?
                LIMIT 1
                """,
                (link_afiliado, plataforma),
            ).fetchone()
            if not row:
                row = conn.execute(
                    """
                    SELECT produtos.*
                    FROM postagens
                    JOIN produtos ON produtos.id = postagens.produto_id
                    WHERE postagens.link_afiliado = ? AND produtos.plataforma = ?
                    LIMIT 1
                    """,
                    (link_afiliado, plataforma),
                ).fetchone()
            if row:
                return row, "link_afiliado"

        rows = conn.execute(
            "SELECT * FROM produtos WHERE plataforma = ?",
            (plataforma,),
        ).fetchall()
        for row in rows:
            if titulo_muito_parecido(titulo, row["titulo"]):
                return row, "titulo_muito_parecido"

    return None, ""


def salvar_ou_atualizar_produto_api(produto):
    """Upsert de coleta oficial, preservando histórico e evitando duplicações."""
    inicializar_banco()
    existente, criterio = buscar_duplicado(produto)
    preco = float(produto.get("preco_atual") or produto.get("preco") or 0)
    if preco <= 0:
        raise ValueError("produto da API sem preço válido")

    if not existente:
        produto = dict(produto)
        produto["status"] = "coletado"
        criado, produto_id, _ = salvar_produto(produto)
        return {"acao": "criado" if criado else "ignorado", "produto_id": produto_id, "criterio": ""}

    produto_id = existente["id"]
    anterior = float(existente["preco_atual"] or 0)
    mudou_preco = round(anterior, 2) != round(preco, 2)
    link = str(produto.get("link_original") or produto.get("link") or "").strip()
    categoria_nome = str(produto.get("categoria_nome") or produto.get("categoria") or "").strip()
    status_atual = str(existente["status"] or "")
    status_novo = "coletado" if status_atual in ("indisponivel", "erro") else status_atual
    with conectar() as conn:
        conn.execute(
            """
            UPDATE produtos
            SET titulo=?, preco_atual=?, preco_anterior=?, link_original=COALESCE(NULLIF(?, ''), link_original),
                link_afiliado=COALESCE(NULLIF(?, ''), link_afiliado), imagem=COALESCE(NULLIF(?, ''), imagem),
                categoria_id=COALESCE(NULLIF(?, ''), categoria_id), categoria_nome=COALESCE(NULLIF(?, ''), categoria_nome),
                categoria=COALESCE(NULLIF(?, ''), categoria),
                preco_original=COALESCE(?, preco_original),
                desconto_percentual=COALESCE(?, desconto_percentual),
                economia_valor=COALESCE(?, economia_valor),
                categoria_nivel_1=COALESCE(NULLIF(?, ''), categoria_nivel_1),
                categoria_nivel_2=COALESCE(NULLIF(?, ''), categoria_nivel_2),
                categoria_nivel_3=COALESCE(NULLIF(?, ''), categoria_nivel_3),
                categoria_nivel_4=COALESCE(NULLIF(?, ''), categoria_nivel_4),
                categoria_caminho=COALESCE(NULLIF(?, ''), categoria_caminho),
                origem_categoria=COALESCE(NULLIF(?, ''), origem_categoria),
                selo_mais_vendido=MAX(selo_mais_vendido, ?), selo_loja_oficial=MAX(selo_loja_oficial, ?),
                avaliacao=COALESCE(?, avaliacao), quantidade_avaliacoes=COALESCE(?, quantidade_avaliacoes),
                melhor_preco=MAX(melhor_preco, ?), parcelamento=COALESCE(NULLIF(?, ''), parcelamento),
                vendedor_nome=COALESCE(NULLIF(?, ''), vendedor_nome), vendedor_confiavel=MAX(vendedor_confiavel, ?),
                dados_comerciais_origem=COALESCE(NULLIF(?, ''), dados_comerciais_origem),
                dados_comerciais_atualizado_em=COALESCE(NULLIF(?, ''), dados_comerciais_atualizado_em),
                percentual_off=COALESCE(?, percentual_off),
                descricao_curta=COALESCE(NULLIF(?, ''), descricao_curta),
                status=?, data_coleta=?, atualizado_em=?
            WHERE id=?
            """,
            (
                str(produto.get("titulo") or existente["titulo"]), preco, produto.get("preco_anterior"), link,
                str(produto.get("link_afiliado") or ""), str(produto.get("imagem") or ""),
                str(produto.get("categoria_id") or ""), categoria_nome, categoria_nome,
                produto.get("preco_original"), produto.get("desconto_percentual"), produto.get("economia_valor"),
                str(produto.get("categoria_nivel_1", "")).strip(), str(produto.get("categoria_nivel_2", "")).strip(),
                str(produto.get("categoria_nivel_3", "")).strip(), str(produto.get("categoria_nivel_4", "")).strip(),
                str(produto.get("categoria_caminho", "")).strip(), str(produto.get("origem_categoria", "")).strip(),
                int(bool(produto.get("selo_mais_vendido"))), int(bool(produto.get("selo_loja_oficial"))),
                produto.get("avaliacao"), produto.get("quantidade_avaliacoes"), int(bool(produto.get("melhor_preco"))),
                str(produto.get("parcelamento", "")).strip(), str(produto.get("vendedor_nome", "")).strip(),
                int(bool(produto.get("vendedor_confiavel"))), str(produto.get("dados_comerciais_origem", "")).strip(),
                str(produto.get("dados_comerciais_atualizado_em", "")).strip(),
                produto.get("percentual_off"),
                str(produto.get("descricao_curta", "")).strip()[:500],
                status_novo, produto.get("data_coleta") or agora(), agora(), produto_id,
            ),
        )

    produto_historico = dict(existente)
    produto_historico.update(produto)
    produto_historico["link_afiliado"] = produto.get("link_afiliado") or existente["link_afiliado"]
    # Cada coleta válida é uma observação histórica, inclusive quando o preço
    # ficou igual. Assim tendência e última verificação não dependem de queda.
    registrar_observacao_preco(produto_id, produto_historico, preco, "coletado")
    if mudou_preco:
        # Reavaliação registra a nova evidência, mas não altera publicação nem aprovação existente.
        from analisador_promocao import analisar_produto

        analise = analisar_produto(produto_historico)
        salvar_promocao(
            produto_id,
            analise["desconto"],
            analise["score"],
            "reavaliado",
            f"Atualização pela API oficial: {analise['motivo']}",
        )
    registrar_log("coleta_api", f"Produto atualizado via API ({criterio}): {produto_historico['titulo']}")
    return {"acao": "atualizado", "produto_id": produto_id, "criterio": criterio, "mudou_preco": mudou_preco}


def atualizar_link_afiliado_oficial(produto_id, link_afiliado):
    """Registra somente link oficial meli.la extraído do portal afiliado."""
    from gerador_link_mercadolivre import link_afiliado_valido

    link_afiliado = str(link_afiliado or "").strip()
    if not link_afiliado_valido(link_afiliado):
        raise ValueError("Link afiliado oficial meli.la inválido")
    inicializar_banco()
    with conectar() as conn:
        conn.execute(
            "UPDATE produtos SET link_afiliado = ?, atualizado_em = ? WHERE id = ?",
            (link_afiliado, agora(), produto_id),
        )
    registrar_log("afiliados", f"Link oficial meli.la salvo para produto={produto_id}")


def salvar_produto(produto):
    inicializar_banco()
    duplicado, motivo = buscar_duplicado(produto)

    if duplicado:
        atualizar_categoria_produto(duplicado["id"], produto)
        registrar_log(
            "deduplicacao",
            f"Produto ignorado por duplicidade ({motivo}): {produto.get('titulo', '')}",
        )
        return False, duplicado["id"], motivo

    data = agora()
    link_original = str(produto.get("link_original") or produto.get("link") or "").strip()
    preco_atual = float(produto.get("preco_atual") or produto.get("preco") or 0)
    plataforma = str(produto.get("plataforma", "mercado_livre")).strip()

    with conectar() as conn:
        cursor = conn.execute(
            """
            INSERT INTO produtos (
                item_id, titulo, preco_atual, preco_anterior, link_original,
                link_afiliado, plataforma, categoria, data_coleta, status,
                vendedor_reputacao, avaliacoes, quantidade_vendida, estoque,
                imagem, criado_em, atualizado_em, categoria_id, categoria_nome
                , preco_original, desconto_percentual, economia_valor,
                categoria_nivel_1, categoria_nivel_2, categoria_nivel_3, categoria_nivel_4,
                categoria_caminho, origem_categoria, selo_mais_vendido, selo_loja_oficial,
                avaliacao, quantidade_avaliacoes, melhor_preco, parcelamento, vendedor_nome,
                vendedor_confiavel, dados_comerciais_origem, dados_comerciais_atualizado_em
                , percentual_off, descricao_curta
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(produto.get("item_id", "")).strip(),
                str(produto.get("titulo", "")).strip(),
                preco_atual,
                produto.get("preco_anterior"),
                link_original,
                str(produto.get("link_afiliado", "")).strip(),
                plataforma,
                str(produto.get("categoria", "ofertas")).strip() or "ofertas",
                produto.get("data_coleta") or data,
                str(produto.get("status", "coletado")).strip() or "coletado",
                produto.get("vendedor_reputacao"),
                produto.get("avaliacoes"),
                produto.get("quantidade_vendida"),
                int(produto.get("estoque", 1) or 0),
                str(produto.get("imagem", "")).strip(),
                data,
                data,
                str(produto.get("categoria_id", "")).strip(),
                str(produto.get("categoria_nome", "")).strip(),
                produto.get("preco_original"),
                produto.get("desconto_percentual"),
                produto.get("economia_valor"),
                str(produto.get("categoria_nivel_1", "")).strip(),
                str(produto.get("categoria_nivel_2", "")).strip(),
                str(produto.get("categoria_nivel_3", "")).strip(),
                str(produto.get("categoria_nivel_4", "")).strip(),
                str(produto.get("categoria_caminho", "")).strip(),
                str(produto.get("origem_categoria", "")).strip(),
                int(bool(produto.get("selo_mais_vendido"))),
                int(bool(produto.get("selo_loja_oficial"))),
                produto.get("avaliacao"), produto.get("quantidade_avaliacoes"),
                int(bool(produto.get("melhor_preco"))), str(produto.get("parcelamento", "")).strip(),
                str(produto.get("vendedor_nome", "")).strip(), int(bool(produto.get("vendedor_confiavel"))),
                str(produto.get("dados_comerciais_origem", "")).strip(),
                str(produto.get("dados_comerciais_atualizado_em", "")).strip(),
                produto.get("percentual_off"),
                str(produto.get("descricao_curta", "")).strip()[:500],
            ),
        )
        produto_id = cursor.lastrowid

    registrar_observacao_preco(produto_id, produto, preco_atual, "coletado")
    registrar_log("coleta", f"Produto salvo: {produto.get('titulo', '')}")
    return True, produto_id, ""


def atualizar_categoria_produto(produto_id, produto):
    categoria_id = str(produto.get("categoria_id", "")).strip()
    categoria_nome = str(produto.get("categoria_nome", "")).strip()
    categoria = categoria_nome or str(produto.get("categoria", "")).strip()
    if not categoria_id and not categoria:
        return

    with conectar() as conn:
        conn.execute(
            """
            UPDATE produtos
            SET categoria_id = COALESCE(NULLIF(?, ''), categoria_id),
                categoria_nome = COALESCE(NULLIF(?, ''), categoria_nome),
                categoria = COALESCE(NULLIF(?, ''), categoria),
                atualizado_em = ?
            WHERE id = ?
            """,
            (categoria_id, categoria_nome, categoria, agora(), produto_id),
        )


def registrar_observacao_preco(
    produto_id,
    produto,
    preco,
    status_verificacao="ok",
    data_verificacao=None,
    fonte_preco=None,
):
    """Acrescenta uma observação de preço sem alterar observações anteriores."""
    inicializar_banco()
    try:
        preco = float(preco)
    except (TypeError, ValueError):
        preco = None

    if preco is not None and preco <= 0:
        preco = None

    data_verificacao = data_verificacao or agora()
    fonte_preco = str(
        fonte_preco
        or produto.get("origem_coleta")
        or {"ok": "api_item", "coletado": "coleta", "baseline_local": "baseline_local"}.get(status_verificacao, status_verificacao)
    ).strip()[:80]
    item_id = str(produto.get("item_id", "")).strip()
    if not item_id:
        raise ValueError("Não é possível registrar histórico sem item_id")

    with conectar() as conn:
        anterior = conn.execute(
            """
            SELECT preco FROM historico_precos
            WHERE produto_id = ? AND preco IS NOT NULL AND status_verificacao IN ('ok', 'coletado', 'baseline_local')
            ORDER BY id DESC LIMIT 1
            """,
            (produto_id,),
        ).fetchone()
        preco_anterior = float(anterior["preco"]) if anterior else None
        variacao = round(preco - preco_anterior, 2) if preco is not None and preco_anterior is not None else 0.0

        conn.execute(
            """
            INSERT INTO historico_precos (
                produto_id, item_id, titulo, plataforma, preco, data_verificacao,
                link_afiliado, categoria_id, categoria_nome, status_verificacao, fonte_preco
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                produto_id,
                item_id,
                str(produto.get("titulo", "")).strip(),
                str(produto.get("plataforma", "mercado_livre")).strip(),
                preco,
                data_verificacao,
                str(produto.get("link_afiliado", "")).strip(),
                str(produto.get("categoria_id", "")).strip(),
                str(produto.get("categoria_nome") or produto.get("categoria") or "").strip(),
                status_verificacao,
                fonte_preco,
            ),
        )

        estatisticas = conn.execute(
            """
            SELECT MIN(preco) AS menor, MAX(preco) AS maior, AVG(preco) AS medio, COUNT(preco) AS total
            FROM historico_precos
            WHERE produto_id = ? AND preco IS NOT NULL AND status_verificacao IN ('ok', 'coletado', 'baseline_local')
            """,
            (produto_id,),
        ).fetchone()
        menor = estatisticas["menor"]
        maior = estatisticas["maior"]
        medio = estatisticas["medio"]
        destaque = int(
            status_verificacao != "baseline_local"
            and preco is not None
            and menor is not None
            and float(preco) <= float(menor)
        )
        categoria_nome = str(produto.get("categoria_nome") or produto.get("categoria") or "").strip()

        conn.execute(
            """
            UPDATE produtos
            SET preco_anterior = ?, preco_atual = COALESCE(?, preco_atual),
                menor_preco = ?, maior_preco = ?, preco_medio = ?, ultima_verificacao = ?,
                vezes_verificado = ?, variacao_preco = ?, status_verificacao = ?,
                destaque_menor_preco = ?, categoria_id = COALESCE(NULLIF(?, ''), categoria_id),
                categoria_nome = COALESCE(NULLIF(?, ''), categoria_nome),
                categoria = COALESCE(NULLIF(?, ''), categoria),
                imagem = COALESCE(NULLIF(?, ''), imagem), atualizado_em = ?
            WHERE id = ?
            """,
            (
                preco_anterior, preco, menor, maior, medio, data_verificacao, estatisticas["total"],
                variacao, status_verificacao, destaque, str(produto.get("categoria_id", "")).strip(),
                categoria_nome, categoria_nome, str(produto.get("imagem", "")).strip(), agora(), produto_id,
            ),
        )

    return {
        "preco_anterior": preco_anterior,
        "variacao": variacao,
        "menor_preco": menor,
        "destaque_menor_preco": bool(destaque),
    }


def semear_historico_existente():
    """Cria uma linha-base para produtos antigos que não possuíam histórico."""
    inicializar_banco()
    with conectar() as conn:
        produtos = [dict(row) for row in conn.execute(
            """
            SELECT produtos.* FROM produtos
            WHERE item_id != ''
              AND preco_atual > 0
              AND NOT EXISTS (
                  SELECT 1 FROM historico_precos
                  WHERE historico_precos.produto_id = produtos.id
              )
            """
        ).fetchall()]

    for produto in produtos:
        registrar_observacao_preco(
            produto["id"], produto, produto["preco_atual"], "baseline_local"
        )
    return len(produtos)


def marcar_produto_indisponivel(produto_id, produto, motivo="item indisponível"):
    registrar_observacao_preco(produto_id, produto, None, "indisponivel")
    with conectar() as conn:
        conn.execute(
            "UPDATE produtos SET status = 'indisponivel', motivo_indisponivel = ?, data_indisponivel = ?, atualizado_em = ? WHERE id = ?",
            (str(motivo)[:500], agora(), agora(), produto_id),
        )
    registrar_log("monitor_precos", f"Produto indisponível: {produto.get('titulo', '')}", dados=motivo)


def salvar_promocao(produto_id, desconto, score, status, motivo):
    inicializar_banco()
    with conectar() as conn:
        cursor = conn.execute(
            """
            INSERT INTO promocoes (produto_id, desconto, score, motivo, status, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (produto_id, float(desconto or 0), float(score or 0), motivo, status, agora()),
        )
        return cursor.lastrowid


def prioridade_status(status):
    prioridades = {
        "rejeitado": 0,
        "pendente_revisao": 1,
        "aprovado_auto": 2,
        "aprovado_manual": 3,
        "publicado": 4,
    }
    return prioridades.get(status, 1)


def criar_postagem(
    produto_id,
    promocao_id,
    produto,
    texto_post,
    status="aprovado_auto",
    data_publicacao=None,
    motivo="",
):
    inicializar_banco()
    data = agora()
    with conectar() as conn:
        existente = conn.execute(
            """
            SELECT id FROM postagens
            WHERE link_afiliado = ? OR texto_post = ?
            LIMIT 1
            """,
            (produto["link_afiliado"], texto_post),
        ).fetchone()

        if existente:
            atual = conn.execute(
                "SELECT status FROM postagens WHERE id = ?",
                (existente["id"],),
            ).fetchone()

            if atual and prioridade_status(status) >= prioridade_status(atual["status"]):
                conn.execute(
                    """
                    UPDATE postagens
                    SET status = ?, data_publicacao = COALESCE(?, data_publicacao),
                        motivo = COALESCE(NULLIF(?, ''), motivo),
                        aprovado_por = CASE WHEN ? IN ('aprovado_auto', 'aprovado_manual') THEN COALESCE(aprovado_por, ?) ELSE aprovado_por END,
                        aprovado_em = CASE WHEN ? IN ('aprovado_auto', 'aprovado_manual') THEN COALESCE(aprovado_em, ?) ELSE aprovado_em END,
                        atualizado_em = ?
                    WHERE id = ?
                    """,
                    (status, data_publicacao, motivo, status, "curadoria_automatica", status, agora(), agora(), existente["id"]),
                )

            return existente["id"]

        cursor = conn.execute(
            """
            INSERT INTO postagens (
                produto_id, promocao_id, titulo, preco, link_afiliado, plataforma,
                categoria, texto_post, status, data_criacao, data_publicacao, motivo
                , aprovado_por, aprovado_em, observacao_interna, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                produto_id,
                promocao_id,
                produto["titulo"],
                float(produto.get("preco_atual") or produto.get("preco") or 0),
                produto["link_afiliado"],
                produto["plataforma"],
                produto.get("categoria", "ofertas"),
                texto_post,
                status,
                data,
                data_publicacao,
                motivo,
                "curadoria_automatica" if status == "aprovado_auto" else "",
                data if status == "aprovado_auto" else None,
                "",
                data,
            ),
        )
        return cursor.lastrowid


def listar_postagens(status=None):
    inicializar_banco()
    query = """
        SELECT postagens.*, produtos.imagem AS imagem_url, produtos.item_id AS item_id,
               produtos.preco_original, produtos.desconto_percentual, produtos.economia_valor,
               produtos.categoria_nome, produtos.categoria_caminho, produtos.origem_categoria,
               produtos.selo_mais_vendido, produtos.selo_loja_oficial, produtos.avaliacao,
               produtos.quantidade_avaliacoes, produtos.quantidade_vendida, produtos.melhor_preco,
               produtos.parcelamento, produtos.vendedor_nome, produtos.vendedor_confiavel,
               (
                   SELECT promocoes.score FROM promocoes
                   WHERE promocoes.produto_id = postagens.produto_id
                   ORDER BY promocoes.id DESC LIMIT 1
               ) AS score_curadoria
        FROM postagens
        LEFT JOIN produtos ON produtos.id = postagens.produto_id
    """
    params = []

    if status:
        query += " WHERE postagens.status = ?"
        params.append(status)

    query += " ORDER BY postagens.data_criacao ASC"

    with conectar() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def proxima_postagem_pendente():
    inicializar_banco()
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT * FROM postagens
            WHERE status IN ('aprovado_auto', 'aprovado_manual')
            ORDER BY data_criacao ASC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None


def atualizar_status_postagem(postagem_id, status, motivo="", data_publicacao=None, ator="sistema"):
    inicializar_banco()
    with conectar() as conn:
        conn.execute(
            """
            UPDATE postagens
            SET status = ?, motivo = ?, data_publicacao = COALESCE(?, data_publicacao),
                aprovado_por = CASE WHEN ? IN ('aprovado_auto', 'aprovado_manual') THEN ? ELSE aprovado_por END,
                aprovado_em = CASE WHEN ? IN ('aprovado_auto', 'aprovado_manual') THEN ? ELSE aprovado_em END,
                atualizado_em = ?
            WHERE id = ?
            """,
            (status, motivo, data_publicacao, status, ator, status, agora(), agora(), postagem_id),
        )


def status_aprovado(status):
    return str(status or "").strip() in STATUS_APROVADOS


def obter_postagem(postagem_id):
    inicializar_banco()
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT postagens.*, produtos.imagem AS imagem_url, produtos.item_id AS item_id
            FROM postagens
            LEFT JOIN produtos ON produtos.id = postagens.produto_id
            WHERE postagens.id = ?
            """,
            (postagem_id,),
        ).fetchone()
    return dict(row) if row else None


def editar_postagem_manual(postagem_id, dados, ator="painel_manual"):
    """Atualiza campos permitidos e deixa trilha de auditoria no SQLite."""
    inicializar_banco()
    status = str(dados.get("status", "")).strip()
    if status not in STATUS_CONTROLE:
        raise ValueError("Status de aprovação inválido")
    try:
        preco = float(dados.get("preco"))
    except (TypeError, ValueError) as erro:
        raise ValueError("Preço inválido") from erro
    if preco <= 0:
        raise ValueError("Preço deve ser maior que zero")

    campos = {
        "titulo": str(dados.get("titulo", "")).strip(),
        "preco": preco,
        "categoria": str(dados.get("categoria", "")).strip() or "ofertas",
        "texto_post": str(dados.get("texto_post", "")).strip(),
        "link_afiliado": str(dados.get("link_afiliado", "")).strip(),
        "imagem_url": str(dados.get("imagem_url", "")).strip(),
        "observacao_interna": str(dados.get("observacao_interna", "")).strip(),
    }
    if not campos["titulo"] or not campos["texto_post"]:
        raise ValueError("Título e texto do post são obrigatórios")

    data = agora()
    with conectar() as conn:
        existente = conn.execute("SELECT * FROM postagens WHERE id = ?", (postagem_id,)).fetchone()
        if not existente:
            raise ValueError("Oferta não encontrada")
        conn.execute(
            """
            UPDATE postagens
            SET titulo = ?, preco = ?, categoria = ?, texto_post = ?, link_afiliado = ?,
                status = ?, observacao_interna = ?, atualizado_em = ?,
                aprovado_por = CASE WHEN ? = 'aprovado_manual' THEN ? ELSE aprovado_por END,
                aprovado_em = CASE WHEN ? = 'aprovado_manual' THEN ? ELSE aprovado_em END
            WHERE id = ?
            """,
            (
                campos["titulo"], campos["preco"], campos["categoria"], campos["texto_post"],
                campos["link_afiliado"], status, campos["observacao_interna"], data,
                status, ator, status, data, postagem_id,
            ),
        )
        conn.execute(
            """
            UPDATE produtos SET titulo = ?, preco_atual = ?, link_afiliado = ?, categoria = ?,
                imagem = COALESCE(NULLIF(?, ''), imagem),
                atualizado_em = ? WHERE id = ?
            """,
            (
                campos["titulo"], campos["preco"], campos["link_afiliado"], campos["categoria"],
                campos["imagem_url"], data, existente["produto_id"],
            ),
        )

    registrar_log(
        "auditoria_painel",
        f"Oferta editada por {ator}: postagem={postagem_id} status={status}",
        dados="campos=titulo,preco,categoria,texto_post,link_afiliado,imagem_url,observacao_interna",
    )
    return obter_postagem(postagem_id)


def ultima_postagem_publicada():
    inicializar_banco()
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT * FROM postagens
            WHERE status = 'publicado'
            ORDER BY data_publicacao DESC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None


def resumo():
    inicializar_banco()
    with conectar() as conn:
        produtos = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
        promocoes = conn.execute(
            "SELECT COUNT(*) FROM promocoes WHERE status IN ('aprovado', 'aprovado_auto', 'aprovado_manual')"
        ).fetchone()[0]
        publicados = conn.execute(
            "SELECT COUNT(*) FROM postagens WHERE status = 'publicado'"
        ).fetchone()[0]
        pendentes = conn.execute(
            "SELECT COUNT(*) FROM postagens WHERE status = 'pendente_revisao'"
        ).fetchone()[0]

    return {
        "produtos": produtos,
        "promocoes_aprovadas": promocoes,
        "posts_publicados": publicados,
        "fila_pendente": pendentes,
    }


def migrar_csvs():
    inicializar_banco()

    if os.path.exists("produtos.csv"):
        with open("produtos.csv", newline="", encoding="utf-8") as arquivo:
            for row in csv.DictReader(arquivo):
                link = str(row.get("link", "")).strip()
                plataforma = "mercado_livre"
                salvar_produto({
                    "titulo": row.get("titulo", ""),
                    "preco": row.get("preco", 0),
                    "link": link,
                    "plataforma": plataforma,
                    "categoria": row.get("categoria", "ofertas"),
                    "status": "migrado_csv",
                })

    if os.path.exists("posts_prontos.csv"):
        with open("posts_prontos.csv", newline="", encoding="utf-8-sig") as arquivo:
            for row in csv.DictReader(arquivo):
                link = str(row.get("link", "")).strip()
                if not link:
                    continue

                plataforma = "mercado_livre"
                produto = {
                    "item_id": row.get("item_id", ""),
                    "titulo": row.get("titulo", ""),
                    "preco": row.get("preco", 0),
                    "link": link,
                    "link_afiliado": link,
                    "plataforma": plataforma,
                    "categoria": row.get("categoria", "ofertas"),
                    "status": "migrado_csv",
                    "imagem": row.get("imagem", ""),
                }
                _, produto_id, _ = salvar_produto(produto)

                if row.get("post"):
                    score = float(row.get("score") or 0)
                    status_csv = str(row.get("status", "")).strip()
                    status_telegram = str(row.get("status_telegram", "")).strip()
                    data_publicacao = None

                    if status_telegram == "enviado" or status_csv in ("aprovado", "publicado"):
                        status_postagem = "publicado"
                        data_publicacao = row.get("data_criacao") or agora()
                    elif status_csv == "rejeitado":
                        status_postagem = "rejeitado"
                    else:
                        status_postagem = "pendente_revisao"

                    promocao_id = salvar_promocao(
                        produto_id,
                        0,
                        score,
                        "aprovado" if status_postagem == "publicado" else status_postagem,
                        "Migrado de posts_prontos.csv",
                    )
                    criar_postagem(
                        produto_id,
                        promocao_id,
                        {
                            "titulo": row.get("titulo", ""),
                            "preco": row.get("preco", 0),
                            "link_afiliado": link,
                            "plataforma": plataforma,
                            "categoria": row.get("categoria", "ofertas"),
                        },
                        row.get("post", ""),
                        status=status_postagem,
                        data_publicacao=data_publicacao,
                        motivo="Sincronizado de posts_prontos.csv",
                    )


if __name__ == "__main__":
    inicializar_banco()
    migrar_csvs()
    print("Banco inicializado:", DB_PATH)
