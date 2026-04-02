import streamlit as st
import pandas as pd
import os
import smtplib
import threading
import time
import schedule
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CSV_FILE = "daily_items.csv"
COLUMNS = ["商品名", "カテゴリ", "在庫数", "単位", "消費期限", "買い物リスト"]

# ========== データ読み書き ==========
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

# ========== 消費期限チェック ==========
def get_expiring_items(df, days=7):
    today = date.today()
    alert_items = []
    for _, row in df.iterrows():
        if pd.notna(row["消費期限"]) and str(row["消費期限"]).strip() != "":
            try:
                exp = datetime.strptime(str(row["消費期限"]), "%Y-%m-%d").date()
                days_left = (exp - today).days
                if days_left <= days:
                    alert_items.append((row["商品名"], days_left))
            except:
                pass
    return alert_items

# ========== レシピ提案（AI） ==========
def get_recipe_suggestion(food_items, for_kids, servings):
    import urllib.request
    import json

    if not food_items:
        return "食品カテゴリの在庫がありません。食材を登録してください。"

    kids_text = "子どもも食べられる" if for_kids else "大人向け"
    items_text = "、".join(food_items)

    prompt = f"""
以下の食材が在庫にあります：{items_text}

条件：
- {kids_text}レシピ
- {servings}人前
- 今日の献立として3つ提案してください
- 各レシピは「料理名」「主な食材」「簡単な作り方（3ステップ）」を含めてください
- 日本語で答えてください
"""

    try:
        ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not ANTHROPIC_API_KEY:
            return "APIキーが設定されていません。Streamlit CloudのSecretsに ANTHROPIC_API_KEY を追加してください。"

        data = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            result = json.loads(res.read().decode("utf-8"))
            return result["content"][0]["text"]
    except Exception as e:
        return f"レシピ取得に失敗しました：{e}"

# ========== Gmail送信 ==========
def send_email(subject, body):
    try:
        gmail_address = st.secrets["GMAIL_ADDRESS"]
        app_password = st.secrets["GMAIL_APP_PASSWORD"]
        notify_email = st.secrets["NOTIFY_EMAIL"]

        msg = MIMEMultipart()
        msg["From"] = gmail_address
        msg["To"] = notify_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        return str(e)

def send_daily_notification(df):
    alert_items = get_expiring_items(df)
    if not alert_items:
        return

    lines = ["【日用品管理アプリ】消費期限通知\n"]
    lines.append("■ 消費期限が近い食材：")
    for name, days in alert_items:
        if days < 0:
            lines.append(f"  ・{name}（期限切れ）")
        else:
            lines.append(f"  ・{name}（あと{days}日）")

    food_items = df[df["カテゴリ"] == "食品"]["商品名"].tolist()
    if food_items:
        lines.append("\n■ 本日のレシピ提案（子ども向け・2人前）：")
        recipe = get_recipe_suggestion(food_items, for_kids=True, servings=2)
        lines.append(recipe)

    body = "\n".join(lines)
    send_email("【日用品管理】本日の消費期限通知＆献立提案", body)

# ========== スケジューラー ==========
def run_scheduler(df):
    schedule.every().day.at("07:00").do(send_daily_notification, df)
    while True:
        schedule.run_pending()
        time.sleep(60)

if "scheduler_started" not in st.session_state:
    st.session_state.scheduler_started = False

# ========== アプリ本体 ==========
st.set_page_config(page_title="日用品管理", page_icon="🏠", layout="wide")
st.title("🏠 日用品管理アプリ")

if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# スケジューラー起動（初回のみ）
if not st.session_state.scheduler_started:
    t = threading.Thread(target=run_scheduler, args=(st.session_state.df,), daemon=True)
    t.start()
    st.session_state.scheduler_started = True

tab1, tab2, tab3, tab4 = st.tabs(["📦 在庫一覧", "➕ 商品登録", "🛒 買い物リスト", "🍳 献立提案"])

# ========== タブ1: 在庫一覧 ==========
with tab1:
    st.subheader("在庫一覧")

    if df.empty:
        st.info("商品が登録されていません。「商品登録」タブから追加してください。")
    else:
        alert_items = get_expiring_items(st.session_state.df)
        if alert_items:
            msg = "、".join([f"{n}（あと{d}日）" if d >= 0 else f"{n}（期限切れ）" for n, d in alert_items])
            st.error(f"⚠️ 消費期限に注意： {msg}")

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

# ========== タブ4: 献立提案 ==========
with tab4:
    st.subheader("🍳 今日の献立提案")
    st.caption("在庫中の食品カテゴリの食材をもとにAIが献立を提案します")

    col1, col2 = st.columns(2)
    with col1:
        for_kids = st.toggle("子どもも食べられるレシピ", value=True)
    with col2:
        servings = st.number_input("人数（人前）", min_value=1, max_value=10, value=2)

    food_items = st.session_state.df[st.session_state.df["カテゴリ"] == "食品"]["商品名"].tolist()

    if food_items:
        st.write("**現在の食品在庫：**", "、".join(food_items))
    else:
        st.warning("食品カテゴリの在庫がありません。商品登録でカテゴリを「食品」にして登録してください。")

    if st.button("🍽️ 献立を提案してもらう", type="primary"):
        with st.spinner("AIが献立を考えています..."):
            result = get_recipe_suggestion(food_items, for_kids, servings)
        st.markdown(result)

    st.divider()
    st.subheader("📧 今すぐ通知メールを送る")
    st.caption("毎朝7時に自動送信されますが、今すぐテスト送信もできます")
    if st.button("テストメールを送信"):
        with st.spinner("送信中..."):
            result = send_email(
                "【テスト】日用品管理アプリからの通知",
                "このメールはテスト送信です。設定が正しく完了しています！"
            )
        if result is True:
            st.success("メールを送信しました！受信ボックスを確認してください。")
        else:
            st.error(f"送信失敗：{result}")
