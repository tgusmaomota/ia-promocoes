import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from banco import STATUS_CONTROLE, inicializar_banco, listar_postagens, resumo, resumo_cliques
from controle_ofertas import aprovar_manual, editar_oferta, rejeitar_oferta
from promogg_assistente import responder_pergunta, salvar_feedback, ultimas_perguntas
from saude_sistema import obter_relatorio_saude
from gerar_site import resumo_seo_publico
from ia_revisora import listar_revisoes_pendentes, registrar_feedback as registrar_feedback_revisora
from estado_sistema import obter_estado_sistema
from gerador_afiliados_oficial import produtos_sem_afiliado


st.set_page_config(page_title="Promogg | Controle de ofertas", layout="wide")
if Path("site/logo.png").exists():
    st.image("site/logo.png", width=150)
st.title("Controle de ofertas")
st.caption("Aprovação, edição e publicação usam o SQLite como fonte de verdade.")

inicializar_banco()
estado_mestre = obter_estado_sistema()
if estado_mestre["estado"] == "MANUTENCAO":
    st.warning("Sistema em manutenção: automações estão pausadas; edição, banco e consultas locais permanecem disponíveis.")
elif estado_mestre["estado"] == "OFFLINE":
    st.error("Sistema offline: serviços automatizados estão parados. Dados locais permanecem preservados.")
else:
    st.success("Sistema online: automações habilitadas.")
ofertas = pd.DataFrame(listar_postagens())
if ofertas.empty:
    ofertas = pd.DataFrame(columns=[
        "id", "titulo", "preco", "link_afiliado", "imagem_url", "categoria", "texto_post",
        "preco_original", "desconto_percentual", "economia_valor",
        "status", "observacao_interna", "aprovado_por", "aprovado_em",
        "data_criacao", "data_publicacao",
    ])


def executar(comando):
    resultado = subprocess.run([sys.executable, *comando], capture_output=True, text=True)
    if resultado.stdout:
        st.code(resultado.stdout)
    if resultado.returncode != 0 or resultado.stderr:
        st.error(resultado.stderr or "Comando encerrou com erro.")
    else:
        st.success("Operação concluída.")


def quantidade(status):
    return int((ofertas["status"] == status).sum()) if "status" in ofertas else 0


dados = resumo()
metricas = st.columns(5)
for coluna, titulo, valor in zip(metricas, [
    "Pendentes", "Aprovadas auto", "Aprovadas manual", "Rejeitadas", "Publicadas",
], [
    quantidade("pendente_revisao"), quantidade("aprovado_auto"), quantidade("aprovado_manual"),
    quantidade("rejeitado"), quantidade("publicado"),
]):
    coluna.metric(titulo, valor)

analytics = resumo_cliques()
st.subheader("Analytics de cliques")
analytics_colunas = st.columns(2)
with analytics_colunas[0]:
    st.caption("Top 20 produtos mais clicados")
    st.dataframe(pd.DataFrame(analytics["produtos"]), use_container_width=True, hide_index=True)
with analytics_colunas[1]:
    st.caption("Top categorias")
    categorias_cliques = pd.DataFrame(analytics["categorias"])
    if categorias_cliques.empty:
        st.info("Ainda não há cliques registrados.")
    else:
        st.bar_chart(categorias_cliques.set_index("categoria"))

tempo_cliques = st.columns(2)
with tempo_cliques[0]:
    st.caption("Cliques por dia")
    dias_cliques = pd.DataFrame(analytics["dias"])
    if not dias_cliques.empty:
        st.line_chart(dias_cliques.set_index("periodo"))
with tempo_cliques[1]:
    st.caption("Cliques por mês")
    meses_cliques = pd.DataFrame(analytics["meses"])
    if not meses_cliques.empty:
        st.bar_chart(meses_cliques.set_index("periodo"))

st.divider()
acoes = st.columns(4)
with acoes[0]:
    if st.button("Atualizar site agora", use_container_width=True):
        executar(["ia_promocoes.py", "gerar-site"])
with acoes[1]:
    if st.button("Publicar 1 no Telegram", use_container_width=True):
        executar(["ia_promocoes.py", "publicar-um"])
with acoes[2]:
    if st.button("Simular próxima publicação", use_container_width=True):
        executar(["ia_promocoes.py", "simular"])
with acoes[3]:
    if st.button("Rodar coleta", use_container_width=True):
        executar(["ia_promocoes.py", "coletar"])

reprocessamento = st.columns(2)
with reprocessamento[0]:
    if st.button("Simular reprocessamento", use_container_width=True):
        executar(["ia_promocoes.py", "reprocessar-pendentes", "--dry-run"])
with reprocessamento[1]:
    if st.button("Reprocessar pendentes", use_container_width=True):
        executar(["ia_promocoes.py", "reprocessar-pendentes"])

st.subheader("Filas de aprovação")
with st.expander("Produtos sem afiliado", expanded=False):
    pendentes_afiliado = pd.DataFrame(produtos_sem_afiliado())
    if pendentes_afiliado.empty:
        st.success("Não há produtos pendentes de link afiliado.")
    else:
        st.dataframe(
            pendentes_afiliado[[coluna for coluna in ("item_id", "titulo", "link_original") if coluna in pendentes_afiliado]],
            use_container_width=True,
            hide_index=True,
        )
        if st.button("Gerar links afiliados", use_container_width=True):
            executar(["ia_promocoes.py", "gerar-afiliados"])
abas = st.tabs([
    "Pendentes de revisão",
    "Aprovadas automaticamente",
    "Aprovadas manualmente",
    "Rejeitadas",
    "Publicadas",
    "Assistente de Preços",
    "Saúde do Sistema",
    "SEO",
    "IA Revisora",
])
for aba, status_aba in zip(abas[:5], [
    "pendente_revisao", "aprovado_auto", "aprovado_manual", "rejeitado", "publicado",
]):
    with aba:
        itens = ofertas[ofertas["status"] == status_aba]
        if status_aba == "pendente_revisao" and "score_curadoria" in itens:
            itens = itens.sort_values("score_curadoria", ascending=False, na_position="last")
        if itens.empty:
            st.info("Nenhuma oferta nesta fila.")
        else:
            st.dataframe(itens[[coluna for coluna in [
                "id", "titulo", "preco", "categoria", "aprovado_por",
                "score_curadoria", "categoria_caminho", "desconto_percentual", "economia_valor",
                "selo_mais_vendido", "selo_loja_oficial", "avaliacao", "quantidade_vendida",
                "aprovado_em", "data_criacao", "data_publicacao",
            ] if coluna in itens]], use_container_width=True)

with abas[5]:
    st.caption("Consulta somente leitura baseada no SQLite local. Ollama é opcional e tem fallback por regras.")
    pergunta_assistente = st.text_input(
        "Pergunte sobre preços",
        placeholder="Qual foi o menor preço do PS5?",
        key="pergunta_assistente",
    )
    if st.button("Perguntar", key="perguntar_assistente"):
        try:
            st.session_state["resposta_assistente"] = responder_pergunta(pergunta_assistente)
        except Exception:
            st.warning("Não foi possível consultar os dados locais agora. Tente novamente mais tarde.")

    resposta_assistente = st.session_state.get("resposta_assistente")
    if resposta_assistente:
        st.text(resposta_assistente["texto"])
        relacionados = pd.DataFrame(resposta_assistente.get("produtos", []))
        if not relacionados.empty:
            colunas_relacionadas = [
                coluna for coluna in ("item_id", "titulo", "preco_atual", "menor_preco", "categoria", "categoria_nome")
                if coluna in relacionados
            ]
            if colunas_relacionadas:
                st.dataframe(relacionados[colunas_relacionadas], use_container_width=True, hide_index=True)

        observacao_feedback = st.text_input("Observação sobre a resposta", key="observacao_feedback_assistente")
        feedback_colunas = st.columns(2)
        for coluna, rotulo, valor in (
            (feedback_colunas[0], "Resposta útil", "util"),
            (feedback_colunas[1], "Resposta não útil", "nao_util"),
        ):
            with coluna:
                if st.button(rotulo, key=f"feedback_assistente_{valor}"):
                    try:
                        salvar_feedback(resposta_assistente.get("pergunta_id"), valor, observacao_feedback)
                        st.success("Feedback salvo localmente.")
                    except (TypeError, ValueError):
                        st.warning("Faça uma nova pergunta antes de enviar feedback.")

    st.caption("Sugestões: menor preço do PS5, preço atual do Xbox, produtos no menor preço histórico, categorias com mais ofertas.")
    st.caption("Últimas perguntas locais")
    historico_assistente = pd.DataFrame(ultimas_perguntas(10))
    if historico_assistente.empty:
        st.info("Ainda não há perguntas registradas.")
    else:
        st.dataframe(
            historico_assistente[[coluna for coluna in ("criado_em", "pergunta", "modo_resposta", "modelo") if coluna in historico_assistente]],
            use_container_width=True,
            hide_index=True,
        )

with abas[6]:
    try:
        saude = obter_relatorio_saude()
        status_geral = saude["status_geral"]
        if status_geral == "OK":
            st.success("Sistema geral: OK")
        elif status_geral == "Atenção":
            st.warning("Sistema geral: Atenção")
        else:
            st.error("Sistema geral: Erro")

        cards_saude = [
            ("Sistema geral", status_geral),
            ("Última coleta", saude["ultima_coleta"]),
            ("Última atualização de preços", saude["ultima_atualizacao_precos"]),
            ("Último monitoramento", saude["ultimo_monitoramento"]),
            ("Último site gerado", saude["ultimo_site_gerado"]),
            ("Último deploy", saude["ultimo_deploy"]),
            ("Último Telegram", saude["ultimo_telegram"]),
            ("Analytics", saude.get("analytics_situacao", saude["ultimo_analytics"])),
            ("Última IA consultiva", saude["ultima_ia_consultiva"]),
            ("Banco SQLite", saude["integridade_banco"]),
            ("Erros 24h", len(saude["erros_24h"])),
            ("Ofertas monitoradas", saude["ofertas_monitoradas"]),
            ("Pendentes de revisão", saude["ofertas_pendentes"]),
        ]
        for inicio in range(0, len(cards_saude), 3):
            colunas_saude = st.columns(3)
            for coluna, (titulo, valor) in zip(colunas_saude, cards_saude[inicio:inicio + 3]):
                coluna.metric(titulo, valor)

        st.subheader("Situações que exigem atenção")
        if not saude["alertas"]:
            st.success("Nenhum alerta operacional.")
        for alerta in saude["alertas"]:
            if alerta["nivel"] == "critico":
                st.error(alerta["mensagem"])
            elif alerta["nivel"] == "alerta":
                st.warning(alerta["mensagem"])
            else:
                st.info(alerta["mensagem"])

        secoes_saude = (
            ("Erros críticos", "critico"),
            ("Erros operacionais", "erro"),
            ("Alertas", "alerta"),
            ("Avisos", "aviso"),
            ("Eventos informativos", "info"),
        )
        for titulo, nivel in secoes_saude:
            st.subheader(titulo)
            eventos_nivel = pd.DataFrame(saude.get("eventos_classificados", {}).get(nivel, []))
            if eventos_nivel.empty:
                st.caption("Nenhum registro recente.")
            else:
                st.dataframe(eventos_nivel, use_container_width=True, hide_index=True)

        st.subheader("Eventos recentes")
        eventos_saude = pd.DataFrame(saude["eventos_recentes"])
        if eventos_saude.empty:
            st.info("Sem eventos registrados ainda.")
        else:
            st.dataframe(eventos_saude, use_container_width=True, hide_index=True)
    except Exception:
        st.warning("Não foi possível carregar a saúde agora. Os demais controles continuam disponíveis.")

with abas[7]:
    try:
        seo = resumo_seo_publico()
        colunas_seo = st.columns(3)
        colunas_seo[0].metric("Páginas indexáveis", seo["paginas_indexaveis"])
        colunas_seo[1].metric("Produtos indexáveis", seo["produtos_indexaveis"])
        colunas_seo[2].metric("Categorias indexáveis", seo["categorias_indexaveis"])
        if seo["sitemap_gerado"]:
            st.success("Sitemap gerado e pronto para envio ao Search Console.")
        else:
            st.warning("Sitemap ainda não foi gerado. Rode Atualizar site agora.")
        if seo["robots_valido"]:
            st.success("robots.txt permite indexação pública e informa o sitemap.")
        else:
            st.warning("robots.txt ainda não está válido.")
    except Exception:
        st.warning("Não foi possível carregar o resumo de SEO agora.")

with abas[8]:
    st.caption("A IA revisora sugere ações com base em dados locais. Ela não altera aprovações sozinha.")
    if st.button("Analisar ofertas pendentes", use_container_width=True, key="revisar_ofertas"):
        executar(["ia_promocoes.py", "revisar-ofertas"])
        st.rerun()
    try:
        revisoes = listar_revisoes_pendentes()
        if not revisoes:
            st.info("Não há ofertas pendentes analisadas. Use o botão para analisar a fila atual.")
        for revisao in revisoes:
            with st.expander(f"{revisao['titulo']} | {revisao['score_revisora']:.1f}/100 | {revisao['sugestao']}"):
                st.caption(f"Curadoria: {revisao.get('score_curadoria', 0)} | Modo: {revisao['modo_resposta']} | Atualizada: {revisao['atualizado_em']}")
                st.text(revisao["parecer"])
                acoes_revisora = st.columns(3)
                with acoes_revisora[0]:
                    if st.button("Aprovar", key=f"revisora_aprovar_{revisao['postagem_id']}"):
                        aprovar_manual(revisao["postagem_id"], "Decisão após parecer da IA revisora", ator="painel_revisora")
                        registrar_feedback_revisora(revisao["item_id"], revisao["sugestao"], "Aprovar")
                        st.success("Oferta aprovada manualmente e feedback salvo.")
                        st.rerun()
                with acoes_revisora[1]:
                    if st.button("Rejeitar", key=f"revisora_rejeitar_{revisao['postagem_id']}"):
                        rejeitar_oferta(revisao["postagem_id"], "Decisão após parecer da IA revisora", ator="painel_revisora")
                        registrar_feedback_revisora(revisao["item_id"], revisao["sugestao"], "Rejeitar")
                        st.success("Oferta rejeitada manualmente e feedback salvo.")
                        st.rerun()
                with acoes_revisora[2]:
                    if st.button("Revisar", key=f"revisora_revisar_{revisao['postagem_id']}"):
                        registrar_feedback_revisora(revisao["item_id"], revisao["sugestao"], "Revisar manualmente")
                        st.info("Feedback salvo; a oferta continua pendente de revisão.")
    except Exception:
        st.warning("Não foi possível carregar a IA revisora agora. As decisões manuais continuam disponíveis.")

st.subheader("Buscar e editar")
status_filtro = st.multiselect(
    "Status", list(STATUS_CONTROLE), default=list(STATUS_CONTROLE),
)
busca = st.text_input("Buscar por título")
filtradas = ofertas[ofertas["status"].isin(status_filtro)].copy()
if busca:
    filtradas = filtradas[filtradas["titulo"].str.contains(busca, case=False, na=False)]

colunas_tabela = [
    "id", "titulo", "preco", "categoria", "status", "aprovado_por",
    "aprovado_em", "data_criacao", "data_publicacao",
]
st.dataframe(filtradas[[coluna for coluna in colunas_tabela if coluna in filtradas]], use_container_width=True)

if filtradas.empty:
    st.info("Nenhuma oferta para os filtros selecionados.")
    st.stop()

opcoes = {
    int(linha["id"]): f"#{linha['id']} | {linha['status']} | {linha['titulo'][:72]}"
    for _, linha in filtradas.iterrows()
}
postagem_id = st.selectbox("Selecionar oferta", list(opcoes), format_func=opcoes.get)
postagem = ofertas[ofertas["id"] == postagem_id].iloc[0].to_dict()

if postagem.get("item_id") and postagem.get("status") in {"aprovado_auto", "aprovado_manual", "publicado"}:
    st.link_button(
        "Abrir página do produto",
        f"https://promogg.com.br/produto/{postagem['item_id']}/",
    )

st.subheader("Editar oferta")
with st.form(f"editar_{postagem_id}"):
    titulo = st.text_input("Título", value=str(postagem.get("titulo", "")))
    preco = st.number_input("Preço", min_value=0.01, value=float(postagem.get("preco") or 0.01), step=0.01)
    preco_original = postagem.get("preco_original")
    desconto = postagem.get("desconto_percentual")
    if preco_original:
        st.caption(f"Preço original: R$ {float(preco_original):.2f}")
    if desconto:
        st.caption(f"Desconto: {float(desconto):.1f}%")
    categoria = st.text_input("Categoria", value=str(postagem.get("categoria", "ofertas")))
    link = st.text_input("Link afiliado", value=str(postagem.get("link_afiliado", "")))
    imagem_url = st.text_input("URL pública da imagem", value=str(postagem.get("imagem_url", "")))
    if imagem_url:
        st.image(imagem_url, width=180)
    status = st.selectbox("Status", list(STATUS_CONTROLE), index=list(STATUS_CONTROLE).index(postagem["status"]))
    texto = st.text_area("Texto do post", value=str(postagem.get("texto_post", "")), height=180)
    observacao = st.text_area("Observação interna", value=str(postagem.get("observacao_interna", "")), height=100)
    salvar = st.form_submit_button("Salvar edição", use_container_width=True)

if salvar:
    try:
        editar_oferta(postagem_id, {
            "titulo": titulo,
            "preco": preco,
            "categoria": categoria,
            "link_afiliado": link,
            "imagem_url": imagem_url,
            "texto_post": texto,
            "status": status,
            "observacao_interna": observacao,
        })
        st.success("Oferta salva no SQLite e sincronizada no CSV.")
        st.rerun()
    except ValueError as erro:
        st.error(str(erro))

decisao = st.columns(2)
with decisao[0]:
    if st.button("Aprovar manualmente", use_container_width=True):
        try:
            aprovar_manual(postagem_id, observacao)
            st.success("Oferta aprovada manualmente.")
            st.rerun()
        except ValueError as erro:
            st.error(str(erro))
with decisao[1]:
    if st.button("Rejeitar", use_container_width=True):
        try:
            rejeitar_oferta(postagem_id, observacao)
            st.success("Oferta rejeitada.")
            st.rerun()
        except ValueError as erro:
            st.error(str(erro))

st.caption(f"Produtos coletados no banco: {dados['produtos']} | Fila aprovada: {dados['fila_pendente']}")
