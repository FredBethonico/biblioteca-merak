import streamlit as st
import pandas as pd
import gspread
import unicodedata
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
    sheet_id = st.secrets.get("SHEET_ID")
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

# Interface
st.title("📚 Biblioteca Merak")

tab1, tab2 = st.tabs(["Adicionar Livro", "Ver Acervo"])

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