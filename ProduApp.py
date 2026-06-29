import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Controle de Produção", layout="wide", page_icon="🍽️")

# ─── GOOGLE SHEETS CONFIG ─────────────────────────────────────────────────────
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_ID = "151kML_quj77_PKVUXfmsbt0ZevXoEBGXO0kgR_rAI6o"

def conectar_sheets():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def carregar_tabela3():
    try:
        sheet = conectar_sheets()
        ws = sheet.worksheet("tabela3")
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=["ID_LANCAMENTO", "ID_PRATO", "DATA", "COZINHEIRO", "RENDIMENTO_REAL", "QTD_PRODUZIDA"])
        df = pd.DataFrame(data)
        df["ID_LANCAMENTO"] = pd.to_numeric(df["ID_LANCAMENTO"], errors="coerce")
        df["ID_PRATO"] = pd.to_numeric(df["ID_PRATO"], errors="coerce")
        df = df.dropna(subset=["ID_LANCAMENTO"])
        df["ID_LANCAMENTO"] = df["ID_LANCAMENTO"].astype(int)
        df["ID_PRATO"] = df["ID_PRATO"].astype(int)
        return df
    except:
        return pd.DataFrame(columns=["ID_LANCAMENTO", "ID_PRATO", "DATA", "COZINHEIRO", "RENDIMENTO_REAL", "QTD_PRODUZIDA"])

def carregar_tabela4():
    try:
        sheet = conectar_sheets()
        ws = sheet.worksheet("tabela4")
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=["ID_PRODUTO", "ID_LANCAMENTO", "INGREDIENTES", "QNT_REAL", "QNT_PREVISTA"])
        df = pd.DataFrame(data)
        df["ID_LANCAMENTO"] = pd.to_numeric(df["ID_LANCAMENTO"], errors="coerce").astype(int)
        df["ID_PRODUTO"] = pd.to_numeric(df["ID_PRODUTO"], errors="coerce").astype(int)
        df["QNT_REAL"] = pd.to_numeric(df["QNT_REAL"], errors="coerce").fillna(0)
        df["QNT_PREVISTA"] = pd.to_numeric(df["QNT_PREVISTA"], errors="coerce").fillna(0)
        return df
    except:
        return pd.DataFrame(columns=["ID_PRODUTO", "ID_LANCAMENTO", "INGREDIENTES", "QNT_REAL", "QNT_PREVISTA"])

def salvar_lancamento(novo_cab, novos_itens, tabela3, tabela4):
    sheet = conectar_sheets()

    # Salva cabeçalho
    try:
        ws3 = sheet.worksheet("tabela3")
    except:
        ws3 = sheet.add_worksheet("tabela3", 1000, 10)
    
    if len(tabela3) == 0:
        ws3.clear()
        ws3.append_row(["ID_LANCAMENTO", "ID_PRATO", "DATA", "COZINHEIRO", "RENDIMENTO_REAL", "QTD_PRODUZIDA"])
    ws3.append_row([
        novo_cab["ID_LANCAMENTO"],
        novo_cab["ID_PRATO"],
        novo_cab["DATA"],
        novo_cab["COZINHEIRO"],
        novo_cab["RENDIMENTO_REAL"],
        novo_cab["QTD_PRODUZIDA"]
    ])

    # Salva itens
    try:
        ws4 = sheet.worksheet("tabela4")
    except:
        ws4 = sheet.add_worksheet("tabela4", 10000, 10)
    
    if len(tabela4) == 0:
        ws4.clear()
        ws4.append_row(["ID_PRODUTO", "ID_LANCAMENTO", "INGREDIENTES", "QNT_REAL", "QNT_PREVISTA"])
    
    for item in novos_itens:
        ws4.append_row([item["ID_PRODUTO"], item["ID_LANCAMENTO"], item["INGREDIENTES"], item["QNT_REAL"], item["QNT_PREVISTA"]])

# ─── CARREGAR FICHAS BASE ─────────────────────────────────────────────────────
@st.cache_data
def carregar_fichas():
    t1 = pd.read_csv("tabela1.csv", sep=None, engine="python")
    t2 = pd.read_csv("tabela_2.csv", sep=None, engine="python")
    t1.columns = t1.columns.str.strip()
    t2.columns = t2.columns.str.strip()

    t1["RENDIMENTO_PREVISTO"] = t1["RENDIMENTO_PREVISTO"].astype(str).str.replace(",", ".").astype(float)

    for col in ["QUANTIDADES", "CUSTO_UNITARIO"]:
        t2[col] = (t2[col].astype(str)
                   .str.replace(".", "", regex=False)
                   .str.replace(",", ".", regex=False)
                   .str.replace("-", "0", regex=False)
                   .astype(float))
    return t1, t2

tabela1, tabela2 = carregar_fichas()

# ─── INTERFACE ────────────────────────────────────────────────────────────────
st.title("🍽️ Controle de Produção")
aba = st.sidebar.radio("Menu", ["📋 Lançamento Real", "📊 Relatório de Desvios"])

# ─── ABA 1: LANÇAMENTO ────────────────────────────────────────────────────────
if aba == "📋 Lançamento Real":
    st.header("Novo Lançamento")

    col1, col2 = st.columns(2)
    with col1:
        # Busca por digitação
        busca = st.text_input("🔍 Buscar prato")
        pratos_filtrados = tabela1[tabela1["NOME_PRODUCAO"].str.contains(busca.upper(), na=False)]["NOME_PRODUCAO"].sort_values()
        if len(pratos_filtrados) == 0:
            st.warning("Nenhum prato encontrado.")
            st.stop()
        prato_nome = st.selectbox("Selecione o prato", pratos_filtrados)
        id_prato = int(tabela1.loc[tabela1["NOME_PRODUCAO"] == prato_nome, "ID_PRATO"].values[0])

    with col2:
        cozinheiro = st.text_input("Cozinheiro")
        data_lancamento = st.date_input("Data", value=date.today())

    # Quantidade a produzir
    rendimento_base = float(tabela1.loc[tabela1["ID_PRATO"] == id_prato, "RENDIMENTO_PREVISTO"].values[0])
    qtd_produzir = st.number_input(f"Quantidade a produzir (kg) — Ficha base para {rendimento_base} kg", min_value=0.1, value=rendimento_base, step=0.1)
    fator = qtd_produzir / rendimento_base if rendimento_base > 0 else 1

    ficha_base = tabela2[tabela2["ID_PRATO"] == id_prato].copy()
    ficha_base["QNT_AJUSTADA"] = (ficha_base["QUANTIDADES"] * fator).round(4)

    st.subheader("📌 Ficha Base Ajustada")
    st.info(f"Produzindo **{qtd_produzir} kg** — multiplicador: **{fator:.2f}x**")
    st.dataframe(
        ficha_base[["INGREDIENTES", "QUANTIDADES", "QNT_AJUSTADA", "UNIDADE", "CUSTO_UNITARIO"]].rename(columns={
            "QUANTIDADES": "Previsto (1kg)",
            "QNT_AJUSTADA": f"Previsto ({qtd_produzir}kg)"
        }).reset_index(drop=True),
        use_container_width=True
    )

    st.subheader("✏️ Lançamento Real")
    rendimento_real = st.number_input("Rendimento real (kg)", min_value=0.0, step=0.01)

    qtd_reais = {}
    for _, row in ficha_base.iterrows():
        qtd_reais[int(row["ID_PRODUTO"])] = st.number_input(
            f"{row['INGREDIENTES']} (previsto: {row['QNT_AJUSTADA']} {row['UNIDADE']})",
            min_value=0.0, step=0.001, format="%.3f",
            key=f"ing_{row['ID_PRODUTO']}"
        )

    if st.button("💾 Salvar Lançamento", type="primary"):
        if not cozinheiro:
            st.error("Informe o nome do cozinheiro!")
        else:
            tabela3 = carregar_tabela3()
            tabela4 = carregar_tabela4()
            novo_id = int(tabela3["ID_LANCAMENTO"].max()) + 1 if len(tabela3) > 0 else 1

            novo_cab = {
                "ID_LANCAMENTO": novo_id,
                "ID_PRATO": id_prato,
                "DATA": data_lancamento.strftime("%d/%m/%Y"),
                "COZINHEIRO": cozinheiro.upper(),
                "RENDIMENTO_REAL": rendimento_real,
                "QTD_PRODUZIDA": qtd_produzir
            }

            novos_itens = []
            for id_prod, qnt in qtd_reais.items():
                nome_ing = ficha_base.loc[ficha_base["ID_PRODUTO"] == id_prod, "INGREDIENTES"].values[0]
                qnt_prev = float(ficha_base.loc[ficha_base["ID_PRODUTO"] == id_prod, "QNT_AJUSTADA"].values[0])
                novos_itens.append({
                    "ID_PRODUTO": id_prod,
                    "ID_LANCAMENTO": novo_id,
                    "INGREDIENTES": nome_ing,
                    "QNT_REAL": qnt,
                    "QNT_PREVISTA": qnt_prev
                })

            salvar_lancamento(novo_cab, novos_itens, tabela3, tabela4)
            st.success(f"✅ Lançamento #{novo_id} salvo no Google Sheets!")

# ─── ABA 2: RELATÓRIO ─────────────────────────────────────────────────────────
elif aba == "📊 Relatório de Desvios":
    st.header("Relatório de Desvios")

    tabela3 = carregar_tabela3()
    tabela4 = carregar_tabela4()

    if len(tabela3) == 0:
        st.warning("Nenhum lançamento encontrado.")
    else:
        opcoes = tabela3.copy()
        opcoes["LABEL"] = opcoes.apply(
            lambda r: f"#{int(r['ID_LANCAMENTO'])} - {r['COZINHEIRO']} - {r['DATA']}", axis=1
        )
        lancamento_label = st.selectbox("Selecione o lançamento", opcoes["LABEL"])
        lancamento = opcoes[opcoes["LABEL"] == lancamento_label].iloc[0]

        id_lancamento = int(lancamento["ID_LANCAMENTO"])
        id_prato = int(lancamento["ID_PRATO"])
        nome_prato = tabela1.loc[tabela1["ID_PRATO"] == id_prato, "NOME_PRODUCAO"].values[0]
        qtd_produzida = float(lancamento.get("QTD_PRODUZIDA", 1))
        rendimento_base = float(tabela1.loc[tabela1["ID_PRATO"] == id_prato, "RENDIMENTO_PREVISTO"].values[0])
        fator = qtd_produzida / rendimento_base if rendimento_base > 0 else 1

        st.subheader(f"🍽️ {nome_prato}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Cozinheiro", lancamento["COZINHEIRO"])
        col2.metric("Quantidade Produzida", f"{qtd_produzida} kg")
        col3.metric("Rendimento Previsto", f"{round(rendimento_base * fator, 3)} kg")
        col4.metric("Rendimento Real", f"{lancamento['RENDIMENTO_REAL']} kg",
                    delta=round(float(lancamento["RENDIMENTO_REAL"]) - rendimento_base * fator, 3))

        itens_reais = tabela4[tabela4["ID_LANCAMENTO"] == id_lancamento].copy()

        relatorio = itens_reais.copy()
        relatorio["DESVIO"] = relatorio["QNT_REAL"] - relatorio["QNT_PREVISTA"]
        relatorio["DESVIO_%"] = ((relatorio["DESVIO"] / relatorio["QNT_PREVISTA"].replace(0, 1)) * 100).round(1)

        # Busca custo unitário
        custo_map = tabela2.set_index("ID_PRODUTO")["CUSTO_UNITARIO"].to_dict()
        relatorio["CUSTO_UNITARIO"] = relatorio["ID_PRODUTO"].map(custo_map).fillna(0)
        relatorio["CUSTO_PREVISTO"] = relatorio["QNT_PREVISTA"] * relatorio["CUSTO_UNITARIO"]
        relatorio["CUSTO_REAL"] = relatorio["QNT_REAL"] * relatorio["CUSTO_UNITARIO"]
        relatorio["VARIACAO_R$"] = relatorio["CUSTO_REAL"] - relatorio["CUSTO_PREVISTO"]

        df_exibir = relatorio[["INGREDIENTES", "QNT_PREVISTA", "QNT_REAL", "DESVIO", "DESVIO_%", "VARIACAO_R$"]].copy()
        df_exibir.columns = ["Ingrediente", "Previsto", "Real", "Desvio", "Desvio %", "Variação R$"]

        def cor_desvio(val):
            if isinstance(val, float) and val > 0:
                return "background-color: #ffcccc"
            elif isinstance(val, float) and val < 0:
                return "background-color: #ccffcc"
            return ""

        st.subheader("📋 Comparativo de Ingredientes")
        st.dataframe(
            df_exibir.style.map(cor_desvio, subset=["Desvio"]),
            use_container_width=True
        )

        total_previsto = relatorio["CUSTO_PREVISTO"].sum()
        total_real = relatorio["CUSTO_REAL"].sum()
        total_variacao = total_real - total_previsto

        st.subheader("💰 Resumo Financeiro")
        c1, c2, c3 = st.columns(3)
        c1.metric("Custo Previsto", f"R$ {total_previsto:.2f}")
        c2.metric("Custo Real", f"R$ {total_real:.2f}")
        # Verde se economizou, vermelho se gastou mais
        cor = "normal" if total_variacao <= 0 else "inverse"
        c3.metric("Variação", f"R$ {total_variacao:.2f}", delta=f"R$ {total_variacao:.2f}", delta_color=cor)

        # Download CSV
        st.subheader("📥 Exportar")
        csv = df_exibir.to_csv(index=False, decimal=",", sep=";")
        st.download_button(
            label="📥 Baixar Relatório CSV",
            data=csv,
            file_name=f"relatorio_{id_lancamento}_{lancamento['COZINHEIRO']}.csv",
            mime="text/csv"
        )
