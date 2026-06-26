"""Operação segura do painel remoto Promogg.

O painel remoto deve ficar atrás de Cloudflare Tunnel + Cloudflare Access.
Este módulo nunca abre porta pública: o Streamlit é iniciado apenas em
127.0.0.1 e a exposição externa deve ser feita pelo túnel autenticado.
"""

import json
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from banco import agora, conectar, inicializar_banco, obter_postagem, registrar_evento_sistema
from operacao_sistema import criar_backup_emergencia
from seguranca_publicacao import auditar_seguranca_publicacao


RELATORIO = Path("RELATORIO_PAINEL_REMOTO.md")
PAINEL_HOST = "127.0.0.1"
PAINEL_PORT = 8501
STATUS_OCULTO = "oculto_admin"


def _bool_env(nome, padrao=False):
    return os.getenv(nome, str(padrao).lower()).strip().lower() in {"1", "true", "sim", "yes", "on"}


def config_painel():
    load_dotenv(override=True)
    emails = [
        email.strip().lower()
        for email in os.getenv("PROMOGG_ADMIN_EMAILS", "").split(",")
        if email.strip()
    ]
    return {
        "remoto": _bool_env("PROMOGG_PAINEL_REMOTO", False),
        "auto_deploy": _bool_env("PROMOGG_PAINEL_AUTO_DEPLOY", False),
        "admin_emails": emails,
        "dominio": os.getenv("PROMOGG_PAINEL_DOMINIO", "painel.promogg.com.br").strip() or "painel.promogg.com.br",
        "host": os.getenv("PROMOGG_PAINEL_HOST", PAINEL_HOST).strip() or PAINEL_HOST,
        "port": int(os.getenv("PROMOGG_PAINEL_PORT", str(PAINEL_PORT)) or PAINEL_PORT),
    }


def _executar(args, timeout=180):
    proc = subprocess.run([sys.executable, "ia_promocoes.py", *args], capture_output=True, text=True, timeout=timeout)
    return {
        "comando": " ".join(["python3", "ia_promocoes.py", *args]),
        "codigo": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-4000:],
        "stderr": (proc.stderr or "").strip()[-2000:],
    }


def auditar_painel_remoto():
    cfg = config_painel()
    achados = []
    avisos = []
    if cfg["host"] != "127.0.0.1":
        achados.append("PROMOGG_PAINEL_HOST deve ser 127.0.0.1; não exponha Streamlit diretamente.")
    if not cfg["remoto"]:
        avisos.append("PROMOGG_PAINEL_REMOTO=false; comando real não iniciará o painel remoto até habilitação explícita.")
    if not cfg["admin_emails"]:
        avisos.append("PROMOGG_ADMIN_EMAILS não configurado; preencha com seu e-mail antes de ativar acesso remoto.")
    if cfg["remoto"] and not cfg["admin_emails"]:
        achados.append("PROMOGG_ADMIN_EMAILS precisa listar ao menos um e-mail autorizado.")
    if cfg["remoto"] and cfg["dominio"] != "painel.promogg.com.br":
        avisos.append(f"Domínio configurado diferente do padrão esperado: {cfg['dominio']}")
    if not Path(".env").exists():
        avisos.append(".env local não encontrado; painel remoto deve ser configurado só em ambiente local seguro.")
    if not Path("painel.py").exists():
        achados.append("painel.py não encontrado.")
    seguranca = auditar_seguranca_publicacao()
    if seguranca.get("critico") or seguranca.get("bloqueante"):
        achados.append("auditoria de segurança de publicação possui crítico/bloqueante.")
    resultado = {
        "gerado_em": agora(),
        "config": {**cfg, "admin_emails": ["[configurado]"] if cfg["admin_emails"] else []},
        "achados": achados,
        "avisos": avisos,
        "seguranca_publicacao": seguranca.get("status_final"),
        "aprovado": not achados,
        "cloudflare_access_requerido": True,
        "comando_tunnel_sugerido": f"cloudflared tunnel --url http://127.0.0.1:{cfg['port']} --hostname {cfg['dominio']}",
    }
    _escrever_relatorio(resultado)
    return resultado


def _escrever_relatorio(resultado):
    linhas = [
        "# Relatório do Painel Remoto Promogg",
        "",
        f"- Gerado em: {resultado['gerado_em']}",
        f"- Aprovado: {resultado['aprovado']}",
        f"- Domínio esperado: {resultado['config']['dominio']}",
        f"- Host local: {resultado['config']['host']}",
        f"- Porta local: {resultado['config']['port']}",
        f"- Remoto habilitado: {resultado['config']['remoto']}",
        f"- Auto deploy painel: {resultado['config']['auto_deploy']}",
        f"- Admin emails configurados: {'sim' if resultado['config']['admin_emails'] else 'não'}",
        "",
        "## Arquitetura recomendada",
        "- `promogg.com.br`: site público estático.",
        "- `painel.promogg.com.br`: Cloudflare Tunnel apontando para `127.0.0.1:8501`.",
        "- Cloudflare Access: login Google e política Allow apenas para `PROMOGG_ADMIN_EMAILS`.",
        "- Não abrir porta pública no roteador.",
        "- Não expor Streamlit sem Cloudflare Access.",
        "",
        "## Achados bloqueantes",
    ]
    linhas += [f"- {a}" for a in resultado["achados"]] or ["- nenhum"]
    linhas += ["", "## Avisos"]
    linhas += [f"- {a}" for a in resultado["avisos"]] or ["- nenhum"]
    linhas += [
        "",
        "## Comando de túnel sugerido",
        f"- `{resultado['comando_tunnel_sugerido']}`",
        "",
        "## Checklist Cloudflare Access",
        "- Criar aplicação Self-hosted em Cloudflare Zero Trust.",
        "- Domínio: `painel.promogg.com.br`.",
        "- Session duration curta/moderada.",
        "- Identity provider: Google.",
        "- Policy Allow: somente os e-mails em `PROMOGG_ADMIN_EMAILS`.",
        "- Policy default: deny.",
    ]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def iniciar_painel_remoto(dry_run=True):
    auditoria = auditar_painel_remoto()
    cfg = config_painel()
    python_exec = str(Path("venv/bin/python")) if Path("venv/bin/python").exists() else sys.executable
    cmd = [
        python_exec,
        "-m",
        "streamlit",
        "run",
        "painel.py",
        "--server.address",
        cfg["host"],
        "--server.port",
        str(cfg["port"]),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    resultado = {
        "dry_run": dry_run,
        "auditoria": auditoria,
        "comando_streamlit": " ".join(shlex.quote(parte) for parte in cmd),
        "iniciado": False,
    }
    if dry_run:
        return resultado
    if not auditoria["aprovado"]:
        raise RuntimeError("Painel remoto bloqueado pela auditoria.")
    if not cfg["remoto"]:
        raise RuntimeError("PROMOGG_PAINEL_REMOTO=false; habilite explicitamente para iniciar.")
    Path("logs").mkdir(exist_ok=True)
    log = (Path("logs") / "painel_remoto.log").open("a", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    Path(".promogg_painel.pid").write_text(str(proc.pid), encoding="utf-8")
    registrar_evento_sistema("painel_remoto", "painel", "sucesso", "Painel remoto iniciado localmente", f"pid={proc.pid}; host={cfg['host']}; port={cfg['port']}")
    resultado["iniciado"] = True
    resultado["pid"] = proc.pid
    return resultado


def publicar_alteracoes_painel(auto=False):
    passos = []
    passos.append(_executar(["gerar-site"]))
    passos.append(_executar(["preparar-publicacao"]))
    passos.append(_executar(["validar", "--somente-leitura"]))
    passos.append(_executar(["auditar-seguranca-publicacao"]))
    ok = all(p["codigo"] == 0 for p in passos)
    deploy = None
    if ok and (auto or config_painel()["auto_deploy"]):
        deploy = _executar(["subir-site"], timeout=300)
        passos.append(deploy)
        ok = deploy["codigo"] == 0
    registrar_evento_sistema(
        "painel_publicacao",
        "painel",
        "sucesso" if ok else "erro",
        "Publicação de alterações do painel concluída" if ok else "Publicação de alterações do painel bloqueada",
        "; ".join(f"{p['comando']}={p['codigo']}" for p in passos),
    )
    return {"ok": ok, "auto_deploy": auto or config_painel()["auto_deploy"], "passos": passos}


def _status_anterior(postagem):
    obs = str(postagem.get("observacao_interna") or "")
    marcador = "status_anterior="
    if marcador in obs:
        return obs.split(marcador, 1)[1].split(";", 1)[0].strip()
    status = str(postagem.get("status") or "").strip()
    return "pendente_revisao" if status in {"oculto_admin", "removido_painel"} else status


def ocultar_oferta(postagem_id, ator="painel_admin"):
    from controle_ofertas import sincronizar_postagem_csv

    inicializar_banco()
    postagem = obter_postagem(postagem_id)
    if not postagem:
        raise ValueError("Oferta não encontrada")
    backup = criar_backup_emergencia()
    status_antigo = str(postagem.get("status") or "")
    obs_antiga = str(postagem.get("observacao_interna") or "")
    obs = f"{obs_antiga}; status_anterior={status_antigo}; ocultado_em={agora()}; ator={ator}".strip("; ")
    data = agora()
    with conectar() as conn:
        conn.execute(
            "UPDATE postagens SET status=?, observacao_interna=?, atualizado_em=? WHERE id=?",
            (STATUS_OCULTO, obs, data, postagem_id),
        )
    atualizada = obter_postagem(postagem_id)
    sincronizar_postagem_csv(atualizada)
    registrar_evento_sistema("painel_admin", ator, "sucesso", "Oferta ocultada do site", f"postagem={postagem_id}; backup={Path(backup).name}")
    publicacao = publicar_alteracoes_painel()
    return {"postagem": atualizada, "backup": str(backup), "publicacao": publicacao}


def restaurar_oferta(postagem_id, ator="painel_admin"):
    from controle_ofertas import sincronizar_postagem_csv

    inicializar_banco()
    postagem = obter_postagem(postagem_id)
    if not postagem:
        raise ValueError("Oferta não encontrada")
    backup = criar_backup_emergencia()
    destino = _status_anterior(postagem)
    if destino in {"oculto_admin", "removido_painel", ""}:
        destino = "pendente_revisao"
    data = agora()
    obs = f"{postagem.get('observacao_interna') or ''}; restaurado_em={data}; ator={ator}".strip("; ")
    with conectar() as conn:
        conn.execute(
            "UPDATE postagens SET status=?, observacao_interna=?, atualizado_em=? WHERE id=?",
            (destino, obs, data, postagem_id),
        )
    atualizada = obter_postagem(postagem_id)
    sincronizar_postagem_csv(atualizada)
    registrar_evento_sistema("painel_admin", ator, "sucesso", "Oferta restaurada pelo painel", f"postagem={postagem_id}; status={destino}; backup={Path(backup).name}")
    publicacao = publicar_alteracoes_painel()
    return {"postagem": atualizada, "backup": str(backup), "publicacao": publicacao}
