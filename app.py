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
def conectar_google_sheets(nome_aba="Biblioteca"):
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

    return spreadsheet.worksheet(nome_aba)

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
    ws_local = conectar_google_sheets("Biblioteca")
    return pd.DataFrame(ws_local.get_all_records())

@st.cache_data(ttl=600)
def carregar_dados_emprestimos():
    ws_local = conectar_google_sheets("Empréstimos")
    return pd.DataFrame(ws_local.get_all_records())

# Interface
st.title("📚 Biblioteca Merak")

tab1, tab2, tab3, tab4 = st.tabs(["Adicionar Livro", "Ver Acervo", "Análises", "Empréstimos"])

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
                        int(quantidade),
                        0, # Emprestado: nenhum exemplar emprestado ao cadastrar
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

    # Sem dragmode/scrollZoom: evita que o toque na área do gráfico (celular) seja
    # interpretado como arraste de zoom em vez de rolagem da página.
    CONFIG_GRAFICO = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False}

    def estilizar_grafico(fig, altura, mostrar_grade_x=False, mostrar_grade_y=False):
        fig.update_layout(
            plot_bgcolor=COR_SUPERFICIE,
            paper_bgcolor=COR_SUPERFICIE,
            font=dict(color=COR_TEXTO, family=FONTE, size=13),
            margin=dict(l=10, r=30, t=10, b=10),
            height=altura,
            showlegend=False,
            dragmode=False,
        )
        fig.update_xaxes(showgrid=mostrar_grade_x, gridcolor=COR_GRADE, title=None, zeroline=False, fixedrange=True)
        fig.update_yaxes(showgrid=mostrar_grade_y, gridcolor=COR_GRADE, title=None, zeroline=False, fixedrange=True)
        return fig

    def grafico_barra_horizontal(dados, rotulo_categoria, rotulo_valor, mostrar_percentual=False):
        hovertemplate = "%{y}: %{x} livro(s)<extra></extra>"
        customdata = None
        if mostrar_percentual:
            total = dados[rotulo_valor].sum()
            customdata = (dados[rotulo_valor] / total * 100).round(1)
            hovertemplate = "%{y}: %{x} livro(s) (%{customdata}%% do acervo)<extra></extra>"

        fig = go.Figure(go.Bar(
            x=dados[rotulo_valor],
            y=dados[rotulo_categoria],
            orientation="h",
            marker_color=AZUL,
            text=dados[rotulo_valor],
            textposition="outside",
            hovertemplate=hovertemplate,
            customdata=customdata,
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

        # Livros com múltiplos autores são cadastrados separados por ";" (ex: "Fulano; Beltrano").
        # Aqui cada autor vira uma linha própria, pra contagens e gráficos considerarem todos.
        autores_explodido = df_analise["Autor"].astype(str).str.split(";").explode().str.strip()
        autores_explodido = autores_explodido[autores_explodido != ""]

        # KPIs (grade em HTML para se reorganizar sozinha em telas pequenas)
        st.markdown("### 📊 Panorama Geral")

        COR_PRIMARIA = "#ffffff" if tema_escuro else "#0b0b0b"

        indicadores = [
            ("Títulos", int((df_analise["Quantidade"] >= 1).sum())),
            ("Exemplares", int(df_analise["Quantidade"].sum())),
            ("Autores", autores_explodido.nunique()),
            ("Categorias", df_analise["Categoria"].nunique()),
            ("Editoras", df_analise["Editora"].replace("", pd.NA).nunique()),
        ]
        tiles_html = "".join(
            f'<div class="kpi-tile"><div class="kpi-label">{rotulo}</div>'
            f'<div class="kpi-value">{valor}</div></div>'
            for rotulo, valor in indicadores
        )
        st.markdown(
            f"""
            <style>
            .kpi-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
                gap: 16px 12px;
                margin: 4px 0 12px 0;
            }}
            .kpi-label {{
                font-size: 0.85rem;
                color: {COR_TEXTO};
                white-space: nowrap;
            }}
            .kpi-value {{
                font-size: 1.9rem;
                font-weight: 600;
                color: {COR_PRIMARIA};
                font-variant-numeric: tabular-nums;
                line-height: 1.3;
            }}
            </style>
            <div class="kpi-grid">{tiles_html}</div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        st.markdown("#### Livros por Categoria")
        contagem_categoria = (
            df_analise["Categoria"].value_counts()
            .rename_axis("Categoria")
            .reset_index(name="Livros")
            .sort_values("Livros", ascending=True)
        )
        st.plotly_chart(
            grafico_barra_horizontal(contagem_categoria, "Categoria", "Livros", mostrar_percentual=True),
            use_container_width=True,
            config=CONFIG_GRAFICO,
        )

        st.divider()

        st.markdown("#### Top 10 Autores")
        contagem_autor = (
            autores_explodido.value_counts().head(10)
            .rename_axis("Autor")
            .reset_index(name="Livros")
            .sort_values("Livros", ascending=True)
        )
        st.plotly_chart(
            grafico_barra_horizontal(contagem_autor, "Autor", "Livros"),
            use_container_width=True,
            config=CONFIG_GRAFICO,
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
                config=CONFIG_GRAFICO,
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
                config=CONFIG_GRAFICO,
            )
        else:
            st.info("Sem dados de ano de publicação suficientes para esta análise.")

with tab4:
    st.caption("Controle de empréstimos do acervo")

    try:
        ws_bib = conectar_google_sheets("Biblioteca")
        ws_emp = conectar_google_sheets("Empréstimos")
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha: {e}")
        st.stop()

    df_bib = carregar_dados_biblioteca()
    df_emp = carregar_dados_emprestimos()

    if df_bib.empty:
        st.info("Ainda não há livros cadastrados para gerenciar empréstimos.")
    else:
        df_bib = df_bib.copy()
        df_bib["Quantidade"] = pd.to_numeric(df_bib["Quantidade"], errors="coerce").fillna(0)
        df_bib["Emprestado"] = pd.to_numeric(df_bib.get("Emprestado", 0), errors="coerce").fillna(0)
        df_bib["Disponível"] = (df_bib["Quantidade"] - df_bib["Emprestado"]).clip(lower=0)

        # ---- Novo empréstimo ----
        st.markdown("### 📤 Novo Empréstimo")
        disponiveis = df_bib[df_bib["Disponível"] > 0]

        if disponiveis.empty:
            st.info("Nenhum exemplar disponível para empréstimo no momento.")
        else:
            opcoes_livro = {
                f"{row['Nome do Livro']} — {row['Autor']} ({int(row['Disponível'])} disponível(is))": row["ID"]
                for _, row in disponiveis.iterrows()
            }
            with st.form(key="form_emprestimo", clear_on_submit=True):
                livro_selecionado = st.selectbox(
                    "Livro", options=list(opcoes_livro.keys()), index=None, placeholder="Selecione um livro"
                )
                pessoa_emprestimo = st.text_input("Pessoa", placeholder="Nome de quem vai levar o livro")
                data_emprestimo = st.date_input("Data", value=datetime.now())
                confirmar_emprestimo = st.form_submit_button("📤 Registrar empréstimo", type="primary")

            if confirmar_emprestimo:
                if not livro_selecionado:
                    st.warning("Selecione um livro.")
                elif not pessoa_emprestimo.strip():
                    st.warning("Informe o nome da pessoa.")
                else:
                    with st.spinner("Registrando empréstimo..."):
                        try:
                            id_livro = opcoes_livro[livro_selecionado]
                            linha_livro = df_bib.index[df_bib["ID"] == id_livro][0] + 2  # +2: cabeçalho + índice 1-based
                            emprestado_atual = int(df_bib.loc[df_bib["ID"] == id_livro, "Emprestado"].iloc[0])
                            nome_livro = df_bib.loc[df_bib["ID"] == id_livro, "Nome do Livro"].iloc[0]

                            ws_bib.update_cell(linha_livro, 9, emprestado_atual + 1)  # coluna I = Emprestado

                            novo_id_emp = gerar_id(ws_emp)
                            ws_emp.append_row([
                                novo_id_emp, id_livro, nome_livro, pessoa_emprestimo.strip(),
                                data_emprestimo.strftime("%d/%m/%Y"), "Empréstimo",
                            ])

                            carregar_dados_biblioteca.clear()
                            carregar_dados_emprestimos.clear()
                            st.success(f"Empréstimo de '{nome_livro}' para {pessoa_emprestimo.strip()} registrado!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao registrar empréstimo: {e}")

        st.divider()

        # ---- Devolução ----
        st.markdown("### 📥 Devolução")

        if df_emp.empty:
            st.info("Nenhum empréstimo registrado ainda.")
        else:
            df_emp_calc = df_emp.copy()
            df_emp_calc["Tipo"] = df_emp_calc["Tipo"].astype(str).str.strip()

            contagem = (
                df_emp_calc.groupby(["ID-Livro", "Nome do Livro", "Pessoa", "Tipo"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
            for coluna in ["Empréstimo", "Devolução"]:
                if coluna not in contagem.columns:
                    contagem[coluna] = 0
            contagem["Em aberto"] = contagem["Empréstimo"] - contagem["Devolução"]
            ativos = contagem[contagem["Em aberto"] > 0].reset_index(drop=True)

            if ativos.empty:
                st.success("Nenhum empréstimo em aberto no momento.")
            else:
                opcoes_devolucao = {
                    f"{row['Nome do Livro']} — {row['Pessoa']} ({int(row['Em aberto'])} em aberto)": row
                    for _, row in ativos.iterrows()
                }
                with st.form(key="form_devolucao", clear_on_submit=True):
                    devolucao_selecionada = st.selectbox("Empréstimo em aberto", options=list(opcoes_devolucao.keys()))
                    data_devolucao = st.date_input("Data da devolução", value=datetime.now(), key="data_devolucao")
                    confirmar_devolucao = st.form_submit_button("✅ Registrar devolução", type="primary")

                if confirmar_devolucao:
                    with st.spinner("Registrando devolução..."):
                        try:
                            info = opcoes_devolucao[devolucao_selecionada]
                            id_livro = info["ID-Livro"]
                            nome_livro = info["Nome do Livro"]
                            pessoa_devolucao = info["Pessoa"]

                            linha_livro_idx = df_bib.index[df_bib["ID"] == id_livro]
                            if len(linha_livro_idx) > 0:
                                emprestado_atual = int(df_bib.loc[df_bib["ID"] == id_livro, "Emprestado"].iloc[0])
                                novo_emprestado = max(0, emprestado_atual - 1)
                                ws_bib.update_cell(linha_livro_idx[0] + 2, 9, novo_emprestado)

                            novo_id_emp = gerar_id(ws_emp)
                            ws_emp.append_row([
                                novo_id_emp, id_livro, nome_livro, pessoa_devolucao,
                                data_devolucao.strftime("%d/%m/%Y"), "Devolução",
                            ])

                            carregar_dados_biblioteca.clear()
                            carregar_dados_emprestimos.clear()
                            st.success(f"Devolução de '{nome_livro}' por {pessoa_devolucao} registrada!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao registrar devolução: {e}")

                st.divider()
                st.markdown("#### Empréstimos em aberto")
                st.dataframe(
                    ativos.rename(columns={"Em aberto": "Qtd. emprestada"})[
                        ["Nome do Livro", "Pessoa", "Qtd. emprestada"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )