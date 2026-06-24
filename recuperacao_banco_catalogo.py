"""Recupera a elegibilidade do SQLite a partir do catálogo estático já validado.

Este fluxo não consulta a rede, não publica e não altera ``dist_site``.  A fonte
de verdade é o contrato público restaurado, não uma falha transitória do monitor.
"""

import json
import re
import shutil
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from banco import DB_PATH, conectar, inicializar_banco, registrar_evento_sistema, registrar_log
from catalogo_integridade import avaliar_catalogo, gerar_catalogo_protegido, resumo_catalogo
from gerador_link_mercadolivre import link_afiliado_valido
from mercadolivre_api import item_id_valido


RELATORIO = Path("RELATORIO_RECUPERACAO_BANCO_CATALOGO.md")
BACKUPS = Path("backups") / "recuperacao_banco_catalogo"
FONTES = (Path("site/ofertas.json"), Path("dist_site/ofertas.json"))
ARTEFATOS = (Path("site"), Path("dist_site"), Path("posts_prontos.csv"), Path("whatsapp_posts.txt"))
STATUS_PUBLICOS = ("aprovado_auto", "aprovado_manual", "publicado")
# "item não encontrado" legado, isoladamente, não é uma prova verificável de
# 404: o catálogo restaurado pode demonstrar justamente que aquela conclusão foi
# transitória. Só bloqueamos marcadores inequívocos de encerramento/pausa.
MARCADORES_FINALIZADO = ("404", "finalizado", "finalizada", "paused", "pausado", "closed", "encerrado")


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _imagem_valida(valor):
    partes = urlparse(str(valor or "").strip())
    return partes.scheme in {"http", "https"} and bool(partes.netloc)


def _preco_valido(valor):
    try:
        return float(valor) > 0
    except (TypeError, ValueError):
        return False


def _titulo_limpo(valor):
    titulo = " ".join(str(valor or "").split())
    return bool(titulo) and not re.search(r"(?i)(?:R\$\s*\d|\d+\s*%\s*OFF)", titulo)


def _catalogo_restaurado():
    """Une fontes públicas iguais/compatíveis, mantendo somente ofertas completas."""
    ofertas = {}
    fontes_lidas = []
    for origem in FONTES:
        try:
            dados = json.loads(origem.read_text(encoding="utf-8"))
            lista = dados.get("ofertas", [])
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(lista, list):
            continue
        fontes_lidas.append(str(origem))
        for oferta in lista:
            item_id = str(oferta.get("item_id") or "").strip().upper()
            produto_url = str(oferta.get("produto_url") or "").strip().strip("/")
            pagina = origem.parent / produto_url / "index.html"
            if item_id and pagina.is_file():
                ofertas.setdefault(item_id, {**oferta, "_fonte": str(origem), "_pagina": str(pagina)})
    return ofertas, fontes_lidas


def _motivo_confirmado(produto, logs):
    texto = " ".join((str(produto.get("motivo_indisponivel") or ""), logs.get(produto["id"], ""))).lower()
    return any(marcador in texto for marcador in MARCADORES_FINALIZADO)


def _dados_banco():
    inicializar_banco()
    with conectar() as conn:
        produtos = [dict(row) for row in conn.execute("SELECT * FROM produtos WHERE plataforma='mercado_livre'")]
        postagens = [dict(row) for row in conn.execute("SELECT * FROM postagens WHERE plataforma='mercado_livre'")]
        # Logs são somente evidência complementar; nunca são expostos no relatório.
        logs = {}
        for row in conn.execute("SELECT dados, mensagem FROM logs WHERE lower(mensagem || ' ' || coalesce(dados, '')) LIKE '%finaliz%' OR lower(mensagem || ' ' || coalesce(dados, '')) LIKE '%404%' OR lower(mensagem || ' ' || coalesce(dados, '')) LIKE '%pausad%'"):
            texto = f"{row['mensagem']} {row['dados'] or ''}".lower()
            for produto in produtos:
                if produto.get("item_id") and str(produto["item_id"]).lower() in texto:
                    logs[produto["id"]] = texto
    por_produto = {}
    for postagem in postagens:
        por_produto.setdefault(postagem["produto_id"], []).append(postagem)
    return produtos, por_produto, logs


def _postagem_preferida(postagens):
    prioridade = {"publicado": 3, "aprovado_manual": 2, "aprovado_auto": 1}
    return sorted(postagens or [], key=lambda x: (prioridade.get(x.get("status"), 0), x.get("id", 0)), reverse=True)[0] if postagens else None


def analisar_recuperacao():
    catalogo, fontes = _catalogo_restaurado()
    produtos, por_produto, logs = _dados_banco()
    por_item = {}
    for produto in produtos:
        por_item.setdefault(str(produto.get("item_id") or "").strip().upper(), []).append(produto)

    itens = []
    for item_id, oferta in catalogo.items():
        candidatos = por_item.get(item_id, [])
        produto = max(candidatos, key=lambda p: (len(por_produto.get(p["id"], [])), p["id"]), default=None)
        postagem = _postagem_preferida(por_produto.get(produto["id"], [])) if produto else None
        motivo = ""
        seguro = False
        if not produto:
            motivo = "item do catálogo não existe no banco"
        elif not item_id_valido(item_id):
            motivo = "item_id inválido"
        elif _motivo_confirmado(produto, logs):
            motivo = "evidência registrada de anúncio finalizado/404/pausado"
        elif not link_afiliado_valido(oferta.get("link")):
            motivo = "catálogo sem link meli.la válido"
        elif not _preco_valido(oferta.get("preco")):
            motivo = "catálogo sem preço válido"
        elif not _imagem_valida(oferta.get("imagem_url")):
            motivo = "catálogo sem imagem válida"
        elif not _titulo_limpo(oferta.get("titulo")):
            motivo = "catálogo com título inválido"
        elif not postagem:
            motivo = "produto sem postagem no banco"
        else:
            seguro = True
            motivo = "evidência completa no catálogo restaurado"
        itens.append({"item_id": item_id, "oferta": oferta, "produto": produto, "postagem": postagem, "seguro": seguro, "motivo": motivo})

    correspondentes = [item for item in itens if item["produto"]]
    status_produto = Counter(item["produto"]["status"] for item in correspondentes)
    status_postagem = Counter(item["postagem"]["status"] for item in correspondentes if item["postagem"])
    metricas = {
        "catalogo_restaurado": len(catalogo), "catalogo_no_banco": len(correspondentes),
        "indisponivel": status_produto["indisponivel"],
        "aprovado_auto": status_postagem["aprovado_auto"], "aprovado_manual": status_postagem["aprovado_manual"],
        "publicado": status_postagem["publicado"],
        "meli_la": sum(link_afiliado_valido(x["oferta"].get("link")) for x in itens),
        "preco_valido": sum(_preco_valido(x["oferta"].get("preco")) for x in itens),
        "recuperaveis": sum(x["seguro"] for x in itens), "pendentes": sum(not x["seguro"] for x in itens),
    }
    return {"itens": itens, "metricas": metricas, "fontes": fontes}


def criar_backup_recuperacao():
    """Snapshot local consistente de banco e artefatos restaurados, sem segredos."""
    destino = BACKUPS / datetime.now().strftime("%Y%m%d_%H%M%S")
    destino.mkdir(parents=True, exist_ok=False)
    origem = sqlite3.connect(DB_PATH)
    copia = sqlite3.connect(destino / "banco.db")
    try:
        origem.backup(copia)
    finally:
        copia.close(); origem.close()
    for artefato in ARTEFATOS:
        if artefato.is_dir():
            shutil.copytree(artefato, destino / artefato.name)
        elif artefato.is_file():
            shutil.copy2(artefato, destino / artefato.name)
    return destino


def _contagens_banco():
    with conectar() as conn:
        return {
            "produtos_indisponiveis": conn.execute("SELECT COUNT(*) FROM produtos WHERE status='indisponivel'").fetchone()[0],
            "postagens_aprovadas": conn.execute("SELECT COUNT(*) FROM postagens WHERE status IN ('aprovado_auto','aprovado_manual','publicado')").fetchone()[0],
            "historico_precos": conn.execute("SELECT COUNT(*) FROM historico_precos").fetchone()[0],
        }


def _aplicar(itens):
    atualizacao = _agora()
    recuperados = 0
    pendentes = 0
    with conectar() as conn:
        for item in itens:
            produto, postagem, oferta = item["produto"], item["postagem"], item["oferta"]
            if not produto:
                continue
            if not item["seguro"]:
                if produto["status"] == "indisponivel" and not _motivo_confirmado(produto, {}):
                    conn.execute("UPDATE produtos SET status='pendente_revisao', atualizado_em=? WHERE id=?", (atualizacao, produto["id"]))
                    pendentes += 1
                continue
            status_post = postagem["status"] if postagem["status"] in STATUS_PUBLICOS else "aprovado_auto"
            # Mantemos motivo/data anteriores para auditoria: a recuperação é
            # uma nova observação, não uma reescrita da evidência histórica.
            conn.execute("""UPDATE produtos SET status='coletado', preco_atual=?, link_afiliado=?, imagem=?, titulo=?,
                         status_verificacao='recuperacao_catalogo_estatico', atualizado_em=? WHERE id=?""",
                         (float(oferta["preco"]), oferta["link"], oferta["imagem_url"], oferta["titulo"], atualizacao, produto["id"]))
            conn.execute("""UPDATE postagens SET status=?, titulo=?, preco=?, link_afiliado=?, categoria=?,
                         motivo=COALESCE(motivo, ''), atualizado_em=? WHERE id=?""",
                         (status_post, oferta["titulo"], float(oferta["preco"]), oferta["link"], oferta.get("categoria") or "ofertas", atualizacao, postagem["id"]))
            conn.execute("""INSERT INTO historico_precos (produto_id,item_id,titulo,plataforma,preco,data_verificacao,link_afiliado,categoria_id,categoria_nome,status_verificacao,fonte_preco)
                         VALUES (?, ?, ?, 'mercado_livre', ?, ?, ?, ?, ?, 'recuperacao_catalogo_estatico', 'recuperacao_catalogo_estatico')""",
                         (produto["id"], item["item_id"], oferta["titulo"], float(oferta["preco"]), atualizacao, oferta["link"], produto.get("categoria_id"), oferta.get("categoria") or "ofertas"))
            recuperados += 1
    return recuperados, pendentes


def _relatorio(resultado):
    m = resultado["analise"]["metricas"]
    antes, depois = resultado["antes"], resultado["depois"]
    integridade = resultado.get("integridade", {})
    linhas = [
        "# Relatório de Recuperação do Banco a partir do Catálogo", "",
        f"- Gerado em: {_agora()}", f"- Modo: {'dry-run' if resultado['dry_run'] else 'execução real'}",
        f"- Fontes: {', '.join(resultado['analise']['fontes']) or 'nenhuma'}", f"- Backup: {resultado.get('backup') or 'não aplicável'}", "",
        "## Total analisado", f"- Catálogo restaurado: {m['catalogo_restaurado']}", f"- Itens do catálogo existentes no banco: {m['catalogo_no_banco']}", f"- Produtos indisponíveis: {m['indisponivel']}",
        f"- Postagens aprovado_auto/manual/publicado: {m['aprovado_auto']}/{m['aprovado_manual']}/{m['publicado']}", f"- Com meli.la válido: {m['meli_la']}", f"- Com preço válido: {m['preco_valido']}", f"- Recuperáveis com segurança: {m['recuperaveis']}", f"- Precisam permanecer pendentes/não elegíveis: {m['pendentes']}", "",
        "## Resultado da recuperação", f"- Recuperados nesta execução: {resultado.get('recuperados', 0)}", f"- Movidos para pendente_revisao nesta execução: {resultado.get('pendentes_alterados', 0)}", f"- Mantidos indisponíveis entre os itens analisados: {resultado.get('mantidos_indisponiveis', 0)}", "- Motivos pendentes/não elegíveis: " + ("; ".join(sorted({x['motivo'] for x in resultado['analise']['itens'] if not x['seguro']})) or "nenhum"), "",
        "## Banco antes/depois", f"- Produtos indisponíveis: {antes['produtos_indisponiveis']} -> {depois['produtos_indisponiveis']}", f"- Postagens elegíveis: {antes['postagens_aprovadas']} -> {depois['postagens_aprovadas']}", f"- Histórico de preços (preservado e acrescido): {antes['historico_precos']} -> {depois['historico_precos']}", "",
        "## Catálogo gerado após recuperação", f"- Ofertas: {integridade.get('atual', {}).get('ofertas', resumo_catalogo(Path('site'))['ofertas'])}", f"- Páginas: {integridade.get('atual', {}).get('paginas', resumo_catalogo(Path('site'))['paginas'])}", f"- Queda: {integridade.get('queda_percentual', 0):.2f}%", f"- Protegido/abortado: {'sim' if resultado.get('protegido') else 'não'}", f"- Bloqueios: {'; '.join(integridade.get('erros', [])) or 'nenhum'}", "",
        "## Motivos", "- Recuperação somente para itens do catálogo estático com página, meli.la, preço, imagem e título válidos, sem evidência local de finalização.", "- Itens incertos são mantidos/convertidos para pendente_revisao; nenhum item fora do catálogo foi promovido.", "- Não houve coleta, monitoramento, Telegram, ONLINE, deploy ou alteração de dist_site.",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def recuperar_banco_catalogo(dry_run=False):
    analise = analisar_recuperacao()
    antes = _contagens_banco()
    resultado = {"dry_run": dry_run, "analise": analise, "antes": antes, "depois": antes, "backup": "", "recuperados": 0, "pendentes_alterados": 0, "protegido": False, "integridade": avaliar_catalogo(Path("site"), referencia=resumo_catalogo(Path("site")))}
    if dry_run:
        _relatorio(resultado)
        return resultado
    backup = criar_backup_recuperacao()
    resultado["backup"] = str(backup)
    recuperados, pendentes = _aplicar(analise["itens"])
    resultado["recuperados"], resultado["pendentes_alterados"] = recuperados, pendentes
    resultado["depois"] = _contagens_banco()
    resultado["mantidos_indisponiveis"] = sum(
        item["produto"] is not None and item["produto"].get("status") == "indisponivel"
        for item in analisar_recuperacao()["itens"]
    )
    from gerar_site import gerar_site, validar_site_publico
    protegido = gerar_catalogo_protegido(gerar_site)
    resultado["protegido"] = protegido["protegido"]
    resultado["integridade"] = protegido["integridade"]
    if not protegido["protegido"]:
        erros = validar_site_publico(escrever_relatorio=False)
        from qualidade_catalogo import auditar_qualidade_catalogo
        qualidade = auditar_qualidade_catalogo()
        if erros or qualidade["indicador"] == "REPROVADO":
            resultado["integridade"]["erros"] += erros + (["auditoria de qualidade reprovada"] if qualidade["indicador"] == "REPROVADO" else [])
    registrar_log("recuperacao_catalogo_estatico", f"Recuperação concluída: recuperados={recuperados} pendentes={pendentes}", dados="fonte=site/ofertas.json,dist_site/ofertas.json")
    registrar_evento_sistema("recuperacao_catalogo_estatico", "operacao", "sucesso" if not resultado["integridade"]["erros"] else "erro", "Recuperação do banco pelo catálogo estático concluída", f"recuperados={recuperados}; backup={backup.name}")
    _relatorio(resultado)
    return resultado
