import streamlit as st
import pandas as pd
import os
from datetime import date, datetime

CSV_FILE = "daily_items.csv"
COLUMNS = ["商品名", "カテゴリ", "在庫数", "単位", "消費期限", "買い物リスト"]

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, dtype=str)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[COLUMNS]
    else:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

st.set_page_config(page_title="日用品管理", page_icon="🏠", layout="wide")
st.title("🏠 日用品管理アプリ")

if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

tab1, tab2, tab3 = st.tabs(["📦 在庫一覧", "➕ 商品登録", "🛒 買い物リスト"])

# ========== タブ1: 在庫一覧 ==========
with tab1:
    st.subheader("在庫一覧")

    if df.empty:
        st.info("商品が登録されていません。「商品登録」タブから追加してください。")
    else:
        today = date.today()
        alert_items = []
        for _, row in df.iterrows():
            if pd.notna(row["消費期限"]) and str(row["消費期限"]).strip() != "":
                try:
                    exp = datetime.strptime(str(row["消費期限"]), "%Y-%m-%d").date()
                    days_left = (exp - today).days
                    if days_left <= 7:
                        alert_items.append(f"{row['商品名']}（あと{days_left}日）")
                except:
                    pass
        if alert_items:
            st.warning("⚠️ 消費期限が近い商品: " + "、".join(alert_items))

        categories = ["すべて"] + sorted(df["カテゴリ"].dropna().unique().tolist())
        selected_cat = st.selectbox("カテゴリで絞り込み", categories)
        filtered = df if selected_cat == "すべて" else df[df["カテゴリ"] == selected_cat]
        st.dataframe(filtered.reset_index(drop=True), use_container_width=True)

        st.subheader("在庫数を更新")
        item_names = df["商品名"].tolist()
        selected_item = st.selectbox("商品を選択", item_names, key="update_select")
        idx = df.index[df["商品名"] == selected_item][0]
        current_stock = df.at[idx, "在庫数"]
        new_stock = st.number_input("新しい在庫数", min_value=0, value=int(current_stock) if str(current_stock).isdigit() else 0)
        if st.button("在庫数を更新"):
            st.session_state.df.at[idx, "在庫数"] = new_stock
            save_data(st.session_state.df)
            st.success(f"「{selected_item}」の在庫数を {new_stock} に更新しました。")
            st.rerun()

        st.subheader("商品を削除")
        del_item = st.selectbox("削除する商品を選択", item_names, key="del_select")
        if st.button("🗑️ 削除する", type="secondary"):
            st.session_state.df = st.session_state.df[st.session_state.df["商品名"] != del_item].reset_index(drop=True)
            save_data(st.session_state.df)
            st.success(f"「{del_item}」を削除しました。")
            st.rerun()

# ========== タブ2: 商品登録 ==========
with tab2:
    st.subheader("新しい商品を登録")

    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("商品名 *", placeholder="例：シャンプー")
        category = st.selectbox("カテゴリ", ["食品", "日用品", "洗剤・清掃", "衛生用品", "その他"])
        stock = st.number_input("在庫数", min_value=0, value=1)
        unit = st.text_input("単位", placeholder="例：本、個、袋")
        exp_date = st.date_input("消費期限（任意）", value=None)
        shopping = st.checkbox("買い物リストに追加する")
        submitted = st.form_submit_button("✅ 登録する")

    if submitted:
        if not name.strip():
            st.error("商品名を入力してください。")
        elif name.strip() in st.session_state.df["商品名"].values:
            st.error(f"「{name}」はすでに登録されています。")
        else:
            new_row = {
                "商品名": name.strip(),
                "カテゴリ": category,
                "在庫数": stock,
                "単位": unit,
                "消費期限": str(exp_date) if exp_date else "",
                "買い物リスト": "✓" if shopping else ""
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.success(f"「{name}」を登録しました！")
            st.rerun()

# ========== タブ3: 買い物リスト ==========
with tab3:
    st.subheader("買い物リスト")

    if st.session_state.df.empty:
        st.info("商品が登録されていません。")
    else:
        shopping_df = st.session_state.df[st.session_state.df["買い物リスト"] == "✓"][["商品名", "カテゴリ", "在庫数", "単位"]].reset_index(drop=True)

        if shopping_df.empty:
            st.info("買い物リストに商品がありません。")
        else:
            st.dataframe(shopping_df, use_container_width=True)

        st.subheader("買い物リストを編集")
        item_names = st.session_state.df["商品名"].tolist()
        toggle_item = st.selectbox("商品を選択", item_names, key="toggle_select")
        idx = st.session_state.df.index[st.session_state.df["商品名"] == toggle_item][0]
        current_flag = st.session_state.df.at[idx, "買い物リスト"]

        if current_flag == "✓":
            if st.button("✅ リストから外す"):
                st.session_state.df.at[idx, "買い物リスト"] = ""
                save_data(st.session_state.df)
                st.success(f"「{toggle_item}」を買い物リストから外しました。")
                st.rerun()
        else:
            if st.button("🛒 買い物リストに追加"):
                st.session_state.df.at[idx, "買い物リスト"] = "✓"
                save_data(st.session_state.df)
                st.success(f"「{toggle_item}」を買い物リストに追加しました。")
                st.rerun()
