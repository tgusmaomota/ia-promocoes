import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from banco import conectar, inicializar_banco, migrar_csvs, registrar_evento_sistema, registrar_log, resumo
from deploy_site import copiar_site
from gerar_site import gerar_site, validar_site_publico
from servidor_site import servir_site


PID_FILE = Path(".ia_promocoes.pid")
STOP_FILE = Path(".ia_promocoes.stop")
STATE_FILE = Path(".ia_promocoes.producao.json")
PRODUCAO_LOG = Path("logs") / "producao.log"
ANALYTICS_PID_FILE = Path(".promogg_analytics.pid")
PAINEL_PID_FILE = Path(".promogg_painel.pid")


load_dotenv()


def processo_ativo(pid):
    try:
        os.kill(pid, 0)
        estado = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        return bool(estado) and "Z" not in estado
    except OSError:
        return False


def pid_atual():
    if not PID_FILE.exists():
        return None

    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def robo_rodando():
    pid = pid_atual()
    return pid if pid and processo_ativo(pid) else None


def _pid_servico(arquivo):
    try:
        pid = int(arquivo.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return pid if processo_ativo(pid) else None


def _executavel_projeto():
    return str(Path("venv/bin/python")) if Path("venv/bin/python").exists() else sys.executable


def _iniciar_servico(nome, pid_file, log_nome, argumentos):
    pid = _pid_servico(pid_file)
    if pid:
        return pid, False
    Path("logs").mkdir(exist_ok=True)
    with (Path("logs") / log_nome).open("a", encoding="utf-8") as log:
        processo = subprocess.Popen(
            [_executavel_projeto(), *argumentos], cwd=Path.cwd(), stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    pid_file.write_text(str(processo.pid), encoding="utf-8")
    registrar_evento_sistema("servico", "master", "sucesso", f"Serviço iniciado: {nome}", f"pid={processo.pid}")
    return processo.pid, True


def _parar_servico(nome, pid_file):
    pid = _pid_servico(pid_file)
    if not pid:
        pid_file.unlink(missing_ok=True)
        return False
    try:
        os.kill(pid, 15)
    except OSError:
        pass
    pid_file.unlink(missing_ok=True)
    registrar_evento_sistema("servico", "master", "sucesso", f"Serviço parado: {nome}", f"pid={pid}")
    return True


def preparar_base(migrar=False):
    inicializar_banco()
    if migrar:
        migrar_csvs()


def esperar_com_parada(segundos):
    fim = time.time() + segundos
    while time.time() < fim:
        if STOP_FILE.exists():
            return False
        time.sleep(min(10, max(1, fim - time.time())))
    return True


def _salvar_estado_producao(**dados):
    estado = {"atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **dados}
    STATE_FILE.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def estado_producao():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _executar_worker_producao():
    from publicador_telegram import gerar_site_local, gerar_whatsapp_manual
    from scheduler import ciclo_completo, inteiro_env
    from saude_sistema import obter_relatorio_saude

    pid = robo_rodando()
    if pid and pid != os.getpid():
        print(f"IA-Promocoes já está rodando. PID: {pid}")
        return 0

    print("Centro de controle: python3 ia_promocoes.py painel")
    print("Use o painel para aprovar, rejeitar, editar e publicar ofertas.")

    STOP_FILE.unlink(missing_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    intervalo = inteiro_env("INTERVALO_COLETA_MINUTOS", 30)
    _salvar_estado_producao(pid=os.getpid(), iniciado_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), intervalo_minutos=intervalo, status="rodando")

    registrar_log(
        "operacao",
        f"Robô iniciado em modo Mercado Livre. intervalo_coleta={intervalo}min",
    )

    try:
        while not STOP_FILE.exists():
            try:
                ciclo_completo(publicar=True)
                gerar_site_local()
                gerar_whatsapp_manual()
                copiar_site("dist_site")
                registrar_log("site", "Site público preparado automaticamente em dist_site/")
                saude = obter_relatorio_saude()
                registrar_evento_sistema("saude", "producao", "sucesso", "Verificação de saúde concluída", f"status={saude['status_geral']}")
                _salvar_estado_producao(pid=os.getpid(), iniciado_em=estado_producao().get("iniciado_em"), intervalo_minutos=intervalo, status="rodando", ultimo_ciclo=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as erro:
                registrar_log("operacao", f"Erro no ciclo automático: {erro}", nivel="error")
                registrar_evento_sistema("producao", "scheduler", "erro", "Falha no ciclo de produção", str(erro))

            if not esperar_com_parada(intervalo * 60):
                break
    finally:
        registrar_log("operacao", "Robô parado com segurança")
        registrar_evento_sistema("producao", "scheduler", "sucesso", "Serviço de produção parado")
        PID_FILE.unlink(missing_ok=True)
        STOP_FILE.unlink(missing_ok=True)
        _salvar_estado_producao(status="parado", encerrado_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return 0


def _iniciar_servico_producao():
    pid = robo_rodando()
    if pid:
        print(f"IA-Promocoes já está rodando. PID: {pid}")
        return 0
    STOP_FILE.unlink(missing_ok=True)
    PRODUCAO_LOG.parent.mkdir(exist_ok=True)
    executavel = Path("venv/bin/python") if Path("venv/bin/python").exists() else Path(sys.executable)
    with PRODUCAO_LOG.open("a", encoding="utf-8") as log:
        processo = subprocess.Popen(
            [str(executavel), __file__, "_worker-producao"],
            cwd=Path.cwd(),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PID_FILE.write_text(str(processo.pid), encoding="utf-8")
    _salvar_estado_producao(pid=processo.pid, iniciado_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status="iniciando")
    print(f"Serviço de produção iniciado. PID: {processo.pid}")
    print("Painel permanece disponível: python3 ia_promocoes.py painel")
    return 0


def comando_iniciar():
    return _iniciar_servico_producao()


def comando_producao():
    return _iniciar_servico_producao()


def comando_parar():
    pid = robo_rodando()
    STOP_FILE.write_text("parar\n", encoding="utf-8")

    if pid:
        print(f"Solicitação de parada enviada. PID: {pid}")
        print("O robô vai encerrar com segurança ao final do passo atual.")
    else:
        PID_FILE.unlink(missing_ok=True)
        print("Robô não estava rodando. Flag de parada registrada/limpa.")

    return 0


def comando_reiniciar():
    pid = robo_rodando()
    if pid:
        comando_parar()
        limite = time.time() + 35
        while robo_rodando() and time.time() < limite:
            time.sleep(1)
        if robo_rodando():
            print("O serviço ainda está finalizando; reinício cancelado para evitar múltiplas instâncias.")
            return 1
    return _iniciar_servico_producao()


def buscar_uma_coluna(query, params=()):
    with conectar() as conn:
        row = conn.execute(query, params).fetchone()
        return row[0] if row else None


def logs_recentes(nivel=None, limite=5):
    query = "SELECT etapa, nivel, mensagem, criado_em FROM logs"
    filtros = ["lower(etapa) NOT LIKE '%shopee%'", "lower(mensagem) NOT LIKE '%shopee%'"]
    params = []

    if nivel:
        filtros.append("nivel = ?")
        params.append(nivel)

    query += " WHERE " + " AND ".join(filtros)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limite)

    with conectar() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def resumir_mensagem(mensagem, limite=220):
    mensagem = str(mensagem or "").replace("\n", " ").strip()
    return mensagem if len(mensagem) <= limite else mensagem[:limite - 3] + "..."


def imprimir_status():
    from estado_sistema import obter_estado_sistema
    from coletor_mercadolivre_api import busca_api_bloqueada
    from banco import obter_saude_coleta_api
    from meli_oauth import status_oauth_local

    preparar_base()
    pid = robo_rodando()
    dados = resumo()
    hoje = date.today().strftime("%Y-%m-%d")

    publicados_hoje = buscar_uma_coluna(
        """
        SELECT COUNT(*)
        FROM postagens
        WHERE status = 'publicado'
          AND substr(COALESCE(data_publicacao, ''), 1, 10) = ?
        """,
        (hoje,),
    )
    ultima_coleta = buscar_uma_coluna(
        "SELECT criado_em FROM logs WHERE etapa = 'coleta' ORDER BY id DESC LIMIT 1"
    )
    ultima_publicacao = buscar_uma_coluna(
        "SELECT data_publicacao FROM postagens WHERE status = 'publicado' ORDER BY data_publicacao DESC LIMIT 1"
    )
    try:
        catalogo = json.loads(Path("site/ofertas.json").read_text(encoding="utf-8"))
        ofertas_publicas = len(catalogo.get("ofertas", []))
    except (OSError, json.JSONDecodeError):
        ofertas_publicas = 0
    paginas_produto = len(list(Path("site/produto").glob("*/*/index.html")))
    ultima_validacao = buscar_uma_coluna(
        "SELECT data_evento FROM sistema_eventos WHERE tipo_evento = 'validacao' ORDER BY id DESC LIMIT 1"
    )
    ultimo_deploy = buscar_uma_coluna(
        "SELECT data_evento FROM sistema_eventos WHERE tipo_evento = 'deploy_github' AND status IN ('sucesso', 'concluido') ORDER BY id DESC LIMIT 1"
    )

    mestre = obter_estado_sistema()
    indicador_estado = {"ONLINE": "🟢", "MANUTENCAO": "🟡", "OFFLINE": "🔴"}.get(mestre["estado"], "🟡")
    print("Status IA-Promocoes")
    print(f"Estado atual: {indicador_estado} {mestre['estado']}")
    print(f"Motivo: {mestre.get('motivo') or 'sem observação'}")
    print(f"Robô: {'rodando' if pid else 'parado'}" + (f" (PID {pid})" if pid else ""))
    saude_busca = obter_saude_coleta_api()
    modo_coleta = os.getenv("MELI_COLETA_MODO", "auto").strip().lower() or "auto"
    if busca_api_bloqueada():
        busca_api = f"403 em cache até {saude_busca.get('bloqueado_ate')}"
    elif saude_busca.get("status") == "ok":
        busca_api = "OK"
    elif saude_busca.get("status") == "403":
        busca_api = "403 (cache expirado)"
    else:
        busca_api = "sem registro"
    print(f"OAuth Mercado Livre: {'OK (configurado)' if status_oauth_local() else 'Erro (configuração ausente)'}")
    print(f"API busca Mercado Livre: {busca_api}")
    print(f"Coleta ativa: {modo_coleta}")
    print(f"Fallback ativo: {'sim' if modo_coleta == 'auto' and busca_api_bloqueada() else 'não'}")
    estado = estado_producao()
    if estado:
        print(f"Início do serviço: {estado.get('iniciado_em', 'sem registro')}")
        print(f"Último ciclo: {estado.get('ultimo_ciclo', 'sem registro')}")
    servicos = {
        "Site": True,
        "Scheduler": bool(pid),
        "Monitor": bool(pid) and mestre["estado"] == "ONLINE",
        "Telegram": bool(pid) and mestre["estado"] == "ONLINE",
        "IA Consultiva": mestre["estado"] != "OFFLINE",
        "IA Revisora": mestre["estado"] != "OFFLINE",
        "Analytics": bool(_pid_servico(ANALYTICS_PID_FILE)),
        "Painel": bool(_pid_servico(PAINEL_PID_FILE)),
        "Deploy": mestre["estado"] == "ONLINE",
    }
    print("\nServiços:")
    for nome, ativo in servicos.items():
        simbolo = "🟢" if ativo and mestre["estado"] == "ONLINE" else "🟡" if ativo else "🔴"
        print(f"{simbolo} {nome}: {'ativo' if ativo else 'parado'}")
    print(f"Pendentes: {dados['fila_pendente']}")
    print(f"Publicados hoje: {publicados_hoje or 0}")
    print(f"Última coleta: {ultima_coleta or 'sem registro'}")
    print(f"Última publicação: {ultima_publicacao or 'sem registro'}")
    print(f"Catálogo público: {ofertas_publicas} ofertas | {paginas_produto} páginas de produto")
    print(f"Última validação: {ultima_validacao or 'sem registro'}")
    print(f"Último deploy: {ultimo_deploy or 'sem registro'}")
    from saude_sistema import obter_relatorio_saude
    saude = obter_relatorio_saude()
    niveis_saude = [alerta["nivel"] for alerta in saude["alertas"]]
    print(f"Saúde: {saude['status_geral']} | críticos={niveis_saude.count('critico')} alertas={niveis_saude.count('alerta')} avisos={niveis_saude.count('aviso')}")

    erros = logs_recentes("error", 5)
    if erros:
        print("\nErros recentes:")
        for erro in erros:
            print(f"- {erro['criado_em']} [{erro['etapa']}] {resumir_mensagem(erro['mensagem'])}")
    else:
        print("\nErros recentes: nenhum")


def comando_coletar():
    from publicador_telegram import gerar_site_local, gerar_whatsapp_manual
    from coletor_mercadolivre import coletar as coletar_mercadolivre
    from fila_postagens import gerar_fila_de_produtos

    preparar_base(migrar=True)
    produtos = coletar_mercadolivre()
    resultado_fila = gerar_fila_de_produtos()
    gerar_site_local()
    gerar_whatsapp_manual()
    print(
        f"Coleta manual concluída: candidatos={len(produtos)} "
        f"aprovados={resultado_fila['aprovados']} pendentes/rejeitados={resultado_fila['rejeitados']}."
    )
    print("Telegram não foi acionado.")
    return 0


def comando_coletar_confiavel(visual=False):
    from coleta_confiavel import coletar_confiavel

    preparar_base()
    try:
        resultado = coletar_confiavel(visual=visual)
    except Exception as erro:
        print(f"Coleta confiável interrompida: {erro}")
        return 1
    print(f"Encontrados: {resultado['encontrados']}")
    print(f"Completos: {resultado['completos']}")
    print(f"Salvos/atualizados: {resultado['salvos']}")
    print(f"Com meli.la: {resultado['afiliados']}")
    print(f"Falhas: {len(resultado['falhas'])}")
    print("Relatório: RELATORIO_COLETA_CONFIAVEL.md")
    print("Telegram não foi acionado.")
    return 0 if not resultado["falhas"] else 1


def comando_limpar_titulos():
    from limpar_titulos import limpar_titulos_existentes

    preparar_base()
    resultado = limpar_titulos_existentes()
    print(f"Títulos corrigidos: {resultado['corrigidos']}")
    print(f"Backup: {resultado['backup']}")
    for antes, depois in resultado["exemplos"]:
        print(f"- Antes: {antes}")
        print(f"  Depois: {depois}")
    print("Relatório: RELATORIO_LIMPEZA_TITULOS.md")
    return 0


def _executar_teste_captura(url, comparar=False):
    from playwright.sync_api import sync_playwright
    from agente_ofertas import extrair_item_id
    from captura_hibrida import capturar_produto_hibrido
    from coleta_confiavel import _detalhar_produto_legado
    from playwright_perfil import PERFIL_PRINCIPAL, PERFIL_RESERVA

    perfil = PERFIL_PRINCIPAL if PERFIL_PRINCIPAL.exists() else PERFIL_RESERVA
    candidato = {"permalink": url, "titulo": "", "item_id": extrair_item_id(url), "desconto": 0}
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch_persistent_context(user_data_dir=str(perfil), headless=False)
        try:
            resultados = {}
            if comparar:
                pagina = navegador.new_page()
                pagina.set_default_timeout(12000)
                inicio = time.monotonic()
                try:
                    produto = _detalhar_produto_legado(pagina, candidato)
                    resultados["legado"] = {"ok": True, "tempo_ms": round((time.monotonic() - inicio) * 1000), "campos": sorted(chave for chave, valor in produto.items() if valor not in (None, "", 0, False))}
                except Exception as erro:
                    resultados["legado"] = {"ok": False, "erro": str(erro), "tempo_ms": round((time.monotonic() - inicio) * 1000)}
                pagina.close()
            pagina = navegador.new_page()
            pagina.set_default_timeout(12000)
            resultado = capturar_produto_hibrido(pagina, candidato)
            pagina.close()
            resultados["hibrido"] = resultado
            return resultados
        finally:
            navegador.close()


def comando_testar_captura_produto(argumentos, comparar=False):
    url = _validar_permalink_argumento(argumentos)
    if not url:
        return 1
    try:
        resultados = _executar_teste_captura(url, comparar=comparar)
    except Exception as erro:
        print(f"Teste de captura falhou: {erro}")
        return 1
    if comparar:
        legado = resultados.get("legado", {})
        print(f"Legado: {'ok' if legado.get('ok') else 'falhou'} | tempo={legado.get('tempo_ms', 0)}ms | campos={len(legado.get('campos', []))}")
    hibrido = resultados["hibrido"]
    print(f"Híbrido: {'completo' if hibrido['completo'] else 'incompleto'}")
    print(f"Fontes: {', '.join(hibrido['fontes'])}")
    print(f"Tempos (ms): {hibrido['tempos_ms']}")
    print(f"Campos válidos: {', '.join(hibrido['campos_validos'])}")
    print(f"Campos faltantes: {', '.join(hibrido['campos_faltantes']) or 'nenhum'}")
    campos_capturados = [
        nome for nome in ("titulo", "preco_atual", "preco_original", "desconto_percentual", "economia_valor",
                           "imagem", "descricao_curta", "categoria_nome", "categoria_caminho", "avaliacao",
                           "quantidade_vendida", "vendedor_nome", "link_afiliado")
        if hibrido["produto"].get(nome) not in (None, "", 0, False)
    ]
    print(f"Campos capturados: {', '.join(campos_capturados)}")
    print(f"meli.la gerado: {'sim' if hibrido['produto'].get('link_afiliado') else 'não'}")
    print("Banco, status, Telegram, site e deploy não foram alterados.")
    return 0 if hibrido["completo"] else 1


def comando_reprocessar_pendentes(dry_run=False):
    from reprocessar_pendentes import reprocessar_pendentes

    resultado = reprocessar_pendentes(dry_run=dry_run)
    modo = "Simulação" if dry_run else "Reprocessamento"
    print(f"{modo}: total={resultado['total']} aprovados_auto={resultado['aprovados_auto']} pendentes={resultado['pendentes']} rejeitados={resultado['rejeitados']}")
    if resultado["backup"]:
        print(f"Backup: {resultado['backup']}")
    print("Relatório: RELATORIO_REPROCESSAMENTO_PENDENTES.md")
    print("Telegram e deploy não foram acionados.")
    return 0


def comando_simular_score():
    from auditoria_score import simular_score

    preparar_base()
    resultado = simular_score()
    print(f"Pendentes auditadas: {resultado['total']}")
    for nome, cenario in resultado["cenarios"].items():
        print(f"\n{nome}")
        print(f"- aprovadas_auto: {cenario['aprovadas_auto']}")
        print(f"- revisao_manual: {cenario['revisao_manual']}")
        print(f"- rejeitadas: {cenario['rejeitadas']}")
    print(f"\nRelatório: {resultado['relatorio']}")
    print("Simulação concluída: nenhuma regra ou status foi alterado.")
    return 0


def comando_atualizar_categorias():
    from atualizar_categorias import atualizar_categorias

    preparar_base()
    resultado = atualizar_categorias()
    print(f"Produtos consultados: {resultado['total']}")
    print(f"Categorias reais atualizadas: {resultado['atualizadas']}")
    print(f"Categorias já reais: {resultado['ja_reais']}")
    print(f"Fallbacks locais: {resultado['fallback']}")
    print(f"Erros de API: {resultado['erros']}")
    print("Relatório: RELATORIO_ATUALIZACAO_CATEGORIAS.md")
    return 0


def comando_calibrar_curadoria():
    from calibracao_curadoria import aplicar_calibracao

    preparar_base()
    resultado = aplicar_calibracao()
    curadoria = resultado["curadoria"]
    categorias = resultado["categorias"]
    print(f"Backup: {resultado['backup']}")
    print(f"Curadoria: aprovadas={curadoria['aprovados_auto']} pendentes={curadoria['pendentes']} rejeitadas={curadoria['rejeitados']}")
    print(f"Categorias: atualizadas={categorias['atualizadas']} fallback={categorias['fallback']} erros_api={categorias['erros']}")
    print(f"Relatório: {resultado['relatorio']}")
    print("Telegram, deploy e modo ONLINE não foram acionados.")
    return 0


def comando_reprocessar_pendentes_enriquecido(dry_run=False):
    from reprocessar_pendentes_enriquecido import reprocessar_pendentes_enriquecido

    preparar_base()
    resultado = reprocessar_pendentes_enriquecido(dry_run=dry_run)
    print(f"Enriquecido: total={resultado['total']} aprovadas={resultado['aprovados']} pendentes={resultado['pendentes']} rejeitadas={resultado['rejeitados']}")
    if resultado["backup"]:
        print(f"Backup: {resultado['backup']}")
    print("Relatório: RELATORIO_ENRIQUECIMENTO_OFERTAS.md")
    print("Telegram, deploy e modo ONLINE não foram acionados.")
    return 0


def comando_auditar_paginas_produto():
    from integridade_paginas_produto import auditar_paginas_produto

    resultado = auditar_paginas_produto()
    print(f"Ofertas públicas: {len(resultado['ofertas'])}")
    print(f"Páginas individuais: {len(resultado['paginas'])}")
    print(f"Ofertas sem página: {len(resultado['sem_pagina'])}")
    print(f"Páginas órfãs: {len(resultado['orfas'])}")
    print(f"Item_id duplicados: {len(resultado['duplicados_item'])}")
    print(f"Slug duplicados: {len(resultado['duplicados_slug'])}")
    print("Relatório: RELATORIO_INTEGRIDADE_SITE.md")
    return 0 if not resultado["erros"] else 1


def comando_auditar_indisponiveis():
    from recuperacao_indisponiveis import auditar_indisponiveis

    resultado = auditar_indisponiveis()
    totais = resultado["totais"]
    print(f"Indisponíveis: {len(resultado['itens'])}")
    print(f"Recuperáveis com segurança: {totais['recuperar_seguro']}")
    print(f"Item_id inválido: {totais['manter_item_id_invalido']}")
    print(f"404/finalizados: {totais['manter_indisponivel_confirmado']}")
    print(f"Sem motivo claro: {totais['manter_sem_evidencia']}")
    print("Relatório: RELATORIO_RECUPERACAO_INDISPONIVEIS.md")
    return 0


def comando_auditar_qualidade_catalogo():
    from qualidade_catalogo import auditar_qualidade_catalogo

    resultado = auditar_qualidade_catalogo()
    print(f"Catálogo: {resultado['indicador']}")
    for chave, valor in resultado["metricas"].items():
        if chave != "status":
            print(f"- {chave}: {valor}")
    print("Relatório: RELATORIO_QUALIDADE_CATALOGO.md")
    return 0 if resultado["indicador"] != "REPROVADO" else 1


COMANDOS_PROMOGG = {
    "MASTER Produção": {
        "iniciar-producao": "Executa pré-voo e entra em ONLINE apenas se aprovado.",
        "manutencao-producao": "Entra em manutenção preservando painel e dados.",
        "parar-producao": "Para a produção com segurança, preservando dados.",
    },
    "Operação Master": {
        "online": "Ativa serviços e automações controladas.", "manutencao": "Pausa automações e mantém painel/dados disponíveis.",
        "offline": "Para serviços automatizados com preservação dos dados.", "status": "Mostra estado, serviços e eventos recentes.",
        "iniciar": "Inicia o worker local de produção.", "producao": "Inicia o worker de produção.", "parar": "Solicita parada segura do worker.", "reiniciar": "Reinicia o worker preservando banco e histórico.",
    },
    "Site": {"gerar-site": "Gera o site estático local.", "validar": "Valida banco, site, SEO, segurança e assistentes.", "servir-site": "Abre o site local para teste.", "subir-site": "Valida e envia o site ao GitHub Pages.", "publicar-site": "Prepara dist_site sem fazer push.", "publicar": "Valida e publica quando o estado permite."},
    "Coleta": {"coletar": "Coleta normal com modo configurado.", "coletar-confiavel": "Coleta lenta com checkpoint por produto.", "testar-coleta-api": "Compara API e Playwright sem persistir.", "testar-captura-produto": "Diagnostica a captura híbrida sem persistir.", "comparar-captura": "Compara captura legada e híbrida sem persistir."},
    "Afiliados": {"gerar-afiliados": "Gera links oficiais meli.la pendentes.", "diagnosticar-afiliado": "Resume a saúde dos links afiliados.", "diagnosticar-compartilhar": "Inspeciona o botão oficial sem alterar dados.", "testar-afiliado": "Testa geração de meli.la sem persistir."},
    "Curadoria": {"reprocessar-pendentes": "Reaplica a curadoria aos pendentes.", "reprocessar-pendentes-enriquecido": "Simula ou aplica curadoria com sinais públicos.", "simular-score": "Compara cenários de score sem alterar banco.", "limpar-titulos": "Saneia títulos com backup.", "calibrar-curadoria": "Aplica calibração segura com backup."},
    "Monitoramento": {"monitorar-precos": "Atualiza preços e histórico sem publicar.", "atualizar-categorias": "Consulta categorias por item_id.", "recuperar-indisponiveis": "Recupera indisponibilidades técnicas; use --dry-run primeiro.", "auditar-indisponiveis": "Audita indisponibilidades."},
    "IA": {"perguntar": "Consulta local de preços.", "treinar-memoria": "Atualiza memória local sem treinar modelo.", "revisar-ofertas": "Gera pareceres da IA revisora.", "treinar-revisora": "Atualiza estatísticas da revisora."},
    "Analytics e Saúde": {"analytics-teste": "Registra um clique de teste local sem dados pessoais.", "analytics-status": "Mostra métricas e a configuração do endpoint.", "saude": "Mostra saúde resumida do sistema.", "saude-detalhada": "Separa críticos, alertas, avisos e eventos.", "relatorio-operacional": "Mostra resumo diário.", "relatorio": "Mostra resumo operacional.", "relatorio-precos": "Mostra resumo de histórico.", "auditar-qualidade-catalogo": "Audita o catálogo público.", "simular": "Simula a próxima publicação Telegram.", "publicar-um": "Publica uma oferta elegível."},
    "Segurança e Diagnóstico": {"meli-auth": "Inicia OAuth Mercado Livre.", "meli-testar-token": "Testa token sem exibi-lo.", "meli-refresh-token": "Renova token local.", "diagnosticar-playwright": "Verifica perfil e locks.", "reparar-playwright": "Remove locks preservando sessão.", "auditar-paginas-produto": "Compara catálogo e páginas individuais.", "corrigir-paginas-produto": "Regenera páginas e remove órfãs.", "auditar-base": "Resume saúde da base.", "reconstruir-base": "Executa recuperação estruturada da base."},
    "Backup e Manutenção": {"backup": "Cria backup operacional seguro.", "restaurar": "Lista backups disponíveis.", "limpar-seguro": "Quarentena segura de candidatos auditados.", "mapa": "Exibe o mapa do projeto.", "painel": "Abre o painel Streamlit.", "comandos": "Lista esta ajuda organizada."},
}


def comando_comandos():
    print("Comandos Promogg")
    for grupo, comandos in COMANDOS_PROMOGG.items():
        print(f"\n{grupo}:")
        for nome, descricao in comandos.items():
            print(f"- {nome}: {descricao}")
    print("\nUse --dry-run antes de comandos de recuperação ou reprocessamento quando disponível.")
    return 0


def comando_recuperar_indisponiveis(dry_run=False):
    from recuperacao_indisponiveis import recuperar_indisponiveis

    resultado = recuperar_indisponiveis(dry_run=dry_run)
    print(f"Modo: {'dry-run' if dry_run else 'execução real'}")
    print(f"Recuperados/simulados: {resultado['recuperados']}")
    print(f"Backup: {resultado['backup'] or 'não aplicável'}")
    print("Relatório: RELATORIO_RECUPERACAO_INDISPONIVEIS.md")
    print("Telegram, deploy e ONLINE não foram acionados.")
    return 0


def comando_corrigir_paginas_produto():
    from integridade_paginas_produto import corrigir_paginas_produto

    preparar_base()
    resultado = corrigir_paginas_produto()
    auditoria = resultado["auditoria"]
    print(f"Catálogo regenerado: {resultado['geracao']['ofertas']} ofertas e {resultado['geracao']['paginas_produto']} páginas.")
    print(f"Ofertas sem página: {len(auditoria['sem_pagina'])} | Órfãs: {len(auditoria['orfas'])}")
    print("Relatório: RELATORIO_INTEGRIDADE_SITE.md")
    return 0 if not auditoria["erros"] else 1


def comando_testar_coleta_api(comparar_playwright=False):
    """Compara fontes sem inserir, atualizar ou publicar qualquer oferta."""
    from coletor_mercadolivre_api import coletar_ofertas_api

    try:
        api = coletar_ofertas_api()
    except Exception as erro:
        api = []
        print(f"API oficial: falhou ({erro})")
    print(f"API oficial: {len(api)} item(ns) válidos")
    if api:
        completos = sum(bool(p.get("item_id") and p.get("titulo") and p.get("preco") and p.get("link") and p.get("categoria_id")) for p in api)
        print(f"API oficial: {completos}/{len(api)} com ID, título, preço, permalink e categoria")

    playwright = []
    if comparar_playwright:
        from agente_ofertas import coletar_ofertas

        try:
            playwright = coletar_ofertas()
            print(f"Playwright: {len(playwright)} item(ns) válidos")
        except Exception as erro:
            print(f"Playwright: falhou ({erro})")
    else:
        print("Playwright: não executado (use o comando com o argumento playwright para comparar; abre navegador).")

    if api and (not comparar_playwright or len(api) >= len(playwright)):
        print("Recomendação: manter API oficial como fonte principal.")
    elif playwright:
        print("Recomendação: manter fallback Playwright enquanto a busca API é ajustada.")
    else:
        print("Recomendação: revisar MELI_COLETA_TERMOS e OAuth antes de ativar a coleta API.")
    print("Modo de comparação: produtos, histórico, fila e site não foram alterados; apenas a saúde da busca API pode ser atualizada.")
    return 0 if api else 1


def comando_diagnosticar_playwright():
    from playwright_perfil import imprimir_diagnostico

    imprimir_diagnostico()
    return 0


def comando_reparar_playwright():
    from playwright_perfil import reparar_perfil

    try:
        resultado = reparar_perfil()
    except RuntimeError as erro:
        print(f"Reparo não concluído: {erro}")
        return 1
    print(f"Processos encerrados: {len(resultado['encerrados'])}")
    print(f"Locks removidos: {len(resultado['locks_removidos'])}")
    print(f"Perfil reserva: {resultado['reserva']}")
    print(f"Perfil principal disponível: {'sim' if resultado['disponivel'] else 'não'}")
    return 0


def comando_auditar_base():
    from recuperacao_base import imprimir_auditoria_base

    imprimir_auditoria_base()
    return 0


def comando_diagnosticar_afiliado():
    from auditoria_afiliados import imprimir_diagnostico

    imprimir_diagnostico()
    return 0


def comando_gerar_afiliados():
    from fila_postagens import gerar_fila_de_produtos
    from gerador_afiliados_oficial import gerar_links_afiliados

    preparar_base()
    try:
        resultado = gerar_links_afiliados()
    except Exception as erro:
        print(f"Não foi possível gerar links afiliados: {erro}")
        return 1
    fila = gerar_fila_de_produtos()
    print(f"Pendentes de afiliado: {resultado['pendentes']}")
    print(f"Links meli.la gerados: {resultado['gerados']}")
    print(f"Falhas: {resultado['falhas']}")
    print(f"Curadoria após links: aprovados={fila['aprovados']} pendentes/rejeitados={fila['rejeitados']}")
    print("Telegram não foi acionado.")
    return 0 if not resultado["falhas"] else 1


def _validar_permalink_argumento(argumentos):
    if not argumentos:
        print("Informe a URL do produto Mercado Livre.")
        return ""
    url = argumentos[0].strip()
    if not url.startswith(("https://www.mercadolivre.com", "https://meli.la/")):
        print("Informe uma URL HTTPS do Mercado Livre.")
        return ""
    return url


def comando_diagnosticar_compartilhar(argumentos):
    from gerador_afiliados_oficial import diagnosticar_compartilhar

    url = _validar_permalink_argumento(argumentos)
    if not url:
        return 1
    resultado = diagnosticar_compartilhar(url, clicar=False)
    print(f"Botão oficial encontrado: {'sim' if resultado['encontrado'] else 'não'}")
    print(f"Estratégia: {resultado['estrategia']}")
    print(f"Coordenadas: {resultado['coordenadas'] or 'não disponível'}")
    print(f"Screenshot: {resultado['screenshot_antes'] or 'não disponível'}")
    return 0 if resultado["encontrado"] else 1


def comando_testar_afiliado(argumentos):
    from gerador_afiliados_oficial import diagnosticar_compartilhar

    url = _validar_permalink_argumento(argumentos)
    if not url:
        return 1
    resultado = diagnosticar_compartilhar(url, clicar=True)
    link = resultado["link"]
    mascarado = f"https://meli.la/{link.rsplit('/', 1)[-1][:3]}..." if link else "não encontrado"
    print(f"Botão oficial encontrado: {'sim' if resultado['encontrado'] else 'não'}")
    print(f"Estratégia: {resultado['estrategia']}")
    print(f"Link meli.la: {mascarado}")
    print(f"Screenshots: antes={resultado['screenshot_antes'] or '-'} depois={resultado['screenshot_depois'] or '-'} link={resultado['screenshot_link'] or '-'}")
    print("Banco, aprovação, Telegram e site não foram alterados.")
    return 0 if link else 1


def comando_reconstruir_base():
    from recuperacao_base import reconstruir_base

    resultado = reconstruir_base()
    print(f"Reconstrução: {resultado['resultado']}")
    print(f"Ofertas no site: {resultado.get('ofertas_site', 0)}")
    print(f"Páginas de produto: {resultado.get('paginas_produto', 0)}")
    print("Relatório: RELATORIO_RECUPERACAO_BASE.md")
    return 0 if resultado.get("homologado") else 1


def comando_simular():
    from publicador_telegram import gerar_whatsapp_manual, publicar_um

    preparar_base()
    publicar_um(dry_run=True)
    gerar_whatsapp_manual()
    return 0


def comando_publicar_um():
    from publicador_telegram import gerar_whatsapp_manual, publicar_um

    preparar_base()
    publicar_um(dry_run=False)
    gerar_whatsapp_manual()
    return 0


def comando_painel():
    preparar_base()
    executavel = Path("venv/bin/python") if Path("venv/bin/python").exists() else Path(sys.executable)
    return subprocess.call([str(executavel), "-m", "streamlit", "run", "painel.py"])


def _atualizar_site_por_estado():
    destino = copiar_site("dist_site")
    registrar_evento_sistema("site_estado", "master", "sucesso", "Site atualizado conforme estado mestre", str(destino))


def comando_online():
    from estado_sistema import ONLINE, definir_estado_sistema

    definir_estado_sistema(ONLINE, "MASTER ONLINE acionado")
    _atualizar_site_por_estado()
    try:
        deploy_ok = comando_publicar() == 0
    except Exception as erro:
        deploy_ok = False
        registrar_evento_sistema("deploy_github", "master", "erro", "Falha ao publicar ao entrar em ONLINE", str(erro))
    producao = _iniciar_servico("scheduler", PID_FILE, "producao.log", [__file__, "_worker-producao"])[0] if not robo_rodando() else robo_rodando()
    analytics, _ = _iniciar_servico("analytics", ANALYTICS_PID_FILE, "analytics.log", ["servidor_analytics.py"])
    painel, _ = _iniciar_servico("painel", PAINEL_PID_FILE, "painel.log", ["-m", "streamlit", "run", "painel.py", "--server.headless", "true"])
    registrar_evento_sistema("master", "operacao", "sucesso", "Sistema MASTER ONLINE", f"scheduler={producao} analytics={analytics} painel={painel}")
    print("Sistema online")
    print(f"- Site online e deploy {'confirmado' if deploy_ok else 'pendente de verificação'}")
    print("- Monitoramento ativo no scheduler")
    print("- IA ativa por serviços locais")
    print("- Telegram controlado pelo scheduler")
    print(f"- Painel ativo: PID {painel}")
    return 0


def comando_iniciar_producao(dry_run=False):
    from producao_promogg import executar_preflight_producao, imprimir_preflight, registrar_resultado_preflight

    preparar_base()
    resultado = executar_preflight_producao(testar_oauth_remoto=not dry_run)
    imprimir_preflight(resultado)
    registrar_resultado_preflight(resultado)
    if not resultado["aprovado"]:
        print("Produção não foi iniciada. Corrija as pendências críticas e execute novamente.")
        return 1
    if dry_run:
        print("Modo seco concluído: produção não foi iniciada.")
        return 0
    print("Pré-voo aprovado. Iniciando operação ONLINE...")
    return comando_online()


def comando_manutencao():
    from estado_sistema import MANUTENCAO, definir_estado_sistema

    definir_estado_sistema(MANUTENCAO, "MASTER MANUTENCAO acionado")
    comando_parar()
    _atualizar_site_por_estado()
    painel, _ = _iniciar_servico("painel", PAINEL_PID_FILE, "painel.log", ["-m", "streamlit", "run", "painel.py", "--server.headless", "true"])
    registrar_evento_sistema("master", "operacao", "aviso", "Sistema em manutenção", f"painel={painel}")
    print("Painel ativo | Banco ativo | IA ativa | Coleta pausada | Publicações pausadas")
    return 0


def comando_manutencao_producao():
    return comando_manutencao()


def comando_offline():
    from estado_sistema import OFFLINE, definir_estado_sistema

    definir_estado_sistema(OFFLINE, "MASTER OFFLINE acionado")
    comando_parar()
    _parar_servico("analytics", ANALYTICS_PID_FILE)
    _parar_servico("painel", PAINEL_PID_FILE)
    _atualizar_site_por_estado()
    registrar_evento_sistema("master", "operacao", "sucesso", "Sistema desligado com segurança")
    print("Sistema desligado com segurança. Banco, histórico e backups foram preservados.")
    return 0


def comando_parar_producao():
    return comando_offline()


def comando_gerar_site():
    preparar_base()
    resultado = gerar_site()
    print(f"Site gerado em site/ com {resultado['ofertas']} ofertas.")
    return 0


def comando_validar(checar_estados=True):
    from promogg_assistente import validar_assistente
    from saude_sistema import validar_saude_sistema
    from operacao_sistema import validar_operacao_sistema
    from ia_revisora import validar_revisora
    from estado_sistema import MANUTENCAO, OFFLINE, ONLINE, definir_estado_sistema, obter_estado_sistema
    from meli_oauth import validar_oauth_local
    from coletor_mercadolivre_api import validar_coleta_api
    from captura_hibrida import validar_captura_hibrida
    from analytics_promogg import validar_analytics
    from gerador_link_mercadolivre import link_afiliado_valido

    erros = []
    estado_original = obter_estado_sistema()
    try:
        definir_estado_sistema(ONLINE, "validação automática")
        gerar_site()
        erros += validar_site_publico() + validar_assistente() + validar_saude_sistema() + validar_operacao_sistema() + validar_revisora() + validar_oauth_local()
        erros += validar_coleta_api() + validar_analytics()
        erros += validar_captura_hibrida()
        with conectar() as conn:
            links_inseguros = conn.execute(
                "SELECT COUNT(*) FROM postagens WHERE status IN ('aprovado_auto', 'aprovado_manual', 'publicado') AND (link_afiliado IS NULL OR link_afiliado = '' OR link_afiliado NOT LIKE 'https://meli.la/%')"
            ).fetchone()[0]
        if links_inseguros:
            erros.append(f"Há {links_inseguros} postagem(ns) aprovada(s) sem link meli.la")
        if checar_estados:
            definir_estado_sistema(MANUTENCAO, "validação automática")
            gerar_site()
            if "Estamos realizando melhorias internas" not in Path("site/index.html").read_text(encoding="utf-8"):
                erros.append("Banner de manutenção não foi gerado")
            definir_estado_sistema(OFFLINE, "validação automática")
            gerar_site()
            if "Promogg temporariamente offline" not in Path("site/index.html").read_text(encoding="utf-8"):
                erros.append("Página offline não foi gerada")
            definir_estado_sistema(ONLINE, "validação automática")
            if obter_estado_sistema()["estado"] != ONLINE:
                erros.append("Persistência do estado ONLINE falhou")
    except Exception as erro:
        erros.append(f"Validação do estado mestre falhou: {erro}")
    finally:
        definir_estado_sistema(estado_original["estado"], estado_original.get("motivo", ""))
        gerar_site()
    if erros:
        registrar_evento_sistema("validacao", "operacao", "erro", "Validação operacional falhou", "; ".join(erros[:5]))
        print("Validação do site público falhou:")
        for erro in erros:
            print(f"- {erro}")
        return 1
    registrar_evento_sistema("validacao", "operacao", "sucesso", "Validação operacional concluída")
    print("Validação concluída: site, SEO, analytics, assistentes, banco, saúde e backup operacionais.")
    return 0


def comando_saude():
    from saude_sistema import imprimir_relatorio_saude

    preparar_base()
    imprimir_relatorio_saude()
    return 0


def comando_saude_detalhada():
    from saude_sistema import imprimir_relatorio_saude_detalhada

    preparar_base()
    imprimir_relatorio_saude_detalhada()
    return 0


def comando_analytics_teste():
    from analytics_promogg import gerar_relatorio_analytics, status_analytics, testar_analytics_local

    preparar_base()
    try:
        resultado = testar_analytics_local()
    except Exception as erro:
        print(f"Teste de analytics falhou: {erro}")
        return 1
    gerar_relatorio_analytics(status_analytics(), resultado)
    print("Teste local de analytics:")
    print(f"- HTTP: {resultado['http']}")
    print(f"- Item: {resultado['item_id']}")
    print(f"- Evento salvo: {'sim' if resultado['salvo'] else 'não'}")
    print("- Dados pessoais: não coletados")
    print("Relatório: RELATORIO_ANALYTICS_HOMOLOGACAO.md")
    return 0 if resultado["salvo"] else 1


def comando_analytics_status():
    from analytics_promogg import gerar_relatorio_analytics, status_analytics

    preparar_base()
    resultado = status_analytics(consultar_endpoint=True)
    gerar_relatorio_analytics(resultado)
    print("Status Analytics Promogg")
    print(f"Total de cliques reais: {resultado['total']}")
    print(f"Cliques reais hoje: {resultado['hoje']}")
    print(f"Eventos de teste: {resultado['testes']}")
    print(f"Servidor local: {'ativo' if resultado['servidor_local_ativo'] else 'parado'}")
    print(f"Endpoint público configurado: {'sim' if resultado['endpoint_publico_configurado'] else 'não'}")
    print(f"Site público configurado para enviar: {'sim' if resultado['site_configurado'] else 'não'}")
    print(f"JavaScript de analytics: {'pronto' if resultado['javascript_pronto'] else 'ausente'}")
    if resultado["endpoint_ativo"] is not None:
        print(f"Endpoint público responde: {'sim' if resultado['endpoint_ativo'] else 'não'}")
    print("Top produtos:")
    for item in resultado["top_produtos"][:5]:
        print(f"- {item['total']} | {item['titulo']} ({item['item_id']})")
    print("Top categorias:")
    for item in resultado["top_categorias"][:5]:
        print(f"- {item['total']} | {item['categoria']}")
    print("Últimos eventos:")
    for item in resultado["ultimos"][:5]:
        print(f"- {item['criado_em']} | {item['tipo_evento']} | {item['item_id']} | {item['categoria']}")
    print("Relatório: RELATORIO_ANALYTICS_HOMOLOGACAO.md")
    return 0


def comando_relatorio_operacional():
    from operacao_sistema import imprimir_relatorio_operacional

    preparar_base()
    imprimir_relatorio_operacional()
    return 0


def comando_backup():
    from operacao_sistema import criar_backup_emergencia

    preparar_base()
    try:
        destino = criar_backup_emergencia()
    except Exception as erro:
        registrar_log("backup", f"Falha ao criar backup operacional: {erro}", nivel="error")
        registrar_evento_sistema("backup", "operacao", "critico", "Falha ao criar backup de emergência", str(erro))
        print("Não foi possível criar o backup. Consulte `python3 ia_promocoes.py saude`.")
        return 1
    print(f"Backup de emergência criado: {destino}")
    print("O arquivo não inclui .env, tokens, cookies ou outros segredos.")
    return 0


def comando_restaurar():
    from operacao_sistema import imprimir_backups_disponiveis

    preparar_base()
    imprimir_backups_disponiveis()
    return 0


def comando_revisar_ofertas():
    from ia_revisora import revisar_ofertas

    preparar_base()
    analises = revisar_ofertas()
    print(f"IA revisora concluiu {len(analises)} análise(s). Nenhuma aprovação foi alterada.")
    for analise in analises:
        print(f"- #{analise['postagem_id']} | {analise['score_revisora']:.1f}/100 | {analise['sugestao']} | {analise['titulo']}")
    return 0


def comando_treinar_revisora():
    from ia_revisora import treinar_revisora

    preparar_base()
    categorias = treinar_revisora()
    print(f"Memória estatística da revisora atualizada para {categorias} categoria(s).")
    print("Nenhum modelo foi treinado ou alterado.")
    return 0


def comando_limpar_seguro():
    from limpeza_segura import executar_limpeza_segura

    preparar_base()
    backup, quarentena, movidos = executar_limpeza_segura()
    print(f"Backup pré-limpeza: {backup}")
    if movidos:
        print(f"Arquivos movidos para quarentena: {quarentena}")
        for caminho in movidos:
            print(f"- {caminho}")
    else:
        print("Nenhum candidato confirmado estava presente; nada foi movido.")
    return 0


def comando_mapa():
    caminho = Path("MAPA_PROJETO.md")
    if not caminho.exists():
        print("MAPA_PROJETO.md não encontrado.")
        return 1
    print(caminho.read_text(encoding="utf-8"))
    return 0


def _imprimir_perfil_meli(perfil):
    print(f"HTTP status: {perfil['http_status']}")
    print(f"user_id: {perfil['user_id']}")
    print(f"nickname: {perfil['nickname']}")
    print(f"site_id: {perfil['site_id']}")


def comando_meli_auth():
    from meli_oauth import ErroOAuthMercadoLivre, autenticar_interativo

    try:
        perfil = autenticar_interativo()
    except ErroOAuthMercadoLivre as erro:
        print(str(erro))
        return 1
    print("Tokens OAuth salvos no .env local. Nenhum token foi exibido.")
    _imprimir_perfil_meli(perfil)
    return 0


def comando_meli_testar_token():
    from meli_oauth import ErroOAuthMercadoLivre, testar_token

    try:
        _imprimir_perfil_meli(testar_token())
    except ErroOAuthMercadoLivre as erro:
        print(str(erro))
        return 1
    return 0


def comando_meli_refresh_token():
    from meli_oauth import ErroOAuthMercadoLivre, refresh_token

    try:
        perfil = refresh_token()
    except ErroOAuthMercadoLivre as erro:
        print(str(erro))
        return 1
    print("Tokens OAuth renovados no .env local. Nenhum token foi exibido.")
    _imprimir_perfil_meli(perfil)
    return 0


def comando_perguntar(pergunta):
    from promogg_assistente import responder_pergunta

    if not pergunta.strip():
        print("Informe uma pergunta. Exemplo: python3 ia_promocoes.py perguntar \"Qual o preço atual do Xbox?\"")
        return 1
    print(responder_pergunta(pergunta)["texto"])
    return 0


def comando_treinar_memoria():
    from promogg_assistente import treinar_memoria

    preparar_base()
    total = treinar_memoria()
    print(f"Memória local atualizada para {total} produtos.")
    print("Nenhum modelo foi treinado ou alterado; apenas resumos locais foram recalculados.")
    return 0


def comando_servir_site():
    preparar_base()
    servir_site()
    return 0


def comando_publicar_site():
    preparar_base()
    destino = copiar_site("dist_site")
    print(f"Site preparado para publicação em: {destino}")
    print("Para GitHub Pages, use:")
    print("venv/bin/python deploy_site.py github-pages --destino /caminho/do/repositorio-pages")
    return 0


def comando_subir_site(reutilizar_site=False):
    from publicar_site_git import DOMINIO, subir_site

    preparar_base()

    try:
        resultado = subir_site(reutilizar_site=reutilizar_site)
    except RuntimeError as erro:
        print(f"Erro ao subir site: {erro}")
        print("\nAntes de rodar novamente, confira:")
        print("- repositório criado no GitHub")
        print("- git init executado nesta pasta")
        print("- remoto origin configurado")
        print(f"- GitHub Pages configurado com o domínio {DOMINIO}")
        return 1

    print(f"Site gerado e atualizado em: {resultado['destino']}")
    print(f"CNAME criado automaticamente para: {resultado['dominio']}")
    print(f"Alterações enviadas para o GitHub na branch: {resultado['branch']}")
    if not resultado["commit_criado"]:
        print("Nenhum commit novo foi necessário.")
    print("O GitHub Actions atualizará o GitHub Pages com a pasta dist_site/.")
    return 0


def comando_publicar():
    from estado_sistema import ONLINE, obter_estado_sistema

    if obter_estado_sistema()["estado"] != ONLINE:
        print("Publicação remota pausada pelo estado mestre. Use ONLINE para publicar.")
        return 1
    print("Validando sistema antes da publicação...")
    if comando_validar(checar_estados=False) != 0:
        print("Publicação cancelada: a validação encontrou problemas.")
        return 1
    print("Gerando e enviando a versão estática para o GitHub Pages...")
    resultado = comando_subir_site(reutilizar_site=True)
    if resultado == 0:
        registrar_evento_sistema("deploy_github", "publicacao", "sucesso", "Publicação de produção concluída")
    return resultado


def comando_relatorio():
    preparar_base()
    hoje = date.today().strftime("%Y-%m-%d")

    with conectar() as conn:
        coletados = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
        aprovados = conn.execute(
            "SELECT COUNT(*) FROM promocoes WHERE status IN ('aprovado', 'aprovado_auto', 'aprovado_manual')"
        ).fetchone()[0]
        rejeitados = conn.execute("SELECT COUNT(*) FROM promocoes WHERE status = 'rejeitado'").fetchone()[0]
        publicados = conn.execute("SELECT COUNT(*) FROM postagens WHERE status = 'publicado'").fetchone()[0]
        pendentes = conn.execute(
            "SELECT COUNT(*) FROM postagens WHERE status = 'pendente_revisao'"
        ).fetchone()[0]
        publicados_hoje = conn.execute(
            """
            SELECT COUNT(*)
            FROM postagens
            WHERE status = 'publicado'
              AND substr(COALESCE(data_publicacao, ''), 1, 10) = ?
            """,
            (hoje,),
        ).fetchone()[0]
        categorias = conn.execute(
            """
            SELECT categoria, COUNT(*) AS total
            FROM postagens
            WHERE status IN ('pendente', 'publicado')
            GROUP BY categoria
            ORDER BY total DESC
            LIMIT 10
            """
        ).fetchall()
        erros = conn.execute(
            """
            SELECT etapa, mensagem, criado_em
            FROM logs
            WHERE nivel = 'error'
              AND lower(etapa) NOT LIKE '%shopee%'
              AND lower(mensagem) NOT LIKE '%shopee%'
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()

    print("Relatório IA-Promocoes")
    print(f"Produtos coletados: {coletados}")
    print(f"Promoções aprovadas: {aprovados}")
    print(f"Promoções rejeitadas: {rejeitados}")
    print(f"Posts publicados: {publicados}")
    print(f"Posts publicados hoje: {publicados_hoje}")
    print(f"Posts pendentes: {pendentes}")

    print("\nMelhores categorias:")
    if categorias:
        for row in categorias:
            print(f"- {row['categoria']}: {row['total']}")
    else:
        print("- sem dados")

    print("\nErros recentes:")
    if erros:
        for row in erros:
            print(f"- {row['criado_em']} [{row['etapa']}] {row['mensagem']}")
    else:
        print("- nenhum erro recente")

    return 0


def comando_relatorio_precos():
    from consulta_precos import imprimir_resumo_precos

    preparar_base()
    imprimir_resumo_precos()
    return 0


def comando_monitorar_precos():
    from monitor_precos import monitorar_precos_diariamente

    preparar_base()
    resultado = monitorar_precos_diariamente(forcar=True)
    print("Monitoramento de preços:")
    for chave, valor in resultado.items():
        print(f"- {chave}: {valor}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Central operacional do Promogg.\n\nGrupos: MASTER Produção, Operação Master, Site, Coleta, Afiliados, Curadoria, Monitoramento, IA, Analytics, Segurança e Backup.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Comandos organizados: python3 ia_promocoes.py comandos\nUse --dry-run em operações que ofereçam simulação.",
    )
    parser.add_argument(
        "comando",
        metavar="COMANDO",
        choices=[
            "iniciar",
            "producao",
            "online",
            "iniciar-producao",
            "manutencao",
            "manutencao-producao",
            "offline",
            "parar-producao",
            "_worker-producao",
            "parar",
            "reiniciar",
            "status",
            "comandos",
            "painel",
            "simular",
            "publicar-um",
            "coletar",
            "coletar-confiavel",
            "testar-captura-produto",
            "comparar-captura",
            "limpar-titulos",
            "reprocessar-pendentes",
            "simular-score",
            "atualizar-categorias",
            "calibrar-curadoria",
            "reprocessar-pendentes-enriquecido",
            "auditar-paginas-produto",
            "auditar-indisponiveis",
            "auditar-qualidade-catalogo",
            "recuperar-indisponiveis",
            "corrigir-paginas-produto",
            "gerar-site",
            "validar",
            "servir-site",
            "publicar-site",
            "subir-site",
            "publicar",
            "relatorio",
            "relatorio-precos",
            "monitorar-precos",
            "perguntar",
            "treinar-memoria",
            "saude",
            "saude-detalhada",
            "analytics-teste",
            "analytics-status",
            "relatorio-operacional",
            "backup",
            "restaurar",
            "revisar-ofertas",
            "treinar-revisora",
            "limpar-seguro",
            "mapa",
            "meli-auth",
            "meli-testar-token",
            "meli-refresh-token",
            "testar-coleta-api",
            "diagnosticar-playwright",
            "reparar-playwright",
            "auditar-base",
            "reconstruir-base",
            "diagnosticar-afiliado",
            "gerar-afiliados",
            "diagnosticar-compartilhar",
            "testar-afiliado",
        ],
    )
    parser.add_argument("argumentos", nargs="*")
    parser.add_argument("--visual", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    comandos = {
        "iniciar": comando_iniciar,
        "producao": comando_producao,
        "online": comando_online,
        "iniciar-producao": lambda: comando_iniciar_producao(args.dry_run),
        "manutencao": comando_manutencao,
        "manutencao-producao": comando_manutencao_producao,
        "offline": comando_offline,
        "parar-producao": comando_parar_producao,
        "_worker-producao": _executar_worker_producao,
        "parar": comando_parar,
        "reiniciar": comando_reiniciar,
        "status": lambda: (imprimir_status() or 0),
        "comandos": comando_comandos,
        "painel": comando_painel,
        "simular": comando_simular,
        "publicar-um": comando_publicar_um,
        "coletar": comando_coletar,
        "coletar-confiavel": lambda: comando_coletar_confiavel(args.visual),
        "testar-captura-produto": lambda: comando_testar_captura_produto(args.argumentos),
        "comparar-captura": lambda: comando_testar_captura_produto(args.argumentos, comparar=True),
        "limpar-titulos": comando_limpar_titulos,
        "reprocessar-pendentes": lambda: comando_reprocessar_pendentes(args.dry_run),
        "simular-score": comando_simular_score,
        "atualizar-categorias": comando_atualizar_categorias,
        "calibrar-curadoria": comando_calibrar_curadoria,
        "reprocessar-pendentes-enriquecido": lambda: comando_reprocessar_pendentes_enriquecido(args.dry_run),
        "auditar-paginas-produto": comando_auditar_paginas_produto,
        "auditar-indisponiveis": comando_auditar_indisponiveis,
        "auditar-qualidade-catalogo": comando_auditar_qualidade_catalogo,
        "recuperar-indisponiveis": lambda: comando_recuperar_indisponiveis(args.dry_run),
        "corrigir-paginas-produto": comando_corrigir_paginas_produto,
        "gerar-site": comando_gerar_site,
        "validar": comando_validar,
        "servir-site": comando_servir_site,
        "publicar-site": comando_publicar_site,
        "subir-site": comando_subir_site,
        "publicar": comando_publicar,
        "relatorio": comando_relatorio,
        "relatorio-precos": comando_relatorio_precos,
        "monitorar-precos": comando_monitorar_precos,
        "perguntar": lambda: comando_perguntar(" ".join(args.argumentos)),
        "treinar-memoria": comando_treinar_memoria,
        "saude": comando_saude,
        "saude-detalhada": comando_saude_detalhada,
        "analytics-teste": comando_analytics_teste,
        "analytics-status": comando_analytics_status,
        "relatorio-operacional": comando_relatorio_operacional,
        "backup": comando_backup,
        "restaurar": comando_restaurar,
        "revisar-ofertas": comando_revisar_ofertas,
        "treinar-revisora": comando_treinar_revisora,
        "limpar-seguro": comando_limpar_seguro,
        "mapa": comando_mapa,
        "meli-auth": comando_meli_auth,
        "meli-testar-token": comando_meli_testar_token,
        "meli-refresh-token": comando_meli_refresh_token,
        "testar-coleta-api": lambda: comando_testar_coleta_api("playwright" in args.argumentos),
        "diagnosticar-playwright": comando_diagnosticar_playwright,
        "reparar-playwright": comando_reparar_playwright,
        "auditar-base": comando_auditar_base,
        "reconstruir-base": comando_reconstruir_base,
        "diagnosticar-afiliado": comando_diagnosticar_afiliado,
        "gerar-afiliados": comando_gerar_afiliados,
        "diagnosticar-compartilhar": lambda: comando_diagnosticar_compartilhar(args.argumentos),
        "testar-afiliado": lambda: comando_testar_afiliado(args.argumentos),
    }
    return comandos[args.comando]()


if __name__ == "__main__":
    raise SystemExit(main())
