# # app.py
# import streamlit as st
# import pandas as pd
# from datetime import datetime
# from api_report import build_api_report, post_merge
# from pathlib import Path
# from infoparser import get_price_by_barcode
# import sqlite3, os, sys
# from streamlit_option_menu import option_menu
# from loguru import logger
# from notification.events import notify_login, notify_report_start, notify_report_complete, notify_download, notify_error
# from dotenv import load_dotenv

# # Пытаемся загрузить из разных источников
# def load_config():
#     load_dotenv()
    
#     password = os.getenv('SPS_PASSWORD')
#     if password:
#         logger.info("Password loaded from environment variables")
#         return password
    
#     # 4. Если ничего не найдено
#     logger.error("SPS_PASSWORD not found in any source")
#     return None

# # ----------  AUTH  ----------
# LOGIN = "admin"
# PASSWORD = load_config()
# DB_FILE = "products.db"
# # ----------------------------
# def setup_logger():
#     logger.remove()  # Убираем дефолтный handler
    
#     # Консольный вывод
#     logger.add(
#         sys.stderr,
#         format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
#         level="INFO",
#         colorize=True
#     )
    
#     # Файловый лог
#     logger.add(
#         "logs/sps_{time:YYYY-MM-DD}.log",
#         rotation="10 MB",
#         retention="30 days",
#         format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
#     )

# setup_logger()

# # ----------  UTILS  ----------
# def check_password(pw: str) -> bool:
#     return pw == PASSWORD

# def login_form():
#     with st.form("login"):
#         pw = st.text_input("Пароль", type="password")
#         if st.form_submit_button("Войти"):
#             if check_password(pw):
#                 st.session_state["auth"] = True
                
#                 # Уведомление о входе
#                 notify_login()
#                 logger.info("User logged in successfully")
                
#                 st.rerun()
#             else:
#                 st.error("Неверный пароль")
#                 logger.warning("Failed login attempt")

# # ----------  UI  ----------
# def info():
#     st.title("Поиск товара по штрих-коду")
#     col1, col2 = st.columns([3, 1])
#     with col1:
#         barcode = st.text_input("Введите штрих-код", key="barcode_input")
#     with col2:
#         search = st.button("Искать", type="primary", key="search_btn")

#     if search and barcode.strip():
#         try:
#             with st.spinner("Ищем товар..."):
#                 link = f"https://infoprice.by/?search={barcode.strip()}"
#                 st.markdown(f"[Ссылка на сайт]({link})")
#                 info = get_price_by_barcode(barcode.strip())
#                 name, min_price, min_promo, shops = info.name, info.min_price, info.min_promo, info.shops
#                 if name != "Не найден":
#                     st.success(f"**{name}**")
#                     c1, c2 = st.columns(2)
#                     c1.metric("Минимальная цена", f"{min_price:.2f} BYN")
#                     if min_promo and min_promo != min_price:
#                         c2.metric("Минимальная промо-цена", f"{min_promo:.2f} BYN")
#                     st.subheader("Цены по магазинам")
#                     st.dataframe(shops, width="stretch")
#                 else:
#                     st.error("Товар не найден")
#         except Exception as e:
#             st.error(f"Ошибка при поиске товара: {str(e)}")
#     elif search and not barcode.strip():
#         st.warning("Введите штрих-код")

# @st.cache_data(show_spinner=False)
# def _load_products() -> pd.DataFrame:
#     with sqlite3.connect(DB_FILE, check_same_thread=False) as c:
#         return pd.read_sql("SELECT barcode, name FROM top", c)

# # ----------  REPORTS  ----------

# def reports():
#     # Показываем предупреждение перед началом
#     st.warning("""
#     ⚠️ **Внимание! Идет процесс парсинга данных**
    
#     - Не закрывайте эту страницу
#     - Не переходите по другим пунктам меню  
#     - Не обновляйте страницу
#     - Процесс может занять несколько минут
#     """)
    
#     # Добавляем индикатор прогресса для всего процесса
#     progress_bar = st.progress(0)
#     status_text = st.empty()
    
#     try:
#         # Обновляем статус
#         status_text.info("🔄 Подготовка к формированию отчета ТОП 400...")
#         progress_bar.progress(10)
        
#         # Уведомление о начале отчета
#         notify_report_start("ТОП 400")
#         logger.info("TOP 400 report generation started")
        
#         with st.spinner("📊 Загружаем данные..."):
#             sku = _load_products()
#             progress_bar.progress(20)
        
#         if sku.empty:
#             logger.warning("Database is empty")
#             st.warning("⚠️ База данных пуста")
#             return
        
#         status_text.info("🔍 Начинаем парсинг данных...")
#         progress_bar.progress(30)
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             st.metric("📦 Всего товаров", f"{sku.shape[0]:,}")
#         with col2:
#             st.metric("📅 Дата", datetime.now().strftime("%d.%m.%Y"))
#         with col3:
#             st.metric("⏰ Время", datetime.now().strftime("%H:%M"))
#         progress_container = st.empty()
#         status_text = st.empty()
#         total_items = sku.shape[0]
#         result_dict = {
#             'name': [], 'barcode': [], 'link_foto': [],
#             'min_price': [], 'promo': [], 'sosedi': [],
#             'santa': [], 'korona': [], 'evroopt': [],
#             'gippo': [], 'grin': []
#         }
#         for count, (_, row) in enumerate(sku.iterrows()):
#             progress = 30 + (count / len(sku)) * 60  # от 30% до 90%
#             progress_bar.progress(int(progress))
#             status_text.info(f"🔍 Обрабатывается товар {count + 1} из {len(sku)}...")
#             barcode = str(int(row['barcode'])) if pd.notna(row['barcode']) else '0'
#             try:
#                 info = get_price_by_barcode(barcode)
#                 if info.name != 'Не найдено':
#                     result_dict['name'].append(info.name)
#                     result_dict['link_foto'].append(f"https://infoprice.by/?search={barcode}")
#                     result_dict['min_price'].append(info.min_price)
#                     result_dict['promo'].append(0.0 if info.min_promo == 10000.0 else info.min_promo)
#                     result_dict['barcode'].append(barcode)
#                     shops_mapping = {
#                         'sosedi': 'Соседи', 'santa': 'Санта', 'korona': 'Корона',
#                         'evroopt': 'Евроопт', 'gippo': 'Гиппо', 'grin': 'Грин'
#                     }
#                     for code, shop_name in shops_mapping.items():
#                         result_dict[code].append(info.shops.get(shop_name, 0.0))
#             except Exception as e:
#                 st.error(f"❌ Ошибка при обработке штрих-кода {barcode}")
#                 for key in result_dict:
#                     result_dict[key].append(0.0 if key in ['min_price', 'promo'] + list(shops_mapping.keys()) else '')
#                 continue
#         progress_container.empty()
#         status_text.empty()
#         result_df = pd.DataFrame.from_dict(result_dict).fillna(0.0)
#         result_df.insert(0, "№", range(1, len(result_df) + 1))
#         filename = f"400_report_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
#         result_df.to_excel(filename, sheet_name="Парсинг", index=False)
#         file_size = Path(filename).stat().st_size
#         notify_report_complete("ТОП 400", file_size)
#         logger.success(f"TOP 400 report completed: {filename}")
#         col1, col2, col3 = st.columns([1, 2, 1])
#         with col2:
#             st.success("✅ Отчет успешно сформирован!")
#             with open(filename, "rb") as f:
#                 st.download_button(
#                     label="📥 Скачать отчет",
#                     data=f,
#                     file_name=filename,
#                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                     width="stretch"
#                 )
#                 notify_download(filename, "ТОП 400")
#                 logger.info(f"File downloaded: {filename}")

#         with st.expander("📊 Статистика по магазинам"):
#             shop_cols = ['sosedi', 'santa', 'korona', 'evroopt', 'gippo', 'grin']
#             stats = {shop.title(): f"{(result_df[shop] > 0).sum()} товаров" for shop in shop_cols}
#             stats_df = pd.DataFrame(list(stats.items()), columns=['Магазин', 'Найдено товаров'])
#             st.dataframe(stats_df, width="stretch")
#     except Exception as e:
#         progress_bar.progress(100)
#         status_text.error("❌ Произошла ошибка!")
#         error_msg = str(e)
#         notify_error(error_msg, "TOP 400 Report")
#         logger.error(f"TOP 400 report error: {error_msg}")
#         st.error(f'🚨 Критическая ошибка: {error_msg}')



# def api_report():
#     # Показываем предупреждение перед началом
#     st.warning("""
#     ⚠️ **Внимание! Идет процесс сбора полного отчета**
    
#     - Не закрывайте эту страницу
#     - Не переходите по другим пунктам меню
#     - Не обновляйте страницу  
#     - Процесс может занять 10-30 минут
#     - Это собираются данные по ВСЕМ товарам
#     """)
    
#     status_text = st.empty()
    
#     # Переменные для хранения путей к файлам
#     raw_filename = None
#     final_file = None
    
#     try:
#         status_text.info("🔄 Подготовка к формированию полного отчета...")
        
#         notify_report_start("Полный отчет")
#         logger.info("Full report generation started")
        
#         status_text.info("🌐 Подключаемся к API...")
        
#         result = build_api_report()
#         if result is None:
#             raise Exception("Failed to collect data")
        
#         status_text.info("💾 Сохраняем сырые данные...")
            
#         ts = datetime.now().strftime("%d%m%Y")
#         raw_filename = Path(f"full_report_{ts}.xlsx")
        
#         df = pd.DataFrame(result['data'].values(), columns=result['columns'])
#         df.to_excel(raw_filename, index=False)
        
#         status_text.info("🔧 Выполняем пост-обработку...")
        
#         final_file = post_merge(raw_filename)
        
#         # Удаляем сырой файл после успешной пост-обработки
#         if raw_filename.exists():
#             raw_filename.unlink()
#             logger.info(f"Raw file deleted: {raw_filename}")
        
#         status_text.success("✅ Полный отчет успешно сформирован!")
        
#         file_size = final_file.stat().st_size
#         notify_report_complete("Полный отчет", file_size)
#         logger.success(f"Full report completed: {final_file}")
        
#         with open(final_file, "rb") as file:
#             file_data = file.read()
#             if st.download_button(
#                 label="📥 Скачать полный отчет",
#                 data=file_data,
#                 file_name=final_file.name,
#                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                 use_container_width=True,
#                 type="primary"
#             ):
#                 notify_download(final_file.name, "Полный отчет")
#                 logger.info(f"Full report downloaded: {final_file.name}")
                
#                 # Удаляем финальный файл после скачивания
#                 if final_file.exists():
#                     final_file.unlink()
#                     logger.info(f"Final file deleted: {final_file}")
        
#     except Exception as e:
#         # В случае ошибки также пытаемся удалить временные файлы
#         try:
#             if raw_filename and raw_filename.exists():
#                 raw_filename.unlink()
#                 logger.info(f"Raw file deleted after error: {raw_filename}")
#             if final_file and final_file.exists():
#                 final_file.unlink()
#                 logger.info(f"Final file deleted after error: {final_file}")
#         except Exception as cleanup_error:
#             logger.warning(f"Cleanup error: {cleanup_error}")
        
#         status_text.error("❌ Произошла ошибка!")
#         error_msg = str(e)
#         notify_error(error_msg, "Full Report")
#         logger.error(f"Full report error: {error_msg}")
#         st.error(f"❌ Критическая ошибка: {error_msg}")


# # ----------  MAIN  ----------

# def main():
#     st.set_page_config(
#         page_title="Sosedi Parsing System",
#         page_icon="🛒",
#         layout="wide",
#         initial_sidebar_state="expanded",
#         menu_items={
#             'Get Help': 'mailto:a.petrowykh@gmail.com',
#             'About': "Система парсинга данных"
#         }
#     )

#     # Стили
#     st.markdown("""
#     <style>
#         .main-header {
#             font-size: 2.5rem;
#             color: #1f77b4;
#             text-align: center;
#             margin-bottom: 2rem;
#         }
#         /* Скрываем sidebar */
#         section[data-testid="stSidebar"] {
#             display: none !important;
#         }
#         /* Убираем кнопку меню в хедере */
#         button[kind="header"] {
#             display: none !important;
#         }
#     </style>
#     """, unsafe_allow_html=True)

#     if not st.session_state.get("auth", False):
#         login_form()
#         st.stop()

#     col1, col2, col3 = st.columns([1, 2, 1])
#     with col2:
#         st.image('img/logo.png', width=200)
#         st.markdown('<div class="main-header">Система парсинга данных</div>', 
#                    unsafe_allow_html=True)

#     selected_menu = option_menu(
#         None, 
#         ["Информация", "Отчеты", "Настройки"],
#         icons=["info-square", 'bar-chart-fill', 'gear'],
#         menu_icon="cast",
#         default_index=0,
#         orientation="horizontal",
#         styles={
#             "nav-link-selected": {"background-color": "#1E90FF"}
#         }
#     )

#     if selected_menu == "Информация":
#         info()
        
#     elif selected_menu == "Отчеты":
#         st.header("📊 Отчеты")
#         report_type = st.radio(
#             "Выберите тип отчета:",
#             ["ТОП 400", "Полный отчет"],
#             horizontal=True
#         )
#         if report_type == "ТОП 400":
#             if st.button("🚀 Сформировать отчет ТОП 400", type="primary", use_container_width=True):
#                 reports()
#         else:
#             if st.button("🚀 Сформировать полный отчет", type="primary", use_container_width=True):
#                 api_report()
                
#     elif selected_menu == "Настройки":
#         st.header("⚙️ Настройки")
#         st.info("Раздел в разработке")

# if __name__ == '__main__':
#     main()


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
from dotenv import load_dotenv

# Пытаемся загрузить из разных источников
def load_config():
    load_dotenv()
    
    password = os.getenv('SPS_PASSWORD')
    if password:
        logger.info("Password loaded from environment variables")
        return password
    
    # 4. Если ничего не найдено
    logger.error("SPS_PASSWORD not found in any source")
    return None

# ----------  FILE MANAGEMENT  ----------
def get_excel_files():
    """Получить список всех Excel файлов в текущей директории"""
    excel_files = []
    current_dir = Path(".")
    
    for file_path in current_dir.glob("*.xlsx"):
        file_info = {
            'name': file_path.name,
            'path': file_path,
            'size': file_path.stat().st_size,
            'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
            'size_mb': file_path.stat().st_size / (1024 * 1024)
        }
        excel_files.append(file_info)
    
    # Сортируем по дате изменения (новые сверху)
    excel_files.sort(key=lambda x: x['modified'], reverse=True)
    return excel_files

def delete_excel_files(file_names):
    """Удалить указанные Excel файлы"""
    deleted_files = []
    errors = []
    
    for file_name in file_names:
        try:
            file_path = Path(file_name)
            if file_path.exists():
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_files.append((file_name, file_size))
                logger.info(f"File deleted: {file_name}")
        except Exception as e:
            errors.append(f"{file_name}: {str(e)}")
            logger.error(f"Error deleting file {file_name}: {e}")
    
    return deleted_files, errors

def get_total_files_size(files):
    """Получить общий размер файлов в МБ"""
    return sum(file['size_mb'] for file in files)

# ----------  AUTH  ----------
LOGIN = "admin"
PASSWORD = load_config()
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
    # Показываем предупреждение перед началом
    st.warning("""
    ⚠️ **Внимание! Идет процесс парсинга данных**
    
    - Не закрывайте эту страницу
    - Не переходите по другим пунктам меню  
    - Не обновляйте страницу
    - Процесс может занять несколько минут
    """)
    
    # Добавляем индикатор прогресса для всего процесса
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Обновляем статус
        status_text.info("🔄 Подготовка к формированию отчета ТОП 400...")
        progress_bar.progress(10)
        
        # Уведомление о начале отчета
        notify_report_start("ТОП 400")
        logger.info("TOP 400 report generation started")
        
        with st.spinner("📊 Загружаем данные..."):
            sku = _load_products()
            progress_bar.progress(20)
        
        if sku.empty:
            logger.warning("Database is empty")
            st.warning("⚠️ База данных пуста")
            return
        
        status_text.info("🔍 Начинаем парсинг данных...")
        progress_bar.progress(30)
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
            progress = 30 + (count / len(sku)) * 60  # от 30% до 90%
            progress_bar.progress(int(progress))
            status_text.info(f"🔍 Обрабатывается товар {count + 1} из {len(sku)}...")
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
        progress_bar.progress(100)
        status_text.error("❌ Произошла ошибка!")
        error_msg = str(e)
        notify_error(error_msg, "TOP 400 Report")
        logger.error(f"TOP 400 report error: {error_msg}")
        st.error(f'🚨 Критическая ошибка: {error_msg}')



def api_report():
    # Показываем предупреждение перед началом
    st.warning("""
    ⚠️ **Внимание! Идет процесс сбора полного отчета**
    
    - Не закрывайте эту страницу
    - Не переходите по другим пунктам меню
    - Не обновляйте страницу  
    - Процесс может занять 10-30 минут
    - Это собираются данные по ВСЕМ товарам
    """)
    
    status_text = st.empty()
    
    # Переменные для хранения путей к файлам
    raw_filename = None
    final_file = None
    
    try:
        status_text.info("🔄 Подготовка к формированию полного отчета...")
        
        notify_report_start("Полный отчет")
        logger.info("Full report generation started")
        
        status_text.info("🌐 Подключаемся к API...")
        
        result = build_api_report()
        if result is None:
            raise Exception("Failed to collect data")
        
        status_text.info("💾 Сохраняем сырые данные...")
            
        ts = datetime.now().strftime("%d%m%Y")
        raw_filename = Path(f"full_report_{ts}.xlsx")
        
        df = pd.DataFrame(result['data'].values(), columns=result['columns'])
        df.to_excel(raw_filename, index=False)
        
        status_text.info("🔧 Выполняем пост-обработку...")
        
        final_file = post_merge(raw_filename)
        
        # Удаляем сырой файл после успешной пост-обработки
        if raw_filename.exists():
            raw_filename.unlink()
            logger.info(f"Raw file deleted: {raw_filename}")
        
        status_text.success("✅ Полный отчет успешно сформирован!")
        
        file_size = final_file.stat().st_size
        notify_report_complete("Полный отчет", file_size)
        logger.success(f"Full report completed: {final_file}")
        
        with open(final_file, "rb") as file:
            file_data = file.read()
            if st.download_button(
                label="📥 Скачать полный отчет",
                data=file_data,
                file_name=final_file.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
                type="primary"
            ):
                notify_download(final_file.name, "Полный отчет")
                logger.info(f"Full report downloaded: {final_file.name}")
                
                # Удаляем финальный файл после скачивания
                if final_file.exists():
                    final_file.unlink()
                    logger.info(f"Final file deleted: {final_file}")
        
    except Exception as e:
        # В случае ошибки также пытаемся удалить временные файлы
        try:
            if raw_filename and raw_filename.exists():
                raw_filename.unlink()
                logger.info(f"Raw file deleted after error: {raw_filename}")
            if final_file and final_file.exists():
                final_file.unlink()
                logger.info(f"Final file deleted after error: {final_file}")
        except Exception as cleanup_error:
            logger.warning(f"Cleanup error: {cleanup_error}")
        
        status_text.error("❌ Произошла ошибка!")
        error_msg = str(e)
        notify_error(error_msg, "Full Report")
        logger.error(f"Full report error: {error_msg}")
        st.error(f"❌ Критическая ошибка: {error_msg}")

# ----------  SETTINGS  ----------
# ----------  SETTINGS  ----------
def settings():
    st.header("⚙️ Настройки системы")
    
    # Информация о временных файлах
    st.subheader("📊 Управление временными файлами")
    
    # Получаем список Excel файлов
    excel_files = get_excel_files()
    total_size = get_total_files_size(excel_files)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📁 Количество файлов", len(excel_files))
    with col2:
        st.metric("💾 Общий размер", f"{total_size:.2f} МБ")
    with col3:
        st.metric("📅 Последнее обновление", datetime.now().strftime("%d.%m.%Y"))
    
    if excel_files:
        st.info(f"Найдено {len(excel_files)} Excel файлов общим размером {total_size:.2f} МБ")
        
        # Таблица с файлами
        with st.expander("📋 Список файлов", expanded=True):
            # Создаем DataFrame для отображения
            files_df = pd.DataFrame([{
                'Файл': file['name'],
                'Размер (МБ)': f"{file['size_mb']:.2f}",
                'Изменен': file['modified'].strftime('%d.%m.%Y %H:%M')
            } for file in excel_files])
            
            st.dataframe(files_df, width="stretch")
        
        # Выбор файлов для удаления
        st.subheader("🗑️ Удаление файлов")
        
        file_options = [file['name'] for file in excel_files]
        selected_files = st.multiselect(
            "Выберите файлы для удаления:",
            options=file_options,
            help="Можно выбрать несколько файлов для удаления"
        )
        
        if selected_files:
            selected_size = sum(file['size_mb'] for file in excel_files if file['name'] in selected_files)
            st.warning(f"⚠️ Вы выбрали для удаления {len(selected_files)} файлов общим размером {selected_size:.2f} МБ")
            
            # Кнопка удаления
            if st.button("🗑️ Удалить выбранные файлы", type="secondary"):
                deleted_files, errors = delete_excel_files(selected_files)
                
                if deleted_files:
                    st.success(f"✅ Удалено {len(deleted_files)} файлов:")
                    for file_name, file_size in deleted_files:
                        st.write(f"• {file_name} ({file_size / (1024 * 1024):.2f} МБ)")
                    
                    # Обновляем страницу для отображения актуальных данных
                    st.rerun()
                
                if errors:
                    st.error("❌ Ошибки при удалении:")
                    for error in errors:
                        st.write(f"• {error}")
        
        # Кнопка удаления всех файлов
        st.markdown("---")
        st.subheader("🧹 Очистка всех файлов")
        
        if st.button("🗑️ Удалить все временные файлы", type="primary"):
            all_file_names = [file['name'] for file in excel_files]
            deleted_files, errors = delete_excel_files(all_file_names)
            
            if deleted_files:
                st.success(f"✅ Удалено всех файлов: {len(deleted_files)}")
                total_deleted_size = sum(size for _, size in deleted_files) / (1024 * 1024)
                st.info(f"Освобождено места: {total_deleted_size:.2f} МБ")
                
                # Обновляем страницу
                st.rerun()
            
            if errors:
                st.error(f"❌ Ошибки при удалении {len(errors)} файлов")
    else:
        st.success("✅ Временные файлы отсутствуют")
        
        # Кнопка обновления списка
        if st.button("🔄 Обновить список файлов"):
            st.rerun()
    
    # Информация о системе
    st.markdown("---")
    st.subheader("ℹ️ Информация о системе")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Версия Python:** {sys.version.split()[0]}")
        st.info(f"**Версия Streamlit:** {st.__version__}")
    with col2:
        st.info(f"**Текущая дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        st.info(f"**Рабочая директория:** {Path('.').absolute()}")

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
            if st.button("🚀 Сформировать отчет ТОП 400", type="primary", width="stretch"):
                reports()
        else:
            if st.button("🚀 Сформировать полный отчет", type="primary", width="stretch"):
                api_report()
                
    elif selected_menu == "Настройки":
        settings()

if __name__ == '__main__':
    main()