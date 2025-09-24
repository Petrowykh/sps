# sps – system of parsing (Sosedi)
# version 0.4  (auth + убрано streamlit-option-menu)

import streamlit as st
import pandas as pd
from datetime import datetime
from api_report import build_api_report, post_merge
from pathlib import Path
from infoparser import get_price_by_barcode
#import myutils as mu

# ----------  AUTH  ----------
# ---------- ВРЕМЕННО: захардкожены ----------
LOGIN = "admin"
PASSWORD = "12345"
# ---------------------------------------------


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


def info():

    st.title("Поиск товара по штрих-коду")
    col1, col2 = st.columns([3, 1])
    with col1:
        barcode = st.text_input("Введите штрих-код", key="barcode_input")
    with col2:
        search = st.button("Искать", type="primary", key="search_btn")

    if search and barcode.strip():          # нажали и ввели
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
    elif search and not barcode.strip():    # нажали, но не ввели
        st.warning("Введите штрих-код")


def reports():
    try:
        sku = pd.read_excel('excel/new3.xlsx')
        if sku.empty:
            st.warning("Файл с товарами пуст или не найден")
            return
        st.table(sku.head(5))
        total_items = sku.shape[0]
        parse_bar = st.progress(0, 'Начинаем парсинг')

        result_dict = {
            'name': [], 'barcode': [], 'link_foto': [],
            'min_price': [], 'promo': [], 'sosedi': [],
            'santa': [], 'korona': [], 'evroopt': [],
            'gippo': [], 'grin': []
        }

        # --------------  HTTP-вариант  --------------

        for count, barcode in enumerate(sku['barcode']):
            try:
                parse_bar.progress(int((count + 1) / total_items * 100))
                barcode = str(int(barcode)) if pd.notna(barcode) else '0'

                info = get_price_by_barcode(barcode)
                name, min_price, promo, rrr = info.name, info.min_price, info.min_promo, info.shops

                if name != 'Не найдено':
                    result_dict['name'].append(name)
                    link = f"https://infoprice.by/?search={barcode}"
                    result_dict['link_foto'].append(link)
                    result_dict['min_price'].append(min_price)   # ← сюда пишем
                    result_dict['promo'].append(promo if promo != 10000.0 else 0.0)
                    result_dict['barcode'].append(barcode)

                    shops_mapping = {
                        'sosedi': 'Соседи', 'santa': 'Санта', 'korona': 'Корона',
                        'evroopt': 'Евроопт', 'gippo': 'Гиппо', 'grin': 'Грин'
                    }
                    for code, shop_name in shops_mapping.items():
                        result_dict[code].append(rrr.get(shop_name, 0.0))
            except Exception as e:
                print(f"Ошибка при обработке штрих-кода {barcode}: {str(e)}")
                for key in result_dict:
                    result_dict[key].append(0.0 if key in ['min_price', 'promo', 'sosedi', 'santa', 'korona', 'evroopt', 'gippo', 'grin'] else '')
                continue

        result_df = pd.DataFrame.from_dict(result_dict).fillna(0.0)
        filename = f"report_{datetime.now().strftime('%d%m%Y')}.xlsx"
        result_df.insert(0, "№", range(1, len(result_df) + 1))
        result_df.to_excel(filename, sheet_name="Парсинг 400", index=False)

        with open(filename, "rb") as f:
            st.download_button(
                label="📥 Скачать отчёт",
                data=f,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.success(f"Отчет успешно сформирован! Сохранен как {filename}")

    except Exception as e:
        st.error(f'Критическая ошибка при формировании отчета: {str(e)}')


def api_report():
    ts = datetime.now().strftime("%d%m%Y")
    raw_file = Path(f"api_report_{ts}.xlsx")
    
    build_api_report(raw_file)

# ----------  MAIN  ----------
def main():
    st.set_page_config(
        page_title="Sosedi Parsing System",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # если пользователь ещё не авторизован – показываем форму
    if not st.session_state.get("auth", False):
        login_form()
        st.stop()

    # авторизован – рисуем шапку и меню-переключалку
    col_img, col_header = st.columns([1, 2])
    col_img.image('img/logo.png', width=200)
    col_header.header('Система парсинга данных')

    menu = st.sidebar.radio(
        "Разделы",
        ["Информация", "Отчет ТОП 400", "Полный отчет"],
        key="main_menu",
    )

    # кнопка «Выполнить» – только для отчётов, для поиска – своя внутри info()
    if menu != "Информация":
        btn_text = {"Отчет ТОП 400": "📊 Сделать", "Полный отчет": "📦 Сделать"}.get(menu, "Выполнить")
        if st.sidebar.button(btn_text, type="primary", key="exec_btn"):
            if menu == "Отчет ТОП 400":
                reports()
            elif menu == "Полный отчет":
                api_report()
    else:
        info()
    
    

if __name__ == '__main__':
    main()