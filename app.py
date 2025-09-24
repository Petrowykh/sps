# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from api_report import build_api_report, post_merge
from pathlib import Path
from infoparser import get_price_by_barcode
import sqlite3

# ----------  AUTH  ----------
LOGIN = "admin"
PASSWORD = "12345"
DB_FILE = "products.db"
# ----------------------------

# ключ-флаг «парсинг идёт»
LOCK_KEY = "running"

# ----------  UTILS  ----------
def check_password(pw: str) -> bool:
    return pw == PASSWORD

def login_form():
    with st.form("login"):
        pw = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти"):
            if check_password(pw):
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Неверный пароль")

# ----------  UI  ----------
def info():
    st.title("Поиск товара по штрих-коду")
    col1, col2 = st.columns([3, 1])
    with col1:
        barcode = st.text_input("Введите штрих-код", key="barcode_input")
    with col2:
        search = st.button("Искать", type="primary", key="search_btn")

    if search and barcode.strip():
        try:
            with st.spinner("Ищем товар..."):
                link = f"https://infoprice.by/?search={barcode.strip()}"
                st.markdown(f"[Ссылка на сайт]({link})")
                info = get_price_by_barcode(barcode.strip())
                name, min_price, min_promo, shops = info.name, info.min_price, info.min_promo, info.shops
                if name != "Не найден":
                    st.success(f"**{name}**")
                    c1, c2 = st.columns(2)
                    c1.metric("Минимальная цена", f"{min_price:.2f} BYN")
                    if min_promo and min_promo != min_price:
                        c2.metric("Минимальная промо-цена", f"{min_promo:.2f} BYN")
                    st.subheader("Цены по магазинам")
                    st.dataframe(shops, width="stretch")
                else:
                    st.error("Товар не найден")
        except Exception as e:
            st.error(f"Ошибка при поиске товара: {str(e)}")
    elif search and not barcode.strip():
        st.warning("Введите штрих-код")

@st.cache_data(show_spinner=False)
def _load_products() -> pd.DataFrame:
    with sqlite3.connect(DB_FILE, check_same_thread=False) as c:
        return pd.read_sql("SELECT barcode, name FROM top", c)

# ----------  REPORTS  ----------
def reports():
    st.session_state[LOCK_KEY] = True
    try:
        with st.spinner("📊 Загружаем данные..."):
            sku = _load_products()
        if sku.empty:
            st.warning("⚠️ База данных пуста")
            return
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 Всего товаров", f"{sku.shape[0]:,}")
        with col2:
            st.metric("📅 Дата", datetime.now().strftime("%d.%m.%Y"))
        with col3:
            st.metric("⏰ Время", datetime.now().strftime("%H:%M"))
        progress_container = st.empty()
        status_text = st.empty()
        total_items = sku.shape[0]
        result_dict = {
            'name': [], 'barcode': [], 'link_foto': [],
            'min_price': [], 'promo': [], 'sosedi': [],
            'santa': [], 'korona': [], 'evroopt': [],
            'gippo': [], 'grin': []
        }
        for count, (_, row) in enumerate(sku.iterrows()):
            progress = int((count + 1) / total_items * 100)
            progress_container.progress(progress)
            status_text.text(f"🔍 Обрабатывается товар {count + 1} из {total_items}...")
            barcode = str(int(row['barcode'])) if pd.notna(row['barcode']) else '0'
            try:
                info = get_price_by_barcode(barcode)
                if info.name != 'Не найдено':
                    result_dict['name'].append(info.name)
                    result_dict['link_foto'].append(f"https://infoprice.by/?search={barcode}")
                    result_dict['min_price'].append(info.min_price)
                    result_dict['promo'].append(0.0 if info.min_promo == 10000.0 else info.min_promo)
                    result_dict['barcode'].append(barcode)
                    shops_mapping = {
                        'sosedi': 'Соседи', 'santa': 'Санта', 'korona': 'Корона',
                        'evroopt': 'Евроопт', 'gippo': 'Гиппо', 'grin': 'Грин'
                    }
                    for code, shop_name in shops_mapping.items():
                        result_dict[code].append(info.shops.get(shop_name, 0.0))
            except Exception as e:
                st.error(f"❌ Ошибка при обработке штрих-кода {barcode}")
                for key in result_dict:
                    result_dict[key].append(0.0 if key in ['min_price', 'promo'] + list(shops_mapping.keys()) else '')
                continue
        progress_container.empty()
        status_text.empty()
        result_df = pd.DataFrame.from_dict(result_dict).fillna(0.0)
        result_df.insert(0, "№", range(1, len(result_df) + 1))
        filename = f"report_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
        result_df.to_excel(filename, sheet_name="Парсинг", index=False)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.success("✅ Отчет успешно сформирован!")
            with open(filename, "rb") as f:
                st.download_button(
                    label="📥 Скачать отчет",
                    data=f,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )
        with st.expander("📊 Статистика по магазинам"):
            shop_cols = ['sosedi', 'santa', 'korona', 'evroopt', 'gippo', 'grin']
            stats = {shop.title(): f"{(result_df[shop] > 0).sum()} товаров" for shop in shop_cols}
            stats_df = pd.DataFrame(list(stats.items()), columns=['Магазин', 'Найдено товаров'])
            st.dataframe(stats_df, width="stretch")
    except Exception as e:
        st.error(f'🚨 Критическая ошибка: {str(e)}')


def api_report():
    st.session_state[LOCK_KEY] = True
    try:
        ts = datetime.now().strftime("%d%m%Y")
        raw_file = Path(f"api_report_{ts}.xlsx")
        build_api_report(raw_file)
    finally:
        st.session_state[LOCK_KEY] = False
        st.rerun()

# ----------  MAIN  ----------
def main():
    st.set_page_config(
        page_title="Sosedi Parsing System",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'mailto:a.petrowykh@gmail.com',
            'About': "Система парсинга данных"
        }
    )
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .success-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
        }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("auth", False):
        login_form()
        st.stop()

    col_img, col_header = st.columns([1, 2])
    col_img.image('img/logo.png', width=200)

    # ---------- формируем меню ----------
    if st.session_state.get(LOCK_KEY, False):
        menu_opts = ["Информация", "⏳ Идёт парсинг…"]
        disabled  = True          # БЛОКИРУЕМ всё radio целиком
    else:
        menu_opts = ["Информация", "Отчет ТОП 400", "Полный отчет"]
        disabled  = False

    menu = st.sidebar.radio("Выберите действие", menu_opts, disabled=disabled)

    # ---------- кнопка «Выполнить» ----------
    if menu != "Информация" and not st.session_state.get(LOCK_KEY, False):
        btn_text = {"Отчет ТОП 400": "📊 Сделать", "Полный отчет": "📦 Сделать"}.get(menu, "Выполнить")
        if st.sidebar.button(btn_text, type="primary"):
            if menu == "Отчет ТОП 400":
                reports()
            elif menu == "Полный отчет":
                api_report()
    else:
        info()

if __name__ == '__main__':
    main()