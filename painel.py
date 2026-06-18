import streamlit as st
import pandas as pd
import subprocess
import os
import sys
from datetime import datetime
from gerador_texto import gerar_post
from schema_posts import garantir_arquivo_posts, ler_posts, salvar_posts
from banco import inicializar_banco, listar_postagens, resumo

ARQUIVO_POSTS = "posts_prontos.csv"
ARQUIVO_PRODUTOS = "produtos.csv"

st.title("Painel de Promoções")

garantir_arquivo_posts(ARQUIVO_POSTS)
inicializar_banco()

if not os.path.exists(ARQUIVO_PRODUTOS):
    pd.DataFrame(
        columns=["titulo", "preco", "link", "categoria"]
    ).to_csv(ARQUIVO_PRODUTOS, index=False)

st.subheader("Adicionar novo produto")

novo_titulo = st.text_input("Título do produto")
novo_preco = st.number_input("Preço", min_value=0.0, step=1.0)
novo_link = st.text_input("Link afiliado meli.la")

nova_categoria = st.selectbox(
    "Categoria",
    ["casa", "eletrônicos", "moda", "beleza", "mercado", "colecionáveis", "outros"]
)

if st.button("Adicionar produto"):

    if not novo_titulo or not novo_link or novo_preco <= 0:
        st.error("Preencha título, preço e link antes de adicionar.")

    else:
        df_existente = ler_posts(ARQUIVO_POSTS)

        if novo_link in df_existente["link"].values:
            st.error("Este produto já foi cadastrado.")

        else:
            produto = {
                "titulo": novo_titulo,
                "preco": novo_preco,
                "link": novo_link,
                "categoria": nova_categoria
            }

            novo = pd.DataFrame([produto])
            novo.to_csv(
                ARQUIVO_PRODUTOS,
                mode="a",
                header=False,
                index=False
            )

            post = gerar_post(produto)

            novo_post = pd.DataFrame([{
                "titulo": novo_titulo,
                "item_id": "",
                "preco": novo_preco,
                "link": novo_link,
                "categoria": nova_categoria,
                "imagem": "",
                "post": post,
                "status": "pendente",
                "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "log_aprovacao": (
                    "Pendente: item sem confiança suficiente: "
                    "produto manual sem score, desconto e validação de preço"
                ),
                "status_telegram": ""
            }])

            df_atualizado = pd.concat([df_existente, novo_post], ignore_index=True)
            salvar_posts(df_atualizado, ARQUIVO_POSTS)

            st.success("Produto adicionado e post gerado.")
            st.rerun()

df = ler_posts(ARQUIVO_POSTS)
resumo_banco = resumo()
df_fila = pd.DataFrame(listar_postagens())

if df_fila.empty:
    df_fila = pd.DataFrame(
        columns=[
            "id",
            "titulo",
            "preco",
            "link_afiliado",
            "plataforma",
            "categoria",
            "status",
            "data_criacao",
            "data_publicacao",
        ]
    )

st.subheader("Resumo")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Produtos coletados", resumo_banco["produtos"])

with col2:
    st.metric("Promoções aprovadas", resumo_banco["promocoes_aprovadas"])

with col3:
    st.metric("Posts publicados", resumo_banco["posts_publicados"])

with col4:
    st.metric("Fila pendente", resumo_banco["fila_pendente"])

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("CSV pendentes", len(df[df["status"] == "pendente"]))

with col2:
    st.metric("CSV aprovados", len(df[df["status"] == "aprovado"]))

with col3:
    st.metric("CSV rejeitados", len(df[df["status"] == "rejeitado"]))

st.subheader("Dashboard")

if not df.empty:
    resumo_categoria = (
        df.groupby("categoria")
        .size()
        .reset_index(name="quantidade")
    )

    st.write("Posts por categoria")
    st.bar_chart(resumo_categoria.set_index("categoria"))

    resumo_status = (
        df.groupby("status")
        .size()
        .reset_index(name="quantidade")
    )

    st.write("Posts por status")
    st.bar_chart(resumo_status.set_index("status"))

    st.subheader("Ranking de Categorias")

    st.dataframe(
        resumo_categoria.sort_values("quantidade", ascending=False),
        use_container_width=True
    )
else:
    st.info("Ainda não existem posts cadastrados.")

st.subheader("Filtros")

plataformas = ["Todas", "mercado_livre"]

if not df_fila.empty and "plataforma" in df_fila.columns:
    for plataforma in sorted([p for p in df_fila["plataforma"].dropna().unique() if p]):
        if plataforma not in plataformas:
            plataformas.append(plataforma)

plataforma_filtro = st.selectbox(
    "Filtrar plataforma",
    plataformas,
)

categoria_filtro = st.selectbox(
    "Filtrar categoria",
    ["Todas", "casa", "eletrônicos", "moda", "beleza", "mercado", "colecionáveis", "outros"]
)

df_filtrado = df.copy()
df_fila_filtrada = df_fila.copy()

if plataforma_filtro != "Todas":
    df_fila_filtrada = df_fila_filtrada[
        df_fila_filtrada["plataforma"] == plataforma_filtro
    ]

if categoria_filtro != "Todas":
    df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria_filtro]
    df_fila_filtrada = df_fila_filtrada[
        df_fila_filtrada["categoria"] == categoria_filtro
    ]

status_filtro = st.selectbox(
    "Filtrar status",
    ["Todos", "pendente", "aprovado", "rejeitado"]
)

if status_filtro != "Todos":
    df_filtrado = df_filtrado[df_filtrado["status"] == status_filtro]

busca = st.text_input("Buscar produto")

if busca:
    df_filtrado = df_filtrado[
        df_filtrado["titulo"].str.contains(busca, case=False, na=False)
    ]
    df_fila_filtrada = df_fila_filtrada[
        df_fila_filtrada["titulo"].str.contains(busca, case=False, na=False)
    ]

st.subheader("Ações")

if st.button("Rodar coleta manual"):
    resultado = subprocess.run(
        [sys.executable, "scheduler.py", "--once"],
        capture_output=True,
        text=True
    )

    st.code(resultado.stdout)

    if resultado.stderr:
        st.error(resultado.stderr)

    st.rerun()

if st.button("Simular próxima publicação"):
    resultado = subprocess.run(
        [sys.executable, "scheduler.py", "--publicar-um", "--dry-run"],
        capture_output=True,
        text=True
    )

    st.code(resultado.stdout)

    if resultado.stderr:
        st.error(resultado.stderr)

    st.rerun()

if st.button("Publicar 1 oferta agora"):
    resultado = subprocess.run(
        [sys.executable, "scheduler.py", "--publicar-um"],
        capture_output=True,
        text=True
    )

    st.code(resultado.stdout)

    if resultado.stderr:
        st.error(resultado.stderr)

    st.rerun()

if st.button("Gerar posts agora"):
    resultado = subprocess.run(
        [sys.executable, "app.py"],
        capture_output=True,
        text=True
    )

    st.code(resultado.stdout)

    if resultado.stderr:
        st.error(resultado.stderr)

if st.button("Exportar aprovados"):
    resultado = subprocess.run(
        [sys.executable, "agente_publicador.py"],
        capture_output=True,
        text=True
    )

    st.code(resultado.stdout)

    if resultado.stderr:
        st.error(resultado.stderr)

    st.success("Arquivos criados: whatsapp.txt, promobit.txt e instagram.txt")

st.subheader("Status da fila SQLite")

if df_fila_filtrada.empty:
    st.info("Fila vazia.")
else:
    st.dataframe(
        df_fila_filtrada[
            [
                "id",
                "titulo",
                "plataforma",
                "categoria",
                "preco",
                "status",
                "data_criacao",
                "data_publicacao",
            ]
        ],
        use_container_width=True
    )

if st.button("Limpar rejeitados"):
    df_limpeza = ler_posts(ARQUIVO_POSTS)
    df_limpeza = df_limpeza[df_limpeza["status"] != "rejeitado"]
    salvar_posts(df_limpeza, ARQUIVO_POSTS)

    st.success("Posts rejeitados removidos.")
    st.rerun()

if st.button("Limpar aprovados"):
    df_limpeza = ler_posts(ARQUIVO_POSTS)
    df_limpeza = df_limpeza[df_limpeza["status"] != "aprovado"]
    salvar_posts(df_limpeza, ARQUIVO_POSTS)

    st.success("Posts aprovados removidos.")
    st.rerun()

st.subheader("Produtos cadastrados")

st.dataframe(
    df_filtrado[
        [
            "item_id",
            "titulo",
            "categoria",
            "preco",
            "status",
            "data_criacao",
            "log_aprovacao",
        ]
    ],
    use_container_width=True
)

st.subheader("Posts pendentes")

pendentes = df_filtrado[df_filtrado["status"] == "pendente"]

for idx, linha in pendentes.iterrows():
    st.markdown("---")
    st.write(f"### {linha['titulo']}")
    st.write(f"ID: {linha['item_id']}")
    st.write(f"Score: {linha['score']}")
    st.write(f"Categoria: {linha['categoria']}")
    st.write(f"Preço: R$ {linha['preco']}")
    st.write(f"Log: {linha['log_aprovacao']}")

    if pd.notna(linha["imagem"]) and str(linha["imagem"]).strip() != "":
        st.image(linha["imagem"], width=200)

    st.write(linha["link"])

    st.text_area("Post", linha["post"], height=120, key=f"post_{idx}")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Aprovar", key=f"aprovar_{idx}"):
            df_original = ler_posts(ARQUIVO_POSTS)
            df_original.loc[idx, "status"] = "aprovado"
            salvar_posts(df_original, ARQUIVO_POSTS)
            st.rerun()

    with col2:
        if st.button("❌ Rejeitar", key=f"rejeitar_{idx}"):
            df_original = ler_posts(ARQUIVO_POSTS)
            df_original.loc[idx, "status"] = "rejeitado"
            salvar_posts(df_original, ARQUIVO_POSTS)
            st.rerun()

    with col3:
        if st.button("🗑 Excluir", key=f"excluir_{idx}"):
            df_original = ler_posts(ARQUIVO_POSTS)
            df_original = df_original.drop(idx)
            salvar_posts(df_original, ARQUIVO_POSTS)

            st.success("Post removido.")
            st.rerun()

st.subheader("Posts aprovados")

aprovados = df_filtrado[df_filtrado["status"] == "aprovado"]

for idx, linha in aprovados.iterrows():
    st.markdown("---")
    st.write(f"### {linha['titulo']}")
    st.write(f"ID: {linha['item_id']}")
    st.write(f"Categoria: {linha['categoria']}")
    st.write(f"Log: {linha['log_aprovacao']}")

    if pd.notna(linha["imagem"]) and str(linha["imagem"]).strip() != "":
        st.image(linha["imagem"], width=200)

    st.text_area(
        "Post aprovado para copiar",
        linha["post"],
        height=120,
        key=f"aprovado_{idx}"
    )

    st.code(linha["post"])

    st.download_button(
        "📋 Baixar Post",
        data=linha["post"],
        file_name=f"{linha['titulo']}.txt",
        mime="text/plain",
        key=f"download_{idx}"
    )
