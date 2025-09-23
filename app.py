# sps – system of parsing (Sosedi)
# version 0.4  (auth + убрано streamlit-option-menu)

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

import myparser as mp
#import myutils as mu

# ----------  AUTH  ----------
USERS_FILE = Path("users.txt")   # login:hash  (одна строка – один пользователь)

def _load_users() -> dict[str, str]:
    """{login: password}"""
    if not USERS_FILE.exists():
        # создаём демо-запись
        USERS_FILE.write_text("demo:123\n")
    users = {}
    for line in USERS_FILE.read_text().splitlines():
        if ":" in line:
            login, pwd = line.strip().split(":", 1)
            users[login] = pwd
    return users

def check_password(login: str, password: str) -> bool:
    """Проверка без шифрования."""
    users = _load_users()
    return users.get(login) == password

def login_form():
    """Показывает форму логина. При успехе ставит st.session_state['auth']=True"""
    st.title("Вход в систему")
    with st.form("login"):
        login = st.text_input("Логин")
        pwd   = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти"):
            if check_password(login, pwd):
                st.session_state["auth"] = True
                st.session_state["user"] = login
                st.rerun()
            else:
                st.error("Неверный логин или пароль")

# ----------  UI  ----------
def info():
    st.sidebar.title('Поиск товара')
    barcode = st.sidebar.text_input('Введите ш/к')
    if st.sidebar.button('Ищем'):
        try:
            with st.spinner('Ищем товар...'):
                infoprice = mp.ParserInfoAll()
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
    type_report = st.sidebar.selectbox('Выберите отчет', ('TOP-1000', 'CTM'))
    email = st.sidebar.text_input('Введите email', placeholder='email@mail.ru')
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
        infoprice = mp.ParserInfoAll()
        for count, barcode in enumerate(sku['barcode']):
            try:
                parse_bar.progress(int((count + 1) / total_items * 100))
                barcode = str(int(barcode)) if pd.notna(barcode) else '0'
                link = f'https://infoprice.by/?search= {barcode}&filter%5B%5D=72494&filter%5B%5D=72468&filter%5B%5D=72512&filter%5B%5D=72517&filter%5B%5D=72511&filter%5B%5D=72526'
                name, min_price, promo, rrr = infoprice.get_price(link)
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
        result_df = pd.DataFrame.from_dict(result_dict).fillna(0.0)
        filename = f"report_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
        result_df.to_excel(filename)
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