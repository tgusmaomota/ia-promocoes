"""Auditoria geral segura do Promogg.

Este módulo é somente leitura sobre banco/catálogo e escreve apenas o relatório
Markdown da auditoria. Não publica, não coleta, não faz deploy e não envia Telegram.
"""

import ast
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from banco import DB_PATH
from catalogo_integridade import avaliar_catalogo, resumo_catalogo
from metricas_historico import resumo_historico_global


RELATORIO = Path("RELATORIO_AUDITORIA_GERAL_PROMOGG.md")
IGNORAR_DIRS = {"site", "dist_site", "backups", "venv", "__pycache__", ".git", ".pytest_cache"}
SENSIVEIS_PUBLICOS = {
    "token", "secret", "password", "senha", "cookie", "authorization",
    "access_token", "refresh_token", "banco", "sqlite", "observacao_interna",
}
MODULOS_LEGADOS_PROVAVEIS = {
    "agente_afiliado.py",
    "agente_curadoria.py",
    "agente_publicador.py",
    "agente_site.py",
    "agente_telegram.py",
    "app.py",
    "corrigir_posts.py",
    "gerar_token.py",
    "trocar_code.py",
    "limpar_invalidos.py",
}


def _arquivos_python():
    return sorted(
        p for p in Path(".").glob("*.py")
        if not any(parte in IGNORAR_DIRS for parte in p.parts)
    )


def _parse_python(caminho):
    texto = caminho.read_text(encoding="utf-8", errors="ignore")
    try:
        arvore = ast.parse(texto)
        erro = ""
    except SyntaxError as exc:
        arvore = ast.Module(body=[], type_ignores=[])
        erro = str(exc)
    imports = []
    funcoes = []
    classes = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            imports.append(no.module.split(".")[0])
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcoes.append(no.name)
        elif isinstance(no, ast.ClassDef):
            classes.append(no.name)
    return {
        "arquivo": str(caminho),
        "linhas": len(texto.splitlines()),
        "imports": imports,
        "funcoes": funcoes,
        "classes": classes,
        "except_exception": texto.count("except Exception"),
        "except_amplo": texto.count("except:"),
        "prints": texto.count("print("),
        "playwright": "sync_playwright" in texto or "launch_persistent_context" in texto,
        "sqlite": "sqlite3" in texto or "conectar(" in texto,
        "requests": "requests." in texto,
        "erro_parse": erro,
    }


def auditar_codigo():
    arquivos = [_parse_python(p) for p in _arquivos_python()]
    importados = Counter()
    for item in arquivos:
        importados.update(item["imports"])
    nomes_modulos = {Path(item["arquivo"]).stem for item in arquivos}
    sem_importacao = [
        item["arquivo"] for item in arquivos
        if Path(item["arquivo"]).stem not in importados
        and Path(item["arquivo"]).name not in {"ia_promocoes.py", "scheduler.py"}
    ]
    grandes = sorted(arquivos, key=lambda item: item["linhas"], reverse=True)[:8]
    riscos = {
        "except_exception": sum(item["except_exception"] for item in arquivos),
        "except_amplo": sum(item["except_amplo"] for item in arquivos),
        "prints": sum(item["prints"] for item in arquivos),
        "playwright_modulos": [item["arquivo"] for item in arquivos if item["playwright"]],
        "requests_modulos": [item["arquivo"] for item in arquivos if item["requests"]],
        "parse_erros": [item for item in arquivos if item["erro_parse"]],
    }
    candidatos = sorted(
        arquivo for arquivo in sem_importacao
        if Path(arquivo).name in MODULOS_LEGADOS_PROVAVEIS
    )
    return {
        "total_arquivos": len(arquivos),
        "total_linhas": sum(item["linhas"] for item in arquivos),
        "arquivos": arquivos,
        "maiores": grandes,
        "sem_importacao": sorted(sem_importacao),
        "candidatos_remocao": candidatos,
        "riscos": riscos,
        "modulos_nomeados": sorted(nomes_modulos),
    }


def _conectar_ro():
    caminho = Path(DB_PATH).resolve()
    conn = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def auditar_banco():
    with _conectar_ro() as conn:
        integridade = conn.execute("PRAGMA integrity_check").fetchone()[0]
        tabelas = [row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )]
        contagens = {}
        for tabela in tabelas:
            try:
                contagens[tabela] = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            except sqlite3.Error:
                contagens[tabela] = None
        duplicados_item = conn.execute(
            """
            SELECT item_id, COUNT(*) AS total
            FROM produtos
            WHERE TRIM(COALESCE(item_id, '')) <> ''
            GROUP BY item_id HAVING total > 1
            ORDER BY total DESC LIMIT 20
            """
        ).fetchall() if "produtos" in tabelas else []
        produtos_sem_historico = conn.execute(
            """
            SELECT COUNT(*) FROM produtos p
            WHERE NOT EXISTS (
                SELECT 1 FROM historico_precos h
                WHERE h.produto_id = p.id AND h.preco IS NOT NULL
            )
            """
        ).fetchone()[0] if {"produtos", "historico_precos"} <= set(tabelas) else 0
        postagens_sem_meli = conn.execute(
            """
            SELECT COUNT(*) FROM postagens
            WHERE status IN ('aprovado_auto', 'aprovado_manual', 'publicado')
              AND (link_afiliado IS NULL OR link_afiliado NOT LIKE 'https://meli.la/%')
            """
        ).fetchone()[0] if "postagens" in tabelas else 0
    return {
        "integridade": integridade,
        "tabelas": tabelas,
        "contagens": contagens,
        "duplicados_item": [dict(row) for row in duplicados_item],
        "produtos_sem_historico": produtos_sem_historico,
        "postagens_sem_meli": postagens_sem_meli,
        "historico": resumo_historico_global(),
    }


def _varrer_json_publico(pasta):
    achados = []
    for caminho in Path(pasta).glob("**/*.json"):
        try:
            texto = caminho.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        encontrados = sorted(chave for chave in SENSIVEIS_PUBLICOS if chave in texto)
        if encontrados:
            achados.append({"arquivo": str(caminho), "marcadores": encontrados[:8]})
    return achados


def auditar_catalogo_publico():
    site = resumo_catalogo("site")
    dist = resumo_catalogo("dist_site")
    protecao = avaliar_catalogo("site")
    return {
        "site": site,
        "dist_site": dist,
        "protecao": protecao,
        "json_sensiveis_site": _varrer_json_publico("site"),
        "json_sensiveis_dist": _varrer_json_publico("dist_site"),
    }


def auditar_git_seguranca():
    gitignore = Path(".gitignore").read_text(encoding="utf-8", errors="ignore") if Path(".gitignore").exists() else ""
    obrigatorios = [".env", "banco.db", "backups/", "logs/", "perfil_mercadolivre/", ".coleta_confiavel_checkpoint.json"]
    return {
        "gitignore_presente": bool(gitignore),
        "ignorados_essenciais": {item: item in gitignore for item in obrigatorios},
        "env_exemplo_tem_segredos": _env_example_tem_segredos(),
    }


def _env_example_tem_segredos():
    caminho = Path(".env.example")
    if not caminho.exists():
        return False
    for linha in caminho.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not linha or linha.strip().startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        if any(s in chave.lower() for s in ("token", "secret", "senha", "password")) and valor.strip():
            return True
    return False


def _arquitetura_resumida():
    return {
        "cli_master": "ia_promocoes.py",
        "persistencia": "banco.py + SQLite banco.db",
        "coleta": "coletor_mercadolivre_api.py -> coletor_mercadolivre.py -> coleta_confiavel.py/Playwright",
        "historico": "historico_precos + metricas_historico.py",
        "curadoria": "analisador_promocao.py + fila_postagens.py + ia_revisora.py",
        "publicacao": "gerar_site.py + catalogo_integridade.py + publicar_site_git.py",
        "engajamento": "publicador_telegram.py + whatsapp_posts.txt",
        "assistente": "promogg_assistente.py + memoria_produtos",
        "analytics": "analytics_promogg.py + servidor_analytics.py + cliques",
        "operacao": "estado_sistema.py + scheduler.py + producao_promogg.py + saude_sistema.py",
    }


def gerar_relatorio(dados):
    codigo = dados["codigo"]
    banco = dados["banco"]
    catalogo = dados["catalogo"]
    linhas = [
        "# Relatório de Auditoria Geral do Promogg",
        "",
        "## Escopo e segurança",
        "- Auditoria executada sem deploy, sem Telegram real, sem ONLINE, sem coleta real e sem limpeza de perfil.",
        "- Banco aberto em modo somente leitura durante as análises de integridade.",
        "- Checkpoints, perfil Playwright, catálogo estático, histórico e backups foram preservados.",
        "",
        "## Arquitetura encontrada",
    ]
    for nome, valor in dados["arquitetura"].items():
        linhas.append(f"- {nome}: `{valor}`")
    linhas += [
        "",
        "## Métricas do código",
        f"- Arquivos Python analisados: {codigo['total_arquivos']}",
        f"- Linhas Python analisadas: {codigo['total_linhas']}",
        f"- `except Exception`: {codigo['riscos']['except_exception']}",
        f"- `except:` amplo: {codigo['riscos']['except_amplo']}",
        f"- Módulos com Playwright: {len(codigo['riscos']['playwright_modulos'])}",
        f"- Módulos com chamadas HTTP: {len(codigo['riscos']['requests_modulos'])}",
        "",
        "### Maiores módulos",
    ]
    for item in codigo["maiores"]:
        linhas.append(f"- `{item['arquivo']}`: {item['linhas']} linhas, {len(item['funcoes'])} funções")
    linhas += [
        "",
        "## Banco SQLite e histórico",
        f"- Integridade SQLite: `{banco['integridade']}`",
        f"- Tabelas: {len(banco['tabelas'])}",
        f"- Produtos: {banco['contagens'].get('produtos', 0)}",
        f"- Postagens: {banco['contagens'].get('postagens', 0)}",
        f"- Histórico de preços: {banco['contagens'].get('historico_precos', 0)}",
        f"- Produtos sem histórico válido: {banco['produtos_sem_historico']}",
        f"- Postagens elegíveis sem meli.la: {banco['postagens_sem_meli']}",
        f"- Duplicidades por item_id: {len(banco['duplicados_item'])}",
        f"- Histórico inconclusivo/API: {banco['historico']['inconclusivos']}",
        "",
        "### Fontes de preço",
    ]
    for fonte in banco["historico"]["fontes"]:
        linhas.append(f"- {fonte['fonte']}: {fonte['total']}")
    linhas += [
        "",
        "## Catálogo público",
        f"- `site/`: {catalogo['site']['ofertas']} ofertas, {catalogo['site']['paginas']} páginas, erro=`{catalogo['site']['erro']}`",
        f"- `dist_site/`: {catalogo['dist_site']['ofertas']} ofertas, {catalogo['dist_site']['paginas']} páginas, erro=`{catalogo['dist_site']['erro']}`",
        f"- Proteção aprovada: {'sim' if catalogo['protecao']['aprovado'] else 'não'}",
    ]
    for erro in catalogo["protecao"]["erros"][:8]:
        linhas.append(f"  - Bloqueio: {erro}")
    linhas += [
        "",
        "## Segurança",
        f"- `.gitignore` presente: {'sim' if dados['seguranca']['gitignore_presente'] else 'não'}",
        f"- `.env.example` com valor sensível preenchido: {'sim' if dados['seguranca']['env_exemplo_tem_segredos'] else 'não'}",
    ]
    for item, ok in dados["seguranca"]["ignorados_essenciais"].items():
        linhas.append(f"- Ignorado no Git `{item}`: {'sim' if ok else 'não'}")
    linhas += [
        f"- JSON público com marcadores sensíveis em `site/`: {len(catalogo['json_sensiveis_site'])}",
        f"- JSON público com marcadores sensíveis em `dist_site/`: {len(catalogo['json_sensiveis_dist'])}",
        "",
        "## Problemas encontrados",
        "- `ia_promocoes.py` concentra muitas responsabilidades e comandos; recomenda-se fatiar comandos por domínio.",
        "- `gerar_site.py` é monolítico; HTML, CSS, dados e validação ficam acoplados.",
        "- Existem agentes legados CSV/Playwright paralelos ao pipeline atual, aumentando risco de uso acidental.",
        "- Muitos `except Exception` dificultam distinguir erro temporário, erro de autenticação e indisponibilidade real.",
        "- O catálogo local atual está degradado em relação à referência aprovada quando a proteção acusa queda.",
        "- Há múltiplos pontos de Playwright; o fluxo novo deve virar caminho oficial e os legados devem ser descontinuados.",
        "",
        "## Melhorias implementadas nesta auditoria",
        "- Adicionado `metricas_historico.py` para tendência, confiabilidade, origem e estatísticas reutilizáveis.",
        "- IA consultiva passou a expor origem do preço e confiabilidade sem inventar dados.",
        "- Adicionado comando `auditar-sistema` com relatório geral somente-leitura.",
        "- Auditoria de segurança verifica `.gitignore`, JSON público e marcadores sensíveis.",
        "- Auditoria consolida banco, histórico, catálogo, módulos grandes, exceções amplas e candidatos à remoção.",
        "",
        "## Arquivos candidatos à remoção ou quarentena futura",
    ]
    for arquivo in codigo["candidatos_remocao"] or ["nenhum candidato inequívoco"]:
        linhas.append(f"- `{arquivo}`")
    linhas += [
        "",
        "## Recomendações próximas",
        "- Transformar `ia_promocoes.py` em roteador fino, movendo comandos para módulos `commands/`.",
        "- Separar templates/assets do `gerar_site.py` e criar testes de contrato para `ofertas.json`.",
        "- Marcar agentes legados como deprecated antes de qualquer remoção física.",
        "- Criar tabela/evento de pipeline por execução para rastrear API -> Playwright -> histórico -> curadoria -> site -> Telegram.",
        "- Evoluir `except Exception` críticos para exceções de domínio: `ErroTemporario`, `LoginNecessario`, `IndisponibilidadeConfirmada`.",
        "- Restaurar ou proteger o catálogo público antes de qualquer produção se a validação continuar abaixo da referência.",
        "",
        "## Impacto esperado",
        "- Desempenho: auditoria evita varreduras manuais e identifica módulos grandes/gargalos sem coleta remota.",
        "- Segurança: reforça conferência de segredos, Git e JSON público antes de produção.",
        "- Manutenção: centraliza métricas de histórico e reduz duplicação conceitual entre assistente/relatórios.",
        "- Automação: cria diagnóstico único para decidir se o pipeline pode avançar ou deve pausar.",
        "",
        "## Status para commit e produção",
        "- Commit: seguro apenas revisando junto as alterações pré-existentes do workspace, que são numerosas.",
        "- Produção: não seguro enquanto o catálogo local estiver degradado ou a validação somente leitura falhar.",
        "",
    ]
    RELATORIO.write_text("\n".join(linhas), encoding="utf-8")
    return RELATORIO


def auditar_sistema():
    dados = {
        "arquitetura": _arquitetura_resumida(),
        "codigo": auditar_codigo(),
        "banco": auditar_banco(),
        "catalogo": auditar_catalogo_publico(),
        "seguranca": auditar_git_seguranca(),
    }
    relatorio = gerar_relatorio(dados)
    dados["relatorio"] = str(relatorio)
    return dados

