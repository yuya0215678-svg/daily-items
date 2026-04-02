import streamlit as st
import pandas as pd
import os
import smtplib
import threading
import time
import schedule
import random
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CSV_FILE = "daily_items.csv"
COLUMNS = ["商品名", "カテゴリ", "在庫数", "単位", "消費期限", "買い物リスト"]

# ========== レシピデータベース ==========
RECIPES = [
    {
        "name": "肉じゃが",
        "keywords": ["じゃがいも", "玉ねぎ", "にんじん", "牛肉", "豚肉"],
        "kids": True,
        "steps": ["肉と野菜を一口大に切る", "油で炒めてから水・醤油・みりん・砂糖で煮る", "汁気が少なくなったら完成"],
        "memo": "甘めに仕上げると子どもが喜びます"
    },
    {
        "name": "野菜炒め",
        "keywords": ["キャベツ", "もやし", "にんじん", "玉ねぎ", "ピーマン", "豚肉", "鶏肉"],
        "kids": True,
        "steps": ["野菜と肉を食べやすい大きさに切る", "強火で炒めて塩・醤油・ごま油で味付け", "さっと仕上げて完成"],
        "memo": "火を強くすることがシャキシャキのコツ"
    },
    {
        "name": "カレーライス",
        "keywords": ["じゃがいも", "にんじん", "玉ねぎ", "牛肉", "豚肉", "鶏肉"],
        "kids": True,
        "steps": ["野菜と肉を切って油で炒める", "水を加えて煮込みカレールーを溶かす", "ご飯と一緒に盛り付けて完成"],
        "memo": "子ども向けは甘口ルーがおすすめ"
    },
    {
        "name": "味噌汁",
        "keywords": ["豆腐", "わかめ", "玉ねぎ", "なす", "じゃがいも", "大根", "にんじん"],
        "kids": True,
        "steps": ["具材を食べやすい大きさに切る", "出汁で煮て味噌を溶かす", "沸騰直前で火を止めて完成"],
        "memo": "どんな具材でも合います"
    },
    {
        "name": "親子丼",
        "keywords": ["鶏肉", "卵", "玉ねぎ"],
        "kids": True,
        "steps": ["鶏肉と玉ねぎを出汁・醤油・みりんで煮る", "溶き卵を回しかけて半熟に仕上げる", "ご飯の上に乗せて完成"],
        "memo": "卵を二段階で入れるとふわふわになります"
    },
    {
        "name": "豚汁",
        "keywords": ["豚肉", "大根", "にんじん", "じゃがいも", "玉ねぎ", "ごぼう"],
        "kids": True,
        "steps": ["野菜と豚肉を切って炒める", "水を加えて煮込み味噌を溶かす", "ごま油を少量たらして完成"],
        "memo": "根菜たっぷりで栄養満点"
    },
    {
        "name": "ハンバーグ",
        "keywords": ["ひき肉", "玉ねぎ", "卵"],
        "kids": True,
        "steps": ["ひき肉・玉ねぎ・卵・パン粉をこねる", "形を整えてフライパンで両面焼く", "ソースをかけて完成"],
        "memo": "中までしっかり火を通してください"
    },
    {
        "name": "鶏の唐揚げ",
        "keywords": ["鶏肉"],
        "kids": True,
        "steps": ["鶏肉を醤油・酒・生姜で下味をつける", "片栗粉をまぶして170℃の油で揚げる", "カリッとしたら完成"],
        "memo": "二度揚げするとさらにカリカリに"
    },
    {
        "name": "トマトパスタ",
        "keywords": ["トマト", "玉ねぎ", "にんにく", "ひき肉", "ベーコン"],
        "kids": True,
        "steps": ["玉ねぎ・にんにくを炒めてトマトを加える", "パスタを茹でてソースと和える", "チーズをかけて完成"],
        "memo": "缶トマトでも美味しく作れます"
    },
    {
        "name": "大根と豚肉の煮物",
        "keywords": ["大根", "豚肉"],
        "kids": True,
        "steps": ["大根を厚めに切り豚肉と炒める", "醤油・みりん・酒・砂糖で煮込む", "大根に味が染みたら完成"],
        "memo": "大根は下茹でするとよく味が染みます"
    },
    {
        "name": "チャーハン",
        "keywords": ["卵", "ねぎ", "ハム", "ベーコン", "ご飯"],
        "kids": True,
        "steps": ["卵をご飯に混ぜておく", "強火で炒めながら醤油・塩で味付け", "ねぎを加えてさっと炒めて完成"],
        "memo": "冷やご飯を使うとパラパラになります"
    },
    {
        "name": "ほうれん草のおひたし",
        "keywords": ["ほうれん草"],
        "kids": True,
        "steps": ["ほうれん草を塩茹でする", "冷水にとって水気を絞る", "醤油とかつおぶしで和えて完成"],
        "memo": "シンプルだけど栄養たっぷり"
    },
    {
        "name": "麻婆豆腐",
        "keywords": ["豆腐", "ひき肉", "ねぎ"],
        "kids": False,
        "steps": ["ひき肉とねぎを炒めて豆板醤・醤油・酒で味付け", "豆腐を加えてさっと煮る", "水溶き片栗粉でとろみをつけて完成"],
        "memo": "子ども向けは豆板醤を減らしてください"
    },
    {
        "name": "生姜焼き",
        "keywords": ["豚肉", "玉ねぎ"],
        "kids": False,
        "steps": ["豚肉を醤油・みりん・生姜で下味をつける", "玉ねぎと一緒に炒める", "タレを絡めて完成"],
        "memo": "ご飯が進む定番おかず"
    },
    {
        "name": "酢豚",
        "keywords": ["豚肉", "ピーマン", "にんじん", "玉ねぎ"],
        "kids": False,
        "steps": ["豚肉に衣をつけて揚げる", "野菜を炒めて酢・砂糖・醤油のタレを加える", "揚げた豚肉を絡めて完成"],
        "memo": "パイナップルを加えると本格的に"
    },
]

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

# ========== レシピ提案 ==========
def suggest_recipes(food_items, for_kids, servings, count=3):
    food_lower = [f.lower() for f in food_items]
    matched = []

    for recipe in RECIPES:
        if for_kids and not recipe["kids"]:
            continue
        score = sum(1 for kw in recipe["keywords"] if any(kw in f or f in kw for f in food_lower))
        if score > 0:
            matched.append((score, recipe))

    matched.sort(key=lambda x: -x[0])
    top = matched[:count] if len(matched) >= count else matched

    if not top:
        return None

    random.shuffle(top)
    return [r for _, r in top]

def format_recipes(recipes, servings):
    if not recipes:
        return "在庫食材に合うレシピが見つかりませんでした。食品カテゴリに食材を登録してみてください。"
    lines = []
    for i, r in enumerate(recipes, 1):
        lines.append(f"### {i}. {r['name']}（{servings}人前）")
        lines.append(f"💡 {r['memo']}")
        lines.append("**作り方：**")
        for j, step in enumerate(r["steps"], 1):
            lines.append(f"{j}. {step}")
        lines.append("")
    return "\n".join(lines)

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

def build_notification_body(df):
    alert_items = get_expiring_items(df)
    lines = ["【日用品管理アプリ】本日の通知\n"]

    if alert_items:
        lines.append("■ 消費期限が近い食材：")
        for name, days in alert_items:
            if days < 0:
                lines.append(f"  ・{name}（期限切れ）")
            else:
                lines.append(f"  ・{name}（あと{days}日）")
    else:
        lines.append("■ 消費期限が近い食材：なし")

    food_items = df[df["カテゴリ"] == "食品"]["商品名"].tolist()
    lines.append("\n■ 本日のレシピ提案（子ども向け・2人前）：")
    recipes = suggest_recipes(food_items, for_kids=True, servings=2)
    if recipes:
        for i, r in enumerate(recipes, 1):
            lines.append(f"\n{i}. {r['name']}")
            lines.append(f"   {r['memo']}")
            for j, step in enumerate(r["steps"], 1):
                lines.append(f"   {j}. {step}")
    else:
        lines.append("  食品カテゴリの在庫がないためレシピを提案できませんでした。")

    return "\n".join(lines)

def send_daily_notification():
    df = load_data()
    body = build_notification_body(df)
    send_email("【日用品管理】本日の消費期限通知＆献立提案", body)

# ========== スケジューラー ==========
def run_scheduler():
    schedule.every().day.at("07:00").do(send_daily_notification)
    while True:
        schedule.run_pending()
        time.sleep(60)

if "scheduler_started" not in st.session_state:
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    st.session_state.scheduler_started = True

# ========== アプリ本体 ==========
st.set_page_config(page_title="日用品管理", page_icon="🏠", layout="wide")
st.title("🏠 日用品管理アプリ")

if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

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
        name = st.text_input("商品名 *", placeholder="例：じゃがいも")
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
    st.caption("在庫中の食品カテゴリの食材をもとにレシピを提案します")

    col1, col2 = st.columns(2)
    with col1:
        for_kids = st.toggle("子どもも食べられるレシピ", value=True)
    with col2:
        servings = st.number_input("人数（人前）", min_value=1, max_value=10, value=2)

    food_items = st.session_state.df[st.session_state.df["カテゴリ"] == "食品"]["商品名"].tolist()

    if food_items:
        st.write("**現在の食品在庫：**", "、".join(food_items))
    else:
        st.warning("食品カテゴリの在庫がありません。「商品登録」でカテゴリを「食品」にして食材を登録してください。")

    if st.button("🍽️ 献立を提案する", type="primary"):
        recipes = suggest_recipes(food_items, for_kids, servings)
        formatted = format_recipes(recipes, servings)
        st.markdown(formatted)

    st.divider()
    st.subheader("📧 メール通知")
    st.caption("毎朝7時に消費期限アラート＋献立提案を自動送信します")
    if st.button("今すぐテストメールを送信"):
        with st.spinner("送信中..."):
            body = build_notification_body(st.session_state.df)
            result = send_email("【日用品管理】テスト通知", body)
        if result is True:
            st.success("✅ メールを送信しました！受信ボックスを確認してください。")
        else:
            st.error(f"送信失敗：{result}")
