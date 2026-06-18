import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from difflib import SequenceMatcher


DB_PATH = "banco.db"
PLATAFORMAS = ["mercado_livre"]


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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

        for plataforma in PLATAFORMAS:
            conn.execute(
                """
                INSERT OR IGNORE INTO plataformas (nome, ativo, criado_em)
                VALUES (?, 1, ?)
                """,
                (plataforma, agora()),
            )


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
    item_id = str(produto.get("item_id", "")).strip()
    titulo = str(produto.get("titulo", "")).strip()
    plataforma = str(produto.get("plataforma", "mercado_livre")).strip()

    with conectar() as conn:
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

        rows = conn.execute(
            "SELECT * FROM produtos WHERE plataforma = ?",
            (plataforma,),
        ).fetchall()
        for row in rows:
            if titulo_muito_parecido(titulo, row["titulo"]):
                return row, "titulo_muito_parecido"

    return None, ""


def salvar_produto(produto):
    inicializar_banco()
    duplicado, motivo = buscar_duplicado(produto)

    if duplicado:
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
                imagem, criado_em, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        produto_id = cursor.lastrowid

    registrar_log("coleta", f"Produto salvo: {produto.get('titulo', '')}")
    return True, produto_id, ""


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
        "pendente": 1,
        "aprovado": 2,
        "publicado": 3,
    }
    return prioridades.get(status, 1)


def criar_postagem(
    produto_id,
    promocao_id,
    produto,
    texto_post,
    status="pendente",
    data_publicacao=None,
    motivo="",
):
    inicializar_banco()
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
                        motivo = COALESCE(NULLIF(?, ''), motivo)
                    WHERE id = ?
                    """,
                    (status, data_publicacao, motivo, existente["id"]),
                )

            return existente["id"]

        cursor = conn.execute(
            """
            INSERT INTO postagens (
                produto_id, promocao_id, titulo, preco, link_afiliado, plataforma,
                categoria, texto_post, status, data_criacao, data_publicacao, motivo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                agora(),
                data_publicacao,
                motivo,
            ),
        )
        return cursor.lastrowid


def listar_postagens(status=None):
    inicializar_banco()
    query = "SELECT * FROM postagens"
    params = []

    if status:
        query += " WHERE status = ?"
        params.append(status)

    query += " ORDER BY data_criacao ASC"

    with conectar() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def proxima_postagem_pendente():
    inicializar_banco()
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT * FROM postagens
            WHERE status = 'pendente'
            ORDER BY data_criacao ASC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None


def atualizar_status_postagem(postagem_id, status, motivo="", data_publicacao=None):
    inicializar_banco()
    with conectar() as conn:
        conn.execute(
            """
            UPDATE postagens
            SET status = ?, motivo = ?, data_publicacao = COALESCE(?, data_publicacao)
            WHERE id = ?
            """,
            (status, motivo, data_publicacao, postagem_id),
        )


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
            "SELECT COUNT(*) FROM promocoes WHERE status = 'aprovado'"
        ).fetchone()[0]
        publicados = conn.execute(
            "SELECT COUNT(*) FROM postagens WHERE status = 'publicado'"
        ).fetchone()[0]
        pendentes = conn.execute(
            "SELECT COUNT(*) FROM postagens WHERE status = 'pendente'"
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

                    if status_telegram == "enviado" or status_csv == "aprovado":
                        status_postagem = "publicado"
                        data_publicacao = row.get("data_criacao") or agora()
                    elif status_csv == "rejeitado":
                        status_postagem = "rejeitado"
                    else:
                        status_postagem = "pendente"

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
