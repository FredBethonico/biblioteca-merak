import streamlit as st
import pandas as pd
import gspread
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
    sheet_id = st.secrets.get("SHEET_ID", "0")
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
st.tittle("📚 Biblioteca Merak")
st.caption("Adicionar novo título ao acervo")

# Definição das categorias disponíveis
try:
    ws = conectar_google_sheets()
    categorias_existentes = sorted(list(set(ws.col_values(7))[1:]))
    if not categorias_existentes:
        categorias_existentes = ["Acadêmico", "Espírita", "História", "Literatura", "Não Ficção", "Poesia", "Religião", "Colorir"]
except Exception as e:
    st.error(f"Erro ao conectar com o banco de dados: {e}")
    st.stop()

with st.form(key="form_livro", clear_on_submit=True):
    nome_livro = st.text_input("Nome do Livro", placeholder="Digite o nome do livro")
    
    col1, col2 = st.columns(2)
    with col1:
        autor = st.text_input("Autor", placeholder="Digite o nome do autor")
        editora = st.text_input("Editora", placeholder="Digite o nome da editora")
        ano = st.number_input("Ano Publicação", min_value=0, max_value=datetime.now().year + 1, step=1, format="%d")
    
    with col2:
        opcoes_categoria = categorias_existentes + ["➕ Nova Categoria"]
        
        input_categoria = st.selectbox("Categoria", options=opcoes_categoria)
        
        if input_categoria == "➕ Nova Categoria":
            nova_categoria_digitada = st.text_input("Digite a nova categoria", placeholder="Ex: Culinária")
            categoria_final = nova_categoria_digitada.strip()                    
        else:
            categoria_final = input_categoria
        
        edicao = st.number_input("Edição", min_value=1, step=1, value=1)
        quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)
        
    submit = st.form_submit_button("Salvar na biblioteca", type="primary")
    
if submit:
    if not nome_livro:
        st.warning("Por favor, preencha o nome do livro.")
    elif not autor:
        st.warning("Por favor, preencha o nome do autor.")
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
                    categoria_final,
                    int(quantidade)
                ]
                
                ws.append_row(nova_linha)
                st.success(f"Livro '{nome_livro}' adicionado com sucesso! ID: {novo_id}.")
                
            except Exception as e:
                st.error(f"Erro ao salvar o livro: {e}")