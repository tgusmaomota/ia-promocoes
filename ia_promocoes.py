import argparse
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from banco import conectar, inicializar_banco, migrar_csvs, registrar_log, resumo
from deploy_site import copiar_site
from gerar_site import gerar_site
from servidor_site import servir_site


PID_FILE = Path(".ia_promocoes.pid")
STOP_FILE = Path(".ia_promocoes.stop")


load_dotenv()


def processo_ativo(pid):
    try:
        os.kill(pid, 0)
        return True
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


def comando_iniciar():
    from publicador_telegram import gerar_site_local, gerar_whatsapp_manual
    from scheduler import ciclo_completo, inteiro_env

    pid = robo_rodando()
    if pid:
        print(f"IA-Promocoes já está rodando. PID: {pid}")
        return 0

    STOP_FILE.unlink(missing_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    intervalo = inteiro_env("INTERVALO_COLETA_MINUTOS", 30)

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
            except Exception as erro:
                registrar_log("operacao", f"Erro no ciclo automático: {erro}", nivel="error")

            if not esperar_com_parada(intervalo * 60):
                break
    finally:
        registrar_log("operacao", "Robô parado com segurança")
        PID_FILE.unlink(missing_ok=True)
        STOP_FILE.unlink(missing_ok=True)

    return 0


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


def imprimir_status():
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

    print("Status IA-Promocoes")
    print(f"Robô: {'rodando' if pid else 'parado'}" + (f" (PID {pid})" if pid else ""))
    print(f"Pendentes: {dados['fila_pendente']}")
    print(f"Publicados hoje: {publicados_hoje or 0}")
    print(f"Última coleta: {ultima_coleta or 'sem registro'}")
    print(f"Última publicação: {ultima_publicacao or 'sem registro'}")

    erros = logs_recentes("error", 5)
    if erros:
        print("\nErros recentes:")
        for erro in erros:
            print(f"- {erro['criado_em']} [{erro['etapa']}] {erro['mensagem']}")
    else:
        print("\nErros recentes: nenhum")


def comando_coletar():
    from publicador_telegram import gerar_site_local, gerar_whatsapp_manual
    from scheduler import ciclo_completo

    preparar_base(migrar=True)
    ciclo_completo(publicar=False)
    gerar_site_local()
    gerar_whatsapp_manual()
    return 0


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
    return subprocess.call([sys.executable, "-m", "streamlit", "run", "painel.py"])


def comando_gerar_site():
    from publicador_telegram import gerar_whatsapp_manual

    preparar_base()
    resultado = gerar_site()
    gerar_whatsapp_manual()
    print(f"Site gerado em site/ com {resultado['ofertas']} ofertas.")
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


def comando_subir_site():
    from publicar_site_git import DOMINIO, subir_site

    preparar_base()

    try:
        resultado = subir_site()
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


def comando_relatorio():
    preparar_base()
    hoje = date.today().strftime("%Y-%m-%d")

    with conectar() as conn:
        coletados = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
        aprovados = conn.execute("SELECT COUNT(*) FROM promocoes WHERE status = 'aprovado'").fetchone()[0]
        rejeitados = conn.execute("SELECT COUNT(*) FROM promocoes WHERE status = 'rejeitado'").fetchone()[0]
        publicados = conn.execute("SELECT COUNT(*) FROM postagens WHERE status = 'publicado'").fetchone()[0]
        pendentes = conn.execute("SELECT COUNT(*) FROM postagens WHERE status = 'pendente'").fetchone()[0]
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


def main():
    parser = argparse.ArgumentParser(description="Operação final do IA-Promocoes")
    parser.add_argument(
        "comando",
        choices=[
            "iniciar",
            "parar",
            "status",
            "painel",
            "simular",
            "publicar-um",
            "coletar",
            "gerar-site",
            "servir-site",
            "publicar-site",
            "subir-site",
            "relatorio",
        ],
    )
    args = parser.parse_args()

    comandos = {
        "iniciar": comando_iniciar,
        "parar": comando_parar,
        "status": lambda: (imprimir_status() or 0),
        "painel": comando_painel,
        "simular": comando_simular,
        "publicar-um": comando_publicar_um,
        "coletar": comando_coletar,
        "gerar-site": comando_gerar_site,
        "servir-site": comando_servir_site,
        "publicar-site": comando_publicar_site,
        "subir-site": comando_subir_site,
        "relatorio": comando_relatorio,
    }
    return comandos[args.comando]()


if __name__ == "__main__":
    raise SystemExit(main())
