"""Auditoria local da camada de links afiliados, sem alterar ofertas."""

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from banco import conectar, inicializar_banco
from gerador_link_mercadolivre import link_afiliado_valido


RELATORIO = Path("RELATORIO_AUDITORIA_AFILIADOS.md")


def _tipo_link(link):
    link = str(link or "").strip()
    if not link:
        return "sem_afiliacao"
    host = (urlparse(link).hostname or "").lower()
    if host == "meli.la":
        return "meli.la_oficial"
    if link_afiliado_valido(link):
        return "mercadolivre_com_campanha"
    return "link_nao_afiliado"


def _contar_tabela(conn, tabela):
    campo = "link_afiliado"
    totais = {"meli.la_oficial": 0, "mercadolivre_com_campanha": 0, "sem_afiliacao": 0, "link_nao_afiliado": 0}
    for row in conn.execute(f"SELECT {campo} FROM {tabela}"):
        totais[_tipo_link(row[0])] += 1
    return totais


def auditar_afiliados():
    inicializar_banco()
    with conectar() as conn:
        produtos = _contar_tabela(conn, "produtos")
        postagens = _contar_tabela(conn, "postagens")
        historico = _contar_tabela(conn, "historico_precos")
        falhas_geracao = conn.execute(
            "SELECT COUNT(*) FROM logs WHERE etapa = 'afiliados' AND nivel IN ('warning', 'error')"
        ).fetchone()[0]
    validos = produtos["meli.la_oficial"] + produtos["mercadolivre_com_campanha"]
    return {
        "produtos": produtos,
        "postagens": postagens,
        "historico": historico,
        "validos_produtos": validos,
        "sem_afiliacao_produtos": produtos["sem_afiliacao"] + produtos["link_nao_afiliado"],
        "falhas_geracao": falhas_geracao,
        "usa_id_opcional": True,
        "bloqueio": (
            "Novos candidatos sem meli.la continuam sem aprovação até receberem um link afiliado válido."
            if produtos["sem_afiliacao"] or produtos["link_nao_afiliado"] else
            "Nenhum bloqueio de afiliação encontrado."
        ),
    }


def gerar_relatorio(dados):
    linhas = [
        "# Relatório de Auditoria de Afiliados - Promogg",
        "",
        f"- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- MERCADO_LIVRE_AFFILIATE_ID não é necessário para links oficiais https://meli.la/...",
        "- A variável permanece opcional apenas para o método legado de acrescentar campanha a um permalink comum.",
        "",
        "## Uso no código",
        "- gerador_link_mercadolivre.py aceita meli.la diretamente e só usa MERCADO_LIVRE_AFFILIATE_ID para permalink mercadolivre.com.",
        "- fila_postagens.py, gerar_site.py e publicador_telegram.py exigem link válido, não exigem a variável diretamente.",
        "- recuperacao_base.py não bloqueia mais a reconstrução pela ausência da variável.",
        "- agente_ofertas.py passa a preferir meli.la quando esse link existir no card.",
        "",
        "## Contagens",
    ]
    for nome in ("produtos", "postagens", "historico"):
        totais = dados[nome]
        linhas.append(
            f"- {nome}: meli.la={totais['meli.la_oficial']}; campanha={totais['mercadolivre_com_campanha']}; "
            f"sem afiliação={totais['sem_afiliacao']}; inválido={totais['link_nao_afiliado']}"
        )
    linhas += [
        "",
        "## Impacto",
        "- Coleta: links meli.la encontrados são preservados como afiliados.",
        "- Curadoria: só candidatos sem link válido permanecem fora da aprovação/publicação.",
        "- Site: ofertas com meli.la válido continuam publicáveis; dados internos não são expostos.",
        f"- Falhas históricas na geração oficial: {dados['falhas_geracao']}.",
        f"- Motivo de bloqueio atual: {dados['bloqueio']}",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return RELATORIO


def imprimir_diagnostico():
    dados = auditar_afiliados()
    print("Diagnóstico de afiliados")
    print(f"Links afiliados válidos em produtos: {dados['validos_produtos']}")
    print(f"Produtos sem link afiliado válido: {dados['sem_afiliacao_produtos']}")
    print(f"Falhas registradas ao gerar: {dados['falhas_geracao']}")
    for nome in ("produtos", "postagens", "historico"):
        totais = dados[nome]
        print(f"{nome}: meli.la={totais['meli.la_oficial']} campanha={totais['mercadolivre_com_campanha']} sem_afiliacao={totais['sem_afiliacao']} inválido={totais['link_nao_afiliado']}")
    print(f"Motivo de bloqueio: {dados['bloqueio']}")
    gerar_relatorio(dados)
    print(f"Relatório: {RELATORIO}")
    return dados
