import argparse
import os
import time

from dotenv import load_dotenv

from banco import inicializar_banco, migrar_csvs, registrar_log
from estado_sistema import automacao_ativa
from coletor_mercadolivre import coletar as coletar_mercadolivre
from fila_postagens import gerar_fila_de_produtos
from monitor_precos import monitorar_precos_diariamente
from publicador_telegram import publicar_proximo, publicar_um


load_dotenv()


def inteiro_env(nome, padrao):
    try:
        return int(os.getenv(nome, str(padrao)))
    except ValueError:
        return padrao


def ciclo_completo(publicar=False):
    if not automacao_ativa():
        registrar_log("scheduler", "Ciclo automático pausado pelo estado mestre", nivel="warning")
        return {"pausado": True}
    inicializar_banco()
    migrar_csvs()

    registrar_log("scheduler", "Iniciando ciclo completo")

    produtos_ml = coletar_mercadolivre()

    resultado_fila = gerar_fila_de_produtos()
    resultado_monitoramento = monitorar_precos_diariamente()

    publicado = False
    if publicar:
        publicado = publicar_proximo()

    registrar_log(
        "scheduler",
        (
            "Ciclo finalizado. "
            f"mercado_livre={len(produtos_ml)} "
            f"fila_aprovados={resultado_fila['aprovados']} "
            f"monitorados={resultado_monitoramento.get('verificados', 0)} "
            f"fila_rejeitados={resultado_fila['rejeitados']} publicado={publicado}"
        ),
    )


def loop_24h():
    intervalo_coleta = inteiro_env("INTERVALO_COLETA_MINUTOS", 30)
    registrar_log("scheduler", f"Robô 24h iniciado. intervalo_coleta={intervalo_coleta}min")

    while True:
        try:
            ciclo_completo(publicar=False)
        except Exception as erro:
            registrar_log("scheduler", f"Erro no ciclo: {erro}", nivel="error")

        time.sleep(intervalo_coleta * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Executa um ciclo e encerra")
    parser.add_argument("--publicar", action="store_true", help="Publica o próximo post após gerar a fila")
    parser.add_argument("--publicar-um", action="store_true", help="Publica apenas 1 post pendente")
    parser.add_argument("--dry-run", action="store_true", help="Simula a publicação sem enviar Telegram")
    parser.add_argument(
        "--sem-publicar",
        action="store_true",
        help="Compatibilidade: executa sem publicar no Telegram",
    )
    args = parser.parse_args()

    if args.publicar_um:
        publicar_um(dry_run=args.dry_run)
    elif args.once:
        ciclo_completo(publicar=args.publicar and not args.sem_publicar)
    else:
        loop_24h()


if __name__ == "__main__":
    main()
