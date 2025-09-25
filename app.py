# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from api_report import build_api_report, post_merge
from pathlib import Path
from infoparser import get_price_by_barcode
import sqlite3, os, sys
from streamlit_option_menu import option_menu
from loguru import logger
from notification.events import notify_login, notify_report_start, notify_report_complete, notify_download, notify_error

# ----------  AUTH  ----------
PASSWORD = os.getenv('SPS_PASSWORD')
DB_FILE = "products.db"
# ----------------------------
def setup_logger():
    logger.remove()  # Убираем дефолтный handler
    
    # Консольный вывод
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Файловый лог
    logger.add(
        "logs/sps_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    )

setup_logger()

# ----------  UTILS  ----------
def check_password(pw: str) -> bool:
    return pw == PASSWORD

def login_form():
    with st.form("login"):
        pw = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти"):
            if check_password(pw):
                st.session_state["auth"] = True
                
                # Уведомление о входе
                notify_login()
                logger.info("User logged in successfully")
                
                st.rerun()
            else:
                st.error("Неверный пароль")
                logger.warning("Failed login attempt")

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
    try:
        # Уведомление о начале отчета
        notify_report_start("ТОП 400")
        logger.info("TOP 400 report generation started")
        
        sku = _load_products()
        if sku.empty:
            logger.warning("Database is empty")
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
        filename = f"400_report_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
        result_df.to_excel(filename, sheet_name="Парсинг", index=False)
        file_size = Path(filename).stat().st_size
        notify_report_complete("ТОП 400", file_size)
        logger.success(f"TOP 400 report completed: {filename}")
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
                notify_download(filename, "ТОП 400")
                logger.info(f"File downloaded: {filename}")

        with st.expander("📊 Статистика по магазинам"):
            shop_cols = ['sosedi', 'santa', 'korona', 'evroopt', 'gippo', 'grin']
            stats = {shop.title(): f"{(result_df[shop] > 0).sum()} товаров" for shop in shop_cols}
            stats_df = pd.DataFrame(list(stats.items()), columns=['Магазин', 'Найдено товаров'])
            st.dataframe(stats_df, width="stretch")
    except Exception as e:
        error_msg = str(e)
        notify_error(error_msg, "TOP 400 Report")
        logger.error(f"TOP 400 report error: {error_msg}")
        st.error(f'🚨 Критическая ошибка: {error_msg}')


def api_report():
    try:
        notify_report_start("Полный отчет")
        logger.info("Full report generation started")
        result = build_api_report()
        if result is None:
            st.error("Не удалось собрать данные")
            return
            
        with st.spinner("💾 Сохранение данных..."):
            ts = datetime.now().strftime("%d%m%Y")
            raw_filename = f"full_report_{ts}.xlsx"
            
            df = pd.DataFrame(result['data'].values(), columns=result['columns'])
            df.to_excel(raw_filename, index=False)
            st.success(f"✅ Сырые данные сохранены: {raw_filename}")

        with st.spinner("🔧 Пост-обработка данных..."):
            try:
                final_file = post_merge(Path(raw_filename))
                st.success(f"✅ Финальный файл готов!")
                file_size = Path(final_file).stat().st_size
                notify_report_complete("Полный отчет", file_size)
                logger.success(f"Full report completed: {final_file}")
            except Exception as e:
                st.error(f"❌ Ошибка пост-обработки: {e}")
                return

        st.subheader("📊 Итоговая статистика")
        stats = result['stats']
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Товаров собрано", f"{stats['total_products']:,}")
        with col2:
            st.metric("Успешных групп", stats['successful_groups'])
        with col3:
            st.metric("Групп с ошибками", stats['failed_groups'])
        with col4:
            st.metric("Общий прогресс", f"{stats['successful_groups']}/{stats['total_groups']}")

        st.subheader("📥 Скачивание результатов")
        with open(final_file, "rb") as file:
            file_data = file.read()
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label="📥 Скачать финальный отчет",
                data=file_data,
                file_name=final_file.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
            notify_download(final_file.name, "Полный отчет")
            logger.info(f"Full report downloaded: {final_file.name}")
        st.info(f"**Файл:** {final_file.name}")
        
    except Exception as e:
        error_msg = str(e)
        notify_error(error_msg, "Full Report")
        logger.error(f"Full report error: {error_msg}")
        st.error(f"❌ Критическая ошибка: {error_msg}")


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

    # Стили
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        /* Скрываем sidebar */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        /* Убираем кнопку меню в хедере */
        button[kind="header"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("auth", False):
        login_form()
        st.stop()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image('img/logo.png', width=200)
        st.markdown('<div class="main-header">Система парсинга данных</div>', 
                   unsafe_allow_html=True)

    selected_menu = option_menu(
        None, 
        ["Информация", "Отчеты", "Настройки"],
        icons=["info-square", 'bar-chart-fill', 'gear'],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "nav-link-selected": {"background-color": "#1E90FF"}
        }
    )

    if selected_menu == "Информация":
        info()
        
    elif selected_menu == "Отчеты":
        st.header("📊 Отчеты")
        report_type = st.radio(
            "Выберите тип отчета:",
            ["ТОП 400", "Полный отчет"],
            horizontal=True
        )
        if report_type == "ТОП 400":
            if st.button("🚀 Сформировать отчет ТОП 400", type="primary", use_container_width=True):
                reports()
        else:
            if st.button("🚀 Сформировать полный отчет", type="primary", use_container_width=True):
                api_report()
                
    elif selected_menu == "Настройки":
        st.header("⚙️ Настройки")
        st.info("Раздел в разработке")

if __name__ == '__main__':
    main()


