import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Controle de Produção", layout="wide", page_icon="🍽️")

# ─── CARREGAR DADOS ───────────────────────────────────────────────────────────
def carregar_dados():
    t1 = pd.read_csv("tabela1.csv", sep=None, engine="python")
    t2 = pd.read_csv("tabela_2.csv", sep=None, engine="python")
    t3 = pd.read_csv("tabela3.csv", sep=None, engine="python")
    t4 = pd.read_csv("tabela4.csv", sep=None, engine="python")

    # Limpar espaços nos nomes das colunas
    t1.columns = t1.columns.str.strip()
    t2.columns = t2.columns.str.strip()
    t3.columns = t3.columns.str.strip()
    t4.columns = t4.columns.str.strip()

    # Converter vírgula para ponto nos numéricos
    for col in ["RENDIMENTO_PREVISTO"]:
        t1[col] = t1[col].astype(str).str.replace(",", ".").astype(float)

    for col in ["QUANTIDADES", "CUSTO_UNITARIO"]:
        t2[col] = t2[col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).str.replace("-", "0", regex=False).astype(float)

    for col in ["RENDIMENTO_REAL"]:
        t3[col] = t3[col].astype(str).str.replace(",", ".").str.replace("nan","0").astype(float)

    t4["QNT_REAL"] = t4["QNT_REAL"].astype(str).str.replace(",", ".").astype(float)

    # Remover linhas vazias
    t3 = t3.dropna(subset=["ID_LANCAMENTO"])
    t3["ID_LANCAMENTO"] = t3["ID_LANCAMENTO"].astype(int)
    t3["ID_PRATO"] = t3["ID_PRATO"].astype(int)
    t4["ID_LANCAMENTO"] = t4["ID_LANCAMENTO"].astype(int)
    t4["ID_PRODUTO"] = t4["ID_PRODUTO"].astype(int)

    return t1, t2, t3, t4

def salvar_lancamento(t3, t4):
    t3.to_csv("tabela3.csv", index=False)
    t4.to_csv("tabela4.csv", index=False)

tabela1, tabela2, tabela3, tabela4 = carregar_dados()

st.title("🍽️ Controle de Produção")

aba = st.sidebar.radio("Menu", ["📋 Lançamento Real", "📊 Relatório de Desvios"])

# ─── ABA 1: LANÇAMENTO ────────────────────────────────────────────────────────
if aba == "📋 Lançamento Real":
    st.header("Novo Lançamento")

    col1, col2 = st.columns(2)
    with col1:
        prato_nome = st.selectbox("Selecione o prato", tabela1["NOME_PRODUCAO"].sort_values())
        id_prato = int(tabela1.loc[tabela1["NOME_PRODUCAO"] == prato_nome, "ID_PRATO"].values[0])
    with col2:
        cozinheiro = st.text_input("Cozinheiro")
        data_lancamento = st.date_input("Data", value=date.today())

    ficha_base = tabela2[tabela2["ID_PRATO"] == id_prato].copy()
    rendimento_previsto = float(tabela1.loc[tabela1["ID_PRATO"] == id_prato, "RENDIMENTO_PREVISTO"].values[0])

    st.subheader("📌 Ficha Base")
    st.dataframe(
        ficha_base[["INGREDIENTES", "QUANTIDADES", "UNIDADE", "CUSTO_UNITARIO"]].reset_index(drop=True),
        use_container_width=True
    )
    st.info(f"Rendimento previsto: **{rendimento_previsto} kg**")

    st.subheader("✏️ Lançamento Real")
    rendimento_real = st.number_input("Rendimento real (kg)", min_value=0.0, step=0.01)

    qtd_reais = {}
    for _, row in ficha_base.iterrows():
        qtd_reais[int(row["ID_PRODUTO"])] = st.number_input(
            f"{row['INGREDIENTES']} (previsto: {row['QUANTIDADES']} {row['UNIDADE']})",
            min_value=0.0, step=0.001, format="%.3f",
            key=f"ing_{row['ID_PRODUTO']}"
        )

    if st.button("💾 Salvar Lançamento", type="primary"):
        if not cozinheiro:
            st.error("Informe o nome do cozinheiro!")
        else:
            novo_id = int(tabela3["ID_LANCAMENTO"].max()) + 1 if len(tabela3) > 0 else 1

            nova_linha3 = pd.DataFrame([{
                "ID_LANCAMENTO": novo_id,
                "ID_PRATO": id_prato,
                "DATA": data_lancamento.strftime("%d/%m/%Y"),
                "COZINHEIRO": cozinheiro.upper(),
                "RENDIMENTO_REAL": rendimento_real
            }])
            tabela3_nova = pd.concat([tabela3, nova_linha3], ignore_index=True)

            linhas4 = []
            for id_prod, qnt in qtd_reais.items():
                nome_ing = ficha_base.loc[ficha_base["ID_PRODUTO"] == id_prod, "INGREDIENTES"].values[0]
                linhas4.append({
                    "ID_PRODUTO": id_prod,
                    "ID_LANCAMENTO": novo_id,
                    "INGREDIENTES": nome_ing,
                    "QNT_REAL": qnt
                })
            tabela4_nova = pd.concat([tabela4, pd.DataFrame(linhas4)], ignore_index=True)

            salvar_lancamento(tabela3_nova, tabela4_nova)
            st.success(f"✅ Lançamento #{novo_id} salvo!")
            st.cache_data.clear()

# ─── ABA 2: RELATÓRIO ─────────────────────────────────────────────────────────
elif aba == "📊 Relatório de Desvios":
    st.header("Relatório de Desvios")

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
        rendimento_previsto = float(tabela1.loc[tabela1["ID_PRATO"] == id_prato, "RENDIMENTO_PREVISTO"].values[0])

        st.subheader(f"🍽️ {nome_prato}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Cozinheiro", lancamento["COZINHEIRO"])
        col2.metric("Rendimento Previsto", f"{rendimento_previsto} kg")
        col3.metric("Rendimento Real", f"{lancamento['RENDIMENTO_REAL']} kg",
                    delta=round(float(lancamento["RENDIMENTO_REAL"]) - rendimento_previsto, 3))

        ficha_base = tabela2[tabela2["ID_PRATO"] == id_prato].copy()
        itens_reais = tabela4[tabela4["ID_LANCAMENTO"] == id_lancamento].copy()

        relatorio = ficha_base.merge(
            itens_reais[["ID_PRODUTO", "QNT_REAL"]],
            on="ID_PRODUTO", how="left"
        )
        relatorio["QNT_REAL"] = relatorio["QNT_REAL"].fillna(0)
        relatorio["DESVIO"] = relatorio["QNT_REAL"] - relatorio["QUANTIDADES"]
        relatorio["DESVIO_%"] = ((relatorio["DESVIO"] / relatorio["QUANTIDADES"]) * 100).round(1)
        relatorio["CUSTO_PREVISTO"] = relatorio["QUANTIDADES"] * relatorio["CUSTO_UNITARIO"]
        relatorio["CUSTO_REAL"] = relatorio["QNT_REAL"] * relatorio["CUSTO_UNITARIO"]
        relatorio["PERDA_R$"] = relatorio["CUSTO_REAL"] - relatorio["CUSTO_PREVISTO"]

        df_exibir = relatorio[["INGREDIENTES", "QUANTIDADES", "QNT_REAL", "DESVIO", "DESVIO_%", "PERDA_R$"]].copy()
        df_exibir.columns = ["Ingrediente", "Previsto", "Real", "Desvio", "Desvio %", "Perda R$"]

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
        total_perda = total_real - total_previsto

        st.subheader("💰 Resumo Financeiro")
        c1, c2, c3 = st.columns(3)
        c1.metric("Custo Previsto", f"R$ {total_previsto:.2f}")
        c2.metric("Custo Real", f"R$ {total_real:.2f}")
        c3.metric("Variação", f"R$ {total_perda:.2f}", delta_color="inverse",
                  delta=f"R$ {total_perda:.2f}")