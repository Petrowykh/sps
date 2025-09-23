# sps – system of parsing (Sosedi)
# version 0.4  (auth + убрано streamlit-option-menu)

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

import myparser as mp
#import myutils as mu

# ----------  AUTH  ----------
# ---------- ВРЕМЕННО: захардкожены ----------
LOGIN = "admin"
PASSWORD = "12345"
# ---------------------------------------------
@st.cache_resource(show_spinner=False)
def get_driver():
    return mp.ParserInfoAll()

driver = get_driver()

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
    st.sidebar.title('Поиск товара')
    barcode = st.sidebar.text_input('Введите ш/к')
    if st.sidebar.button('Ищем'):
        try:
            with st.spinner('Ищем товар...'):
                infoprice = driver
                link = f'https://infoprice.by/?search= {barcode}&filter%5B%5D=72494&filter%5B%5D=72468&filter%5B%5D=72512&filter%5B%5D=72517&filter%5B%5D=72511&filter%5B%5D=72526'
                st.text(link)
                name, rrr, ddd = infoprice.get_price(link)
                if name != 'Не найден':
                    st.subheader(name)
                    st.table(rrr)
                    st.table(ddd)
                else:
                    st.warning('Товар не найден')
                infoprice.close()
        except Exception as e:
            st.error(f'Ошибка при поиске товара: {str(e)}')

def reports():
    st.sidebar.title('Отчеты')
    # type_report = st.sidebar.selectbox('Выберите отчет', ('TOP-1000', 'CTM'))
    # email = st.sidebar.text_input('Введите email', placeholder='email@mail.ru')
    if not st.sidebar.button('Сформировать'):
        return
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
        infoprice = driver
        for count, barcode in enumerate(sku['barcode'].head(10)):
            try:
                parse_bar.progress(int((count + 1) / total_items * 100))
                barcode = str(int(barcode)) if pd.notna(barcode) else '0'
                link = f'https://infoprice.by/?search={barcode}&filter%5B%5D=72494&filter%5B%5D=72468&filter%5B%5D=72512&filter%5B%5D=72517&filter%5B%5D=72511&filter%5B%5D=72526'
                info = infoprice.get_price(link)
                name, min_price, promo, rrr = info.name, info.min_price, info.min_promo, info.shops
                print(f"{name}, {barcode}")
                if name != 'Не найден':
                    result_dict['name'].append(name)
                    result_dict['link_foto'].append(link)
                    result_dict['min_price'].append(min_price)
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
        infoprice.close()
        result_df = pd.DataFrame.from_dict(result_dict).fillna(0.0)
        filename = f"report_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
        result_df.to_excel(filename)

        # ---- кнопка скачивания ----
        with open(filename, "rb") as f:
            st.download_button(
                label="📥 Скачать отчёт",
                data=f,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        # ---------------------------

        st.success(f"Отчет успешно сформирован! Сохранен как {filename}")
        st.table(result_df.head(10))

    except Exception as e:
        st.error(f'Критическая ошибка при формировании отчета: {str(e)}')
    finally:
        if 'infoprice' in locals():
            infoprice.close()

def settings():
    st.sidebar.title('Настройки')
    st.write("Здесь будут настройки системы")

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
        ["Информация", "Отчеты", "Настройки"],
        index=0
    )
    if menu == "Информация":
        info()
    elif menu == "Отчеты":
        reports()
    elif menu == "Настройки":
        settings()

if __name__ == '__main__':
    main()