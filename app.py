# sps - system of parsing (Sosedi)

# version 0.1


import streamlit as st
from streamlit_option_menu import option_menu
import myparser as mp
import myutils as mu

import time



def info():
    infoprice = mp.ParserInfo()
    barcode = st.sidebar.text_input('Введите ш/к')
    if st.sidebar.button('Ищем'):
        link = 'https://infoprice.by/?search=' + barcode
        st.text(link)
        
        name, rrr = infoprice.get_price(link)
        if name != None:
            st.subheader(name)
            st.table(rrr)
        else:
            st.subheader('Товар не найден')
    
    

def reports():
    parse_bar = st.progress(0, 'Начинаем парсинг')
    array_price = []
    sku = mu.load_sku('excel/new_sku.xlsx').fillna('')
    #st.table(sku)
    part_of_parse = 50/sku.shape[0]
    st.sidebar.title('Отчеты')
    st.sidebar.selectbox(
        'Выберите отчет',
        ('TOP-100', 'Цена 1000')
    )
    st.sidebar.multiselect('Включать данные',
                   ['ГИППО', 'Евроторг', 'Санта'])
    sku['gippo_price'] = 0
    sku['eurotorg_price'] = 0
    email = st.sidebar.text_input('Введите email', placeholder='email@mail.ru')
    email_flag = True
    if email:
        email_flag = False
    if st.sidebar.button('Сформировать', disabled=email_flag):
        gippo = mp.ParserGippo()
        
        links = sku['gippo']
        
        for count, link in enumerate(links):
            parse_bar.progress(int(count*part_of_parse), 'Гиппо')
            if link != '':
                array_price.append(gippo.get_price(gippo.get_page(link)))
            else:
                array_price.append(0)
        sku['gippo_price'] = array_price
        sku['gippo_price'] = sku['gippo_price'].apply(lambda x: round(x, 2))

        eurotorg = mp.ParserEurotorg()
        links = sku['eurotorg']
        array_price = []
        first_step = True
        for count, link in enumerate(links):
            parse_bar.progress(int(50+count*part_of_parse), 'Евроторг')
            if link != '':
                res = eurotorg.get_price(link, first_step)
                
                first_step = False
                array_price.append(res)
            else:
                array_price.append(0)
        sku['eurotorg_price'] = array_price
        sku['eurotorg_price'] = sku['eurotorg_price'].apply(lambda x: round(x, 2))

        #st.table(sku[['code', 'name', 'gippo_price', 'eurotorg_price']])
        ready_excel = sku[['code', 'name', 'gippo_price', 'eurotorg_price']]
        ready_excel.to_excel('ready.xlsx')
        parse_bar.progress(int(100), 'Готово!')
        mu.send_letter(email, 'ready.xlsx')
        st.success('Все хорошо')



            
    

def settings():
    pass

menu_dict = {
    "Информация" : info,
    "Отчеты": reports,
    "Настройки": settings,
}

def main():
    

    st.set_page_config(
        page_title="Sosedi Parsing System",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
        
        )
    col_img, col_header = st.columns([1,2])
    col_img.image('img/logo.png',width=200)
    col_header.header('Система парсинга данных')
    select_menu = option_menu(None, ["Информация", "Отчеты", "Настройки"], 
        icons=["info-square", 'bar-chart-fill', 'gear'], 
        menu_icon="cast", default_index=0, orientation="horizontal",
        styles={
            "nav-link-selected": {"background-color": "#314264"}
        })
    if select_menu in menu_dict.keys():   
        menu_dict[select_menu]()



if __name__=='__main__':
    main()