"""Proteções de disponibilidade para o catálogo estático do Promogg."""

import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


SITE_DIR = Path("site")
DIST_DIR = Path("dist_site")
ESTADO_APROVADO = Path("backups") / "ultimo_catalogo_aprovado.json"


def minimo_catalogo():
    try:
        return max(1, int(os.getenv("PROMOGG_CATALOGO_MINIMO", "30")))
    except ValueError:
        return 30


def limite_queda_percentual():
    try:
        return min(100, max(0, float(os.getenv("PROMOGG_LIMITE_QUEDA_CATALOGO", "20"))))
    except ValueError:
        return 20.0


def resumo_catalogo(diretorio=SITE_DIR):
    """Lê somente dados públicos, sem regenerar nem alterar arquivos."""
    diretorio = Path(diretorio)
    caminho_ofertas = diretorio / "ofertas.json"
    resultado = {
        "diretorio": str(diretorio), "ofertas": 0, "paginas": 0,
        "links_invalidos": 0, "paginas_ausentes": 0, "erro": "",
    }
    try:
        dados = json.loads(caminho_ofertas.read_text(encoding="utf-8"))
        ofertas = dados.get("ofertas", [])
        if not isinstance(ofertas, list):
            raise ValueError("ofertas não é uma lista")
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        resultado["erro"] = f"ofertas.json indisponível ou inválido: {erro}"
        return resultado

    resultado["ofertas"] = len(ofertas)
    for oferta in ofertas:
        link = str(oferta.get("link") or "").strip().lower()
        if not link.startswith("https://meli.la/"):
            resultado["links_invalidos"] += 1
        produto_url = str(oferta.get("produto_url") or "").strip().strip("/")
        if not produto_url or not (diretorio / produto_url / "index.html").is_file():
            resultado["paginas_ausentes"] += 1

    produto_dir = diretorio / "produto"
    resultado["paginas"] = len(list(produto_dir.glob("*/*/index.html"))) if produto_dir.exists() else 0
    return resultado


def carregar_referencia_aprovada():
    """Prioriza o último deploy confirmado; usa dist_site como fallback local."""
    try:
        dados = json.loads(ESTADO_APROVADO.read_text(encoding="utf-8"))
        if int(dados.get("ofertas", 0)) > 0:
            return {"origem": str(ESTADO_APROVADO), **dados}
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    resumo = resumo_catalogo(DIST_DIR)
    return {"origem": str(DIST_DIR), **resumo}


def avaliar_catalogo(candidato=SITE_DIR, referencia=None):
    """Bloqueia catálogo incompleto ou queda brusca em relação à referência."""
    atual = resumo_catalogo(candidato)
    referencia = referencia or carregar_referencia_aprovada()
    erros = []
    minimo = minimo_catalogo()
    limite = limite_queda_percentual()

    if atual["erro"]:
        erros.append(atual["erro"])
    if atual["ofertas"] < minimo:
        erros.append(f"catálogo possui {atual['ofertas']} ofertas; mínimo configurado é {minimo}")
    if atual["paginas"] != atual["ofertas"] or atual["paginas_ausentes"]:
        erros.append(
            f"páginas inconsistentes: ofertas={atual['ofertas']} páginas={atual['paginas']} ausentes={atual['paginas_ausentes']}"
        )
    if atual["links_invalidos"]:
        erros.append(f"{atual['links_invalidos']} link(s) público(s) sem meli.la válido")

    referencia_ofertas = int(referencia.get("ofertas") or 0)
    if referencia_ofertas >= minimo and atual["ofertas"] < referencia_ofertas:
        queda = round((1 - atual["ofertas"] / referencia_ofertas) * 100, 2)
        if queda > limite:
            erros.append(
                f"queda de catálogo de {queda:.2f}% em relação a {referencia.get('origem', 'referência')} "
                f"({referencia_ofertas} -> {atual['ofertas']}); limite é {limite:.0f}%"
            )
    else:
        queda = 0.0

    return {
        "aprovado": not erros,
        "erros": erros,
        "atual": atual,
        "referencia": referencia,
        "queda_percentual": queda,
        "minimo": minimo,
    }


def registrar_catalogo_aprovado(diretorio=SITE_DIR):
    """Guarda somente métricas públicas após um deploy bem-sucedido."""
    resumo = resumo_catalogo(diretorio)
    if resumo["erro"] or resumo["ofertas"] < minimo_catalogo():
        return None
    ESTADO_APROVADO.parent.mkdir(parents=True, exist_ok=True)
    dados = {**resumo, "aprovado_em": datetime.now().isoformat(timespec="seconds")}
    ESTADO_APROVADO.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dados


def validar_catalogo_estatico(diretorio=SITE_DIR):
    """Validação somente leitura do contrato público, sem consultar o SQLite."""
    diretorio = Path(diretorio)
    resumo = resumo_catalogo(diretorio)
    erros = list(avaliar_catalogo(diretorio, referencia=resumo).get("erros", []))
    if resumo["erro"]:
        return erros
    try:
        ofertas = json.loads((diretorio / "ofertas.json").read_text(encoding="utf-8")).get("ofertas", [])
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        return erros + [f"ofertas.json inválido: {erro}"]

    campos_sensiveis = {"status", "observacao_interna", "token", "cookie", "env", "banco", "sqlite"}
    for indice, oferta in enumerate(ofertas, start=1):
        if campos_sensiveis & set(oferta):
            erros.append(f"oferta {indice}: campo interno exposto")
        try:
            if float(oferta.get("preco")) <= 0:
                erros.append(f"oferta {indice}: preço inválido")
        except (TypeError, ValueError):
            erros.append(f"oferta {indice}: preço inválido")
        if re.search(r"(?i)(?:R\$\s*\d|\d+\s*%\s*OFF)", str(oferta.get("titulo") or "")):
            erros.append(f"oferta {indice}: título contém preço ou desconto")
        imagem = str(oferta.get("imagem_url") or "")
        if not imagem.startswith(("https://", "http://")):
            erros.append(f"oferta {indice}: imagem pública inválida")
        pagina = diretorio / str(oferta.get("produto_url") or "") / "index.html"
        if not pagina.is_file():
            continue
        conteudo = pagina.read_text(encoding="utf-8").lower()
        if any(marcador in conteudo for marcador in ("observacao_interna", "aprovado_auto", "aprovado_manual", "pendente_revisao", "rejeitado")):
            erros.append(f"oferta {indice}: página expõe dado interno")
    return erros


def gerar_catalogo_protegido(gerador):
    """Executa uma geração, mas restaura o site se o candidato piorar a base."""
    with tempfile.TemporaryDirectory(prefix="promogg_geracao_segura_") as temporario:
        copia = Path(temporario) / "site"
        if SITE_DIR.exists():
            shutil.copytree(SITE_DIR, copia)
        referencia = resumo_catalogo(copia) if copia.exists() else resumo_catalogo(SITE_DIR)
        resultado_geracao = gerador()
        integridade = avaliar_catalogo(SITE_DIR, referencia=referencia)
        if integridade["aprovado"]:
            return {"protegido": False, "geracao": resultado_geracao, "integridade": integridade}
        if copia.exists():
            if SITE_DIR.exists():
                shutil.rmtree(SITE_DIR)
            shutil.copytree(copia, SITE_DIR)
        return {"protegido": True, "geracao": resultado_geracao, "integridade": integridade}
