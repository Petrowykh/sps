# sps - system of parsing (Sosedi)

# version 0.1


import streamlit as st
from streamlit_option_menu import option_menu
import myparser as mp
import myutils as mu
import pandas as pd

import time



def info():
    
    barcode = st.sidebar.text_input('Введите ш/к')
    if st.sidebar.button('Ищем'):
        infoprice = mp.ParserInfoAll()
        link = 'https://infoprice.by/?search=' + barcode + '&filter%5B%5D=72494&filter%5B%5D=72468&filter%5B%5D=72512&filter%5B%5D=72517&filter%5B%5D=72511&filter%5B%5D=72526'
        st.text(link)
        
        name, rrr, ddd = infoprice.get_price(link)
        if name != None:
            st.subheader(name)
            st.table(rrr)
            st.table(ddd)
        else:
            st.subheader('Товар не найден')
    
    

# def reports1():
#     parse_bar = st.progress(0, 'Начинаем парсинг')
#     array_price = []
#     sku = mu.load_sku('excel/new_sku.xlsx').fillna('')
#     #st.table(sku)
#     part_of_parse = 50/sku.shape[0]
#     st.sidebar.title('Отчеты')
#     st.sidebar.selectbox(
#         'Выберите отчет',
#         ('TOP-100', 'Цена 1000')
#     )
#     st.sidebar.multiselect('Включать данные',
#                    ['ГИППО', 'Евроторг', 'Санта'])
#     sku['gippo_price'] = 0
#     sku['eurotorg_price'] = 0
#     email = st.sidebar.text_input('Введите email', placeholder='email@mail.ru')
#     email_flag = True
#     if email:
#         email_flag = False
#     if st.sidebar.button('Сформировать', disabled=email_flag):
#         gippo = mp.ParserGippo()
        
#         links = sku['gippo']
        
#         for count, link in enumerate(links):
#             parse_bar.progress(int(count*part_of_parse), 'Гиппо')
#             if link != '':
#                 array_price.append(gippo.get_price(gippo.get_page(link)))
#             else:
#                 array_price.append(0)
#         sku['gippo_price'] = array_price
#         sku['gippo_price'] = sku['gippo_price'].apply(lambda x: round(x, 2))

#         eurotorg = mp.ParserEurotorg()
#         links = sku['eurotorg']
#         array_price = []
#         first_step = True
#         for count, link in enumerate(links):
#             parse_bar.progress(int(50+count*part_of_parse), 'Евроторг')
#             if link != '':
#                 res = eurotorg.get_price(link, first_step)
                
#                 first_step = False
#                 array_price.append(res)
#             else:
#                 array_price.append(0)
#         sku['eurotorg_price'] = array_price
#         sku['eurotorg_price'] = sku['eurotorg_price'].apply(lambda x: round(x, 2))

#         #st.table(sku[['code', 'name', 'gippo_price', 'eurotorg_price']])
#         ready_excel = sku[['code', 'name', 'gippo_price', 'eurotorg_price']]
#         ready_excel.to_excel('ready.xlsx')
#         parse_bar.progress(int(100), 'Готово!')
#         mu.send_letter(email, 'ready.xlsx')
#         st.success('Все хорошо')

def reports():
    parse_bar = st.progress(0, 'Начинаем парсинг')
    
    sku = mu.load_sku('excel/new2.xlsx').fillna('')
    #st.table(sku)
    part_of_parse = 100/sku.shape[0]
    st.sidebar.title('Отчеты')
    type_report = st.sidebar.selectbox(
        'Выберите отчет',
        ('TOP-1000', 'CTM')
    )
    email = st.sidebar.text_input('Введите email', placeholder='email@mail.ru')
    if st.sidebar.button('Сформировать'):
        if type_report == 'TOP-1000':
            result_dict = {'name':[],'barcode':[], 'link_foto':[], 'min_price':[], 'promo':[],'sosedi':[],'santa':[],'korona':[],'evroopt':[], 'gippo':[],'grin':[]}
            infoprice = mp.ParserInfoAll()
            barcodes = sku['barcode']
            for count, barcode in enumerate(barcodes):
                
                parse_bar.progress(int(count*part_of_parse))
                link = 'https://infoprice.by/?search=' + str(int(barcode)) + '&filter%5B%5D=72494&filter%5B%5D=72468&filter%5B%5D=72512&filter%5B%5D=72517&filter%5B%5D=72511&filter%5B%5D=72526'
                name, min_price, promo, rrr = infoprice.get_price(link)
                if name != 'Не найден':
                    result_dict['name'].append(name)
                    result_dict['link_foto'].append(link)
                    result_dict['min_price'].append(min_price)
                    if promo == 10000.0:
                        result_dict['promo'].append(0.0)
                    else:
                        result_dict['promo'].append(promo)
                    
                    result_dict['barcode'].append(str(int(barcode)))
                    result_dict['sosedi'].append(rrr.get('Соседи'))
                    #result_dict['sosedi_date'].append(ddd.get('Соседи'))
                    result_dict['santa'].append(rrr.get('Санта'))
                    #result_dict['santa_date'].append(ddd.get('Санта'))
                    result_dict['korona'].append(rrr.get('Корона'))
                    #result_dict['korona_date'].append(ddd.get('Корона'))
                    result_dict['evroopt'].append(rrr.get('Евроопт'))
                    #result_dict['evroopt_date'].append(ddd.get('Евроопт'))
                    result_dict['gippo'].append(rrr.get('Гиппо'))
                    #result_dict['gippo_date'].append(ddd.get('Гиппо'))
                    result_dict['grin'].append(rrr.get('Грин'))
                    #result_dict['grin_date'].append(ddd.get('Грин'))
            result_df = pd.DataFrame.from_dict(result_dict)
            result_df = result_df.fillna(0.0)
            result_df.to_excel('ready.xlsx')
            st.table(result_df)
        else:
            gippo = mp.ParserGippoVery()
            last_page = gippo.get_last_page(gippo.get_page('https://gippo-market.by/catalog/brands/alinor/'))
            itog_name = []
            itog_price = []
            itog_barcode = []
            
            for page in range(last_page):
                link_step = "https://gippo-market.by/catalog/brands/alinor/?PAGEN_2=" + str(page+1)
                res = gippo.get_links(gippo.get_page(link_step)) 
                itog_barcode = itog_barcode + res[0]
                itog_name = itog_name + res[1]
                itog_price = itog_price + res[2]  
            itog = pd.DataFrame({'barcode': itog_barcode,
                                'name': itog_name,
                                'price': itog_price}) 
                       
            itog.to_excel('gippo_stm.xlsx')
            st.table(itog)         
                


            
    

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