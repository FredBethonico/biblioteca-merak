import streamlit as st
import pandas as pd
import gspread
import unicodedata
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Biblioteca Merak", page_icon="❤️", layout="centered")

# Conexão com o Google Sheets
@st.cache_resource
def conectar_google_sheets():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Autenticação de credenciais
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    except Exception:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        
    client = gspread.authorize(creds)
    
    # Abertura da planilha
    try:
        sheet_id = st.secrets.get("SHEET_ID")
    except Exception:
        sheet_id = None

    if sheet_id:
        spreadsheet = client.open_by_key(sheet_id)
    else:
        spreadsheet = client.open("Biblioteca Merak")
        
    return spreadsheet.worksheet("Biblioteca")

# Função para a PK do registro (coluna A:A - ID)
def gerar_id(worksheet):
    coluna_A = worksheet.col_values(1)
    ids = []
    for x in coluna_A:
        if x.isdigit():
            ids.append(int(x))
    
    if not ids:
        return 1
    
    return max(ids) + 1

# Função para normalizar texto da busca
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return str(texto)
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

@st.cache_data(ttl=600)
def carregar_dados_biblioteca():
    ws_local = conectar_google_sheets()
    return pd.DataFrame(ws_local.get_all_records())

# Interface
st.title("📚 Biblioteca Merak")

tab1, tab2, tab3 = st.tabs(["Adicionar Livro", "Ver Acervo", "Análises"])

with tab1:
    st.caption("Adicionar novo título ao acervo")

    # Definição das categorias disponíveis
    try:
        ws = conectar_google_sheets()
        
        todos_valores = ws.col_values(7)
        if "Categoria" in todos_valores:
            todos_valores.remove("Categoria")
            
        categorias_existentes = sorted(list(set(filter(None, todos_valores))))
        
        if not categorias_existentes:
            categorias_existentes = ["Acadêmico", "Espírita", "História", "Literatura", "Não Ficção", "Poesia", "Religião", "Colorir"]

    except Exception as e:
        st.error(f"Erro ao carregar categorias: {e}")
        categorias_existentes = ["Acadêmico", "Espírita", "História", "Literatura", "Não Ficção", "Poesia", "Religião", "Colorir"]
        
    # Categoria
    st.markdown("### 1. Classificação")
    col_cat1, col_cat2 = st.columns(2)

    with col_cat1:
        opcoes_categoria = categorias_existentes + ["➕ Nova Categoria"]
        input_categoria = st.selectbox("Selecione a Categoria", options=opcoes_categoria)

    categoria_final = input_categoria

    if input_categoria == "➕ Nova Categoria":
        with col_cat2:
            nova_categoria_digitada = st.text_input("Digite o nome da nova categoria", placeholder="Ex: Culinária")
            if nova_categoria_digitada:
                categoria_final = nova_categoria_digitada.strip()
            else:
                categoria_final = "" # Garante que fique vazio se a pessoa não digitou nada ainda

    # Detalhes do Livro
    st.markdown("### 2. Detalhes do Livro")
    with st.form(key="form_livro", clear_on_submit=True):
        nome_livro = st.text_input("Nome do Livro", placeholder="Digite o nome do livro")
        
        col1, col2 = st.columns(2)
        with col1:
            autor = st.text_input("Autor", placeholder="Digite o nome do autor")
            editora = st.text_input("Editora", placeholder="Digite o nome da editora")
            
        with col2:
            ano = st.number_input("Ano Publicação", min_value=0, max_value=datetime.now().year + 1, step=1, format="%d")
            edicao = st.number_input("Edição", min_value=1, step=1, value=1)
            quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)
            
        submit = st.form_submit_button("💾 Salvar na biblioteca", type="primary")
        
    # Processamento do formulário    
    if submit:
        erros = []
        if not nome_livro: erros.append("Nome do Livro")
        if not autor: erros.append("Autor")
        if not categoria_final: erros.append("Categoria (você selecionou 'Nova' mas não digitou o nome)")
        
        if erros:
            st.warning(f"Por favor, preencha: {', '.join(erros)}")
        else:
            with st.spinner("Salvando livro na biblioteca..."):
                try:
                    novo_id = gerar_id(ws)
                    
                    nova_linha = [
                        novo_id,
                        nome_livro,
                        autor,
                        editora,
                        int(ano),
                        int(edicao),
                        categoria_final, # Usa a variável definida fora do form
                        int(quantidade)
                    ]
                    
                    ws.append_row(nova_linha)
                    st.success(f"Livro '{nome_livro}' adicionado com sucesso na categoria '{categoria_final}'! (ID: {novo_id})")
                    
                except Exception as e:
                    st.error(f"Erro ao salvar o livro: {e}")
                
with tab2:
    st.caption("Consultar livros da biblioteca Merak")

    df = carregar_dados_biblioteca()
    
    query = st.text_input("🔍 Buscar por título ou autor", placeholder="Digite o que deseja buscar")
    
    if query:
        query_normalizada = normalizar_texto(query)
        
        df["Título Normalizado"] = df["Nome do Livro"].apply(normalizar_texto)
        df["Autor Normalizado"] = df["Autor"].apply(normalizar_texto)
        
        resultados = df[
            df["Título Normalizado"].str.contains(query_normalizada) | 
            df["Autor Normalizado"].str.contains(query_normalizada)
        ]
        
        resultados = resultados.drop(columns=["Título Normalizado", "Autor Normalizado","Edição","Quantidade"])
        
        if not resultados.empty:
            st.write(f"📚 {len(resultados)} livros encontrados:")
            colunas_visiveis = [c for c in resultados.columns if c not in ["Edição", "Quantidade"]]
            st.dataframe(resultados[colunas_visiveis].reset_index(drop=True), hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum resultado encontrado.")

with tab3:
    st.caption("Panorama e indicadores do acervo")

    # Cores e template visual (consistentes em todos os gráficos, adaptados ao tema)
    tema_escuro = st.context.theme is not None and st.context.theme.type == "dark"

    if tema_escuro:
        AZUL = "#3987e5"
        COR_SUPERFICIE = "#1a1a19"
        COR_GRADE = "#2c2c2a"
        COR_TEXTO = "#c3c2b7"
    else:
        AZUL = "#2a78d6"
        COR_SUPERFICIE = "#fcfcfb"
        COR_GRADE = "#e1e0d9"
        COR_TEXTO = "#52514e"

    FONTE = "system-ui, -apple-system, 'Segoe UI', sans-serif"

    def estilizar_grafico(fig, altura, mostrar_grade_x=False, mostrar_grade_y=False):
        fig.update_layout(
            plot_bgcolor=COR_SUPERFICIE,
            paper_bgcolor=COR_SUPERFICIE,
            font=dict(color=COR_TEXTO, family=FONTE, size=13),
            margin=dict(l=10, r=30, t=10, b=10),
            height=altura,
            showlegend=False,
        )
        fig.update_xaxes(showgrid=mostrar_grade_x, gridcolor=COR_GRADE, title=None, zeroline=False)
        fig.update_yaxes(showgrid=mostrar_grade_y, gridcolor=COR_GRADE, title=None, zeroline=False)
        return fig

    def grafico_barra_horizontal(dados, rotulo_categoria, rotulo_valor):
        fig = go.Figure(go.Bar(
            x=dados[rotulo_valor],
            y=dados[rotulo_categoria],
            orientation="h",
            marker_color=AZUL,
            text=dados[rotulo_valor],
            textposition="outside",
            hovertemplate="%{y}: %{x} livro(s)<extra></extra>",
        ))
        fig.update_xaxes(range=[0, dados[rotulo_valor].max() * 1.2])
        return estilizar_grafico(fig, altura=max(220, 40 * len(dados)), mostrar_grade_x=True)

    df_analise = carregar_dados_biblioteca()

    if df_analise.empty:
        st.info("Ainda não há livros cadastrados para gerar análises.")
    else:
        df_analise = df_analise.copy()
        df_analise["Quantidade"] = pd.to_numeric(df_analise["Quantidade"], errors="coerce").fillna(0)
        df_analise["Ano de Publicação"] = pd.to_numeric(df_analise["Ano de Publicação"], errors="coerce")
        df_analise["Categoria"] = df_analise["Categoria"].replace("", "Sem Categoria")

        # KPIs
        st.markdown("### 📊 Panorama Geral")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Títulos", len(df_analise))
        col2.metric("Exemplares", int(df_analise["Quantidade"].sum()))
        col3.metric("Autores", df_analise["Autor"].nunique())
        col4.metric("Categorias", df_analise["Categoria"].nunique())
        col5.metric("Editoras", df_analise["Editora"].replace("", pd.NA).nunique())

        st.divider()

        col_graf1, col_graf2 = st.columns(2)

        with col_graf1:
            st.markdown("#### Livros por Categoria")
            contagem_categoria = (
                df_analise["Categoria"].value_counts()
                .rename_axis("Categoria")
                .reset_index(name="Livros")
                .sort_values("Livros", ascending=True)
            )
            st.plotly_chart(
                grafico_barra_horizontal(contagem_categoria, "Categoria", "Livros"),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        with col_graf2:
            st.markdown("#### Top 10 Autores")
            contagem_autor = (
                df_analise["Autor"].value_counts().head(10)
                .rename_axis("Autor")
                .reset_index(name="Livros")
                .sort_values("Livros", ascending=True)
            )
            st.plotly_chart(
                grafico_barra_horizontal(contagem_autor, "Autor", "Livros"),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        st.divider()

        st.markdown("#### Top 10 Editoras")
        contagem_editora = (
            df_analise["Editora"].replace("", pd.NA).dropna().value_counts().head(10)
            .rename_axis("Editora")
            .reset_index(name="Livros")
            .sort_values("Livros", ascending=True)
        )
        if not contagem_editora.empty:
            st.plotly_chart(
                grafico_barra_horizontal(contagem_editora, "Editora", "Livros"),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.info("Sem editoras cadastradas para esta análise.")

        st.divider()

        st.markdown("#### Publicações por Década")
        df_decadas = df_analise.dropna(subset=["Ano de Publicação"])
        df_decadas = df_decadas[df_decadas["Ano de Publicação"] > 0]

        if not df_decadas.empty:
            decadas = (df_decadas["Ano de Publicação"] // 10 * 10).astype(int)
            contagem_decada = (
                decadas.value_counts()
                .rename_axis("Década")
                .reset_index(name="Livros")
                .sort_values("Década")
            )
            contagem_decada["Década"] = contagem_decada["Década"].astype(str) + "s"

            fig_decada = go.Figure(go.Bar(
                x=contagem_decada["Década"],
                y=contagem_decada["Livros"],
                marker_color=AZUL,
                text=contagem_decada["Livros"],
                textposition="outside",
                hovertemplate="%{x}: %{y} livro(s)<extra></extra>",
            ))
            fig_decada.update_yaxes(range=[0, contagem_decada["Livros"].max() * 1.2])
            st.plotly_chart(
                estilizar_grafico(fig_decada, altura=350, mostrar_grade_y=True),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        else:
            st.info("Sem dados de ano de publicação suficientes para esta análise.")