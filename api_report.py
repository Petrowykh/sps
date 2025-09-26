# import pandas as pd
# import requests
# import streamlit as st
# from api import post_json, PARAMS, HEADERS
# from pathlib import Path
# import datetime
# import time, sqlite3
# import logging

# # Настройка логирования
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def get_main_group():
#     try:
#         data_group = '{"CRC":"","Packet":{"FromId":"10003001","ServerKey":"omt5W465fjwlrtxcEco97kew2dkdrorqqq","Data":{}}}'
#         response = requests.post('https://api.infoprice.by/InfoPrice.GoodsGroup', params=PARAMS, headers=HEADERS, data=data_group, timeout=30)
#         response.raise_for_status()
#         main_group = response.json()
#         return {i['GoodsGroupName']: [i['GoodsGroupId'], i['Child']] for i in main_group['Table']}
#     except Exception as e:
#         st.error(f"Ошибка при получении главных групп: {e}")
#         return {}

# def create_data_group(group_id, page="", is_promo=False):
#     promo_flag = 1 if is_promo else 0
#     data = f'{{"CRC":"","Packet":{{"FromId":"10003001","ServerKey":"omt5W465fjwlrtxcEco97kew2dkdrorqqq","Data":{{"ContractorId":"","GoodsGroupId":"{group_id}","Page":"{page}","Search":"","OrderBy":0,"OrderByContractor":0,"CompareСontractorId":72631,"CatalogType":1,"IsAgeLimit":0,"IsPromotionalPrice":{promo_flag}}}}}}}'
#     return data.encode()

# def get_price_group(group_id, page, is_promo=False):
#     try:
#         data_price = create_data_group(group_id, page=page, is_promo=is_promo)
#         response = requests.post('https://api.infoprice.by/InfoPrice.Goods', params=PARAMS, headers=HEADERS, data=data_price, timeout=60)
#         response.raise_for_status()
#         return response.json()
#     except Exception as e:
#         st.error(f"Ошибка при получении {'промо-' if is_promo else ''}цен для группы {group_id}, страница {page}: {e}")
#         return None

# def process_goods(goods, main_name, is_promo=False):
#     processed_data = []
    
#     if 'GoodsOffer' not in goods or not goods['GoodsOffer']:
#         return processed_data
        
#     for data_good in goods['GoodsOffer']:
#         try:
#             goods_group_name = data_good.get('GoodsGroupName', '')
#             goods_name = data_good.get('GoodsName', '').rstrip()
#             goods_id = data_good.get('GoodsId', '')
            
#             if not goods_id:
#                 continue
                
#             prices = {72494: 0.00, 72512: 0.00, 72511: 0.00, 72517: 0.00, 72468: 0.00, 72526: 0.00}
            
#             if 'Offers' in data_good and data_good['Offers']:
#                 for price_contractor in data_good['Offers']:
#                     contractor_id = price_contractor.get('ContractorId')
#                     if contractor_id in prices:
#                         if not is_promo or (is_promo and price_contractor.get('IsPromotionalPrice', False)):
#                             try:
#                                 prices[contractor_id] = float(price_contractor.get('Price', 0))
#                             except:
#                                 prices[contractor_id] = 0.00
            
#             link = 'https://infoprice.by/?search=' + "+".join(goods_name.split(" "))
            
#             if is_promo:
#                 processed_data.append((goods_id, *prices.values()))
#             else:
#                 processed_data.append((goods_id, main_name, goods_group_name, goods_name, link, *prices.values()))
                
#         except Exception as e:
#             st.warning(f"Ошибка обработки товара: {e}")
#             continue
            
#     return processed_data

# def safe_get_pages_count(data):
#     """Безопасно получаем количество страниц"""
#     try:
#         if data and 'Table' in data and data['Table']:
#             general_data = data['Table'][0].get('GeneralData', [{}])[0]
#             return general_data.get('AmountPages', 0)
#     except (IndexError, KeyError, TypeError):
#         pass
#     return 0

# def safe_get_goods_data(data):
#     """Безопасно получаем данные о товарах"""
#     try:
#         if data and 'Table' in data and data['Table']:
#             for goods in data['Table']:
#                 general_data = goods.get('GeneralData', [{}])[0]
#                 amount_goods = general_data.get('AmountGoods', 0)
#                 if amount_goods > 0 and 'GoodsOffer' in goods:
#                     yield goods
#     except (IndexError, KeyError, TypeError):
#         pass

# def build_api_report():
#     """Сбор данных с API InfoPrice"""
#     st.header("📊 Сбор данных с API InfoPrice")
#     st.write("⏰ Процесс может занять несколько минут...")
    
#     # Проверка API
#     with st.spinner("Проверка доступности API..."):
#         try:
#             test_response = requests.get('https://api.infoprice.by', timeout=10)
#             if test_response.status_code != 200:
#                 st.error("❌ API недоступен")
#                 return None
#         except:
#             st.error("❌ API недоступен. Проверьте подключение к интернету.")
#             return None

#     # Получаем группы
#     with st.spinner("Получение списка категорий..."):
#         main_group = get_main_group()
    
#     if not main_group:
#         st.error("Не удалось получить данные о группах товаров")
#         return None

#     # Тестовый режим
#     # if st.toggle("🔧 Тестовый режим (3 категории)", value=True):
#     #     main_group = dict(list(main_group.items())[:3])
#     #     st.info(f"🔧 Тестовый режим: обрабатывается {len(main_group)} категорий")

#     columns = [
#         'good_id', 'category', 'subcategory', 'name', 'link',
#         'sosedi', 'sosedi_promo', 'korona', 'korona_promo', 
#         'gippo', 'gippo_promo', 'evroopt', 'evroopt_promo', 
#         'santa', 'santa_promo', 'green', 'green_promo'
#     ]
    
#     data_dict = {}
#     total_groups = sum(len(children) for _, children in main_group.values())
#     current_group = 0

#     # Основной прогресс-бар для всех групп
#     main_progress_bar = st.progress(0)
#     main_status_text = st.empty()

#     st.subheader("📋 Обработка категорий:")
    
#     for main_name in main_group.keys():
#         with st.expander(f"Категория: {main_name}", expanded=False):
#             children = main_group[main_name][1]
            
#             for group in children:
#                 current_group += 1
#                 group_id = group['GoodsGroupId']
#                 group_name = group.get('GoodsGroupName', f'Группа {group_id}')
                
#                 # Обновляем основной прогресс
#                 progress = current_group / total_groups
#                 main_progress_bar.progress(progress)
#                 main_status_text.text(f"Обработка: {group_name} ({current_group}/{total_groups})")
                
#                 st.write(f"🔄 Обработка группы: {group_name}")
                
#                 try:
#                     # Обработка обычных цен
#                     price_data = get_price_group(group_id, "")
#                     if price_data is None:
#                         st.warning(f"Пропускаем группу {group_name} из-за ошибки")
#                         continue

#                     pages_count = safe_get_pages_count(price_data)
#                     if pages_count == 0:
#                         st.write(f" ℹ️ Нет данных в группе {group_name}")
#                         continue

#                     # Прогресс-бар для страниц обычных цен
#                     st.write(f" 📄 Обычные цены: {pages_count} страниц")
#                     page_progress_bar = st.progress(0)
#                     page_status = st.empty()
                    
#                     regular_count = 0
#                     for page in range(pages_count):
#                         page_status.text(f"Страница {page + 1}/{pages_count}")
#                         page_progress_bar.progress((page + 1) / pages_count)
                        
#                         prices_page = get_price_group(group_id, str(page))
#                         if prices_page is None:
#                             st.warning(f"Пропускаем страницу {page} группы {group_name}")
#                             continue

#                         for goods in safe_get_goods_data(prices_page):
#                             processed_data = process_goods(goods, main_name)
#                             for row in processed_data:
#                                 good_id = row[0]
#                                 if good_id not in data_dict:
#                                     data_dict[good_id] = {col: 0.00 for col in columns}
#                                     data_dict[good_id]['good_id'] = good_id
#                                     data_dict[good_id]['category'] = row[1]
#                                     data_dict[good_id]['subcategory'] = row[2]
#                                     data_dict[good_id]['name'] = row[3]
#                                     data_dict[good_id]['link'] = row[4]
                                
#                                 # Обновляем обычные цены
#                                 data_dict[good_id]['sosedi'] = row[5]
#                                 data_dict[good_id]['korona'] = row[6]
#                                 data_dict[good_id]['gippo'] = row[7]
#                                 data_dict[good_id]['evroopt'] = row[8]
#                                 data_dict[good_id]['santa'] = row[9]
#                                 data_dict[good_id]['green'] = row[10]
#                                 regular_count += 1

#                         # Небольшая пауза между страницами
#                         time.sleep(0.1)
                    
#                     # Убираем прогресс-бар страниц
#                     page_progress_bar.empty()
#                     page_status.empty()

#                     # Обработка промо-цен
#                     promo_count = 0
#                     price_promo_data = get_price_group(group_id, "", is_promo=True)
#                     if price_promo_data:
#                         promo_pages_count = safe_get_pages_count(price_promo_data)
                        
#                         if promo_pages_count > 0:
#                             st.write(f" 🎯 Промо-цены: {promo_pages_count} страниц")
#                             promo_progress_bar = st.progress(0)
#                             promo_status = st.empty()
                            
#                             for page in range(promo_pages_count):
#                                 promo_status.text(f"Промо страница {page + 1}/{promo_pages_count}")
#                                 promo_progress_bar.progress((page + 1) / promo_pages_count)
                                
#                                 prices_promo_page = get_price_group(group_id, str(page), is_promo=True)
#                                 if prices_promo_page is None:
#                                     continue

#                                 for goods in safe_get_goods_data(prices_promo_page):
#                                     processed_promo_data = process_goods(goods, main_name, is_promo=True)
#                                     for row in processed_promo_data:
#                                         good_id = row[0]
#                                         if good_id in data_dict:  # Обновляем только существующие товары
#                                             data_dict[good_id]['sosedi_promo'] = row[1]
#                                             data_dict[good_id]['korona_promo'] = row[2]
#                                             data_dict[good_id]['gippo_promo'] = row[3]
#                                             data_dict[good_id]['evroopt_promo'] = row[4]
#                                             data_dict[good_id]['santa_promo'] = row[5]
#                                             data_dict[good_id]['green_promo'] = row[6]
#                                             promo_count += 1

#                                 # Небольшая пауза между страницами
#                                 time.sleep(0.1)
                            
#                             # Убираем прогресс-бар промо-страниц
#                             promo_progress_bar.empty()
#                             promo_status.empty()

#                     st.success(f" ✅ Группа {group_name} обработана: {regular_count} обычных + {promo_count} промо")

#                 except Exception as e:
#                     st.error(f" ❌ Ошибка обработки группы {group_name}: {e}")
#                     continue
                
#                 time.sleep(0.5)  # Пауза между группами

#     # Убираем основные элементы прогресса
#     main_progress_bar.empty()
#     main_status_text.empty()
    
#     if data_dict:
#         st.success(f"✅ Сбор данных завершен! Обработано товаров: {len(data_dict):,}")
        
#         # Показываем статистику
#         st.subheader("📈 Статистика по магазинам:")
#         stats_data = []
#         shops = ['sosedi', 'korona', 'gippo', 'evroopt', 'santa', 'green']
#         for shop in shops:
#             shop_count = sum(1 for product in data_dict.values() if product.get(shop, 0) > 0)
#             promo_count = sum(1 for product in data_dict.values() if product.get(f"{shop}_promo", 0) > 0)
#             stats_data.append({
#                 'Магазин': shop,
#                 'Товаров с обычными ценами': shop_count,
#                 'Товаров с промо ценами': promo_count
#             })
        
#         st.dataframe(pd.DataFrame(stats_data))
        
#         return {
#             'data': data_dict,
#             'columns': columns,
#             'stats': {
#                 'total_products': len(data_dict),
#                 'total_groups': total_groups
#             }
#         }
#     else:
#         st.error("❌ Не удалось собрать данные.")
#         return None

# def post_merge(src_file: Path | str) -> Path:
#     """Пост-обработка данных: подтягиваем штрих-коды"""
#     src_file = Path(src_file)
#     db_file = Path("products.db")

#     if not src_file.exists():
#         st.error(f"Не найден исходный файл: {src_file}")
#         return src_file

#     if not db_file.exists():
#         st.error(f"Не найдена БД: {db_file}")
#         return src_file

#     # Чтение данных
#     df_main = pd.read_excel(src_file)
    
#     with sqlite3.connect(db_file, check_same_thread=False) as conn:
#         df_bc = pd.read_sql("SELECT name, barcode FROM barcode", conn)

#     # Объединение
#     df = pd.merge(df_main, df_bc, how="left", on="name")
#     df = df.loc[:, ~df.columns.str.contains("^Unnamed: 0$")]

#     # Сохранение
#     ts = datetime.datetime.now().strftime("%d%m%Y_%H%M")
#     out_file = src_file.with_name(f"full{ts}.xlsx")
#     df.to_excel(out_file, index=False)

#     st.success(f"Post-merge завершён: {out_file.name}")
#     return out_file


import pandas as pd
import requests
import streamlit as st
from api import post_json, PARAMS, HEADERS
from pathlib import Path
import datetime
import time, sqlite3
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_main_group():
    try:
        data_group = '{"CRC":"","Packet":{"FromId":"10003001","ServerKey":"omt5W465fjwlrtxcEco97kew2dkdrorqqq","Data":{}}}'
        response = requests.post('https://api.infoprice.by/InfoPrice.GoodsGroup', params=PARAMS, headers=HEADERS, data=data_group, timeout=30)
        response.raise_for_status()
        main_group = response.json()
        return {i['GoodsGroupName']: [i['GoodsGroupId'], i['Child']] for i in main_group['Table']}
    except Exception as e:
        st.error(f"Ошибка при получении главных групп: {e}")
        return {}

def create_data_group(group_id, page="", is_promo=False):
    promo_flag = 1 if is_promo else 0
    data = f'{{"CRC":"","Packet":{{"FromId":"10003001","ServerKey":"omt5W465fjwlrtxcEco97kew2dkdrorqqq","Data":{{"ContractorId":"","GoodsGroupId":"{group_id}","Page":"{page}","Search":"","OrderBy":0,"OrderByContractor":0,"CompareСontractorId":72631,"CatalogType":1,"IsAgeLimit":0,"IsPromotionalPrice":{promo_flag}}}}}}}'
    return data.encode()

def get_price_group(group_id, page, is_promo=False):
    try:
        data_price = create_data_group(group_id, page=page, is_promo=is_promo)
        response = requests.post('https://api.infoprice.by/InfoPrice.Goods', params=PARAMS, headers=HEADERS, data=data_price, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Ошибка при получении {'промо-' if is_promo else ''}цен для группы {group_id}, страница {page}: {e}")
        return None

def process_goods(goods, main_name, is_promo=False):
    processed_data = []
    
    if 'GoodsOffer' not in goods or not goods['GoodsOffer']:
        return processed_data
        
    for data_good in goods['GoodsOffer']:
        try:
            goods_group_name = data_good.get('GoodsGroupName', '')
            goods_name = data_good.get('GoodsName', '').rstrip()
            goods_id = data_good.get('GoodsId', '')
            
            if not goods_id:
                continue
                
            prices = {72494: 0.00, 72512: 0.00, 72511: 0.00, 72517: 0.00, 72468: 0.00, 72526: 0.00}
            
            if 'Offers' in data_good and data_good['Offers']:
                for price_contractor in data_good['Offers']:
                    contractor_id = price_contractor.get('ContractorId')
                    if contractor_id in prices:
                        if not is_promo or (is_promo and price_contractor.get('IsPromotionalPrice', False)):
                            try:
                                prices[contractor_id] = float(price_contractor.get('Price', 0))
                            except:
                                prices[contractor_id] = 0.00
            
            link = 'https://infoprice.by/?search=' + "+".join(goods_name.split(" "))
            
            if is_promo:
                processed_data.append((goods_id, *prices.values()))
            else:
                processed_data.append((goods_id, main_name, goods_group_name, goods_name, link, *prices.values()))
                
        except Exception as e:
            st.warning(f"Ошибка обработки товара: {e}")
            continue
            
    return processed_data

def safe_get_pages_count(data):
    """Безопасно получаем количество страниц"""
    try:
        if data and 'Table' in data and data['Table']:
            general_data = data['Table'][0].get('GeneralData', [{}])[0]
            return general_data.get('AmountPages', 0)
    except (IndexError, KeyError, TypeError):
        pass
    return 0

def safe_get_goods_data(data):
    """Безопасно получаем данные о товарах"""
    try:
        if data and 'Table' in data and data['Table']:
            for goods in data['Table']:
                general_data = goods.get('GeneralData', [{}])[0]
                amount_goods = general_data.get('AmountGoods', 0)
                if amount_goods > 0 and 'GoodsOffer' in goods:
                    yield goods
    except (IndexError, KeyError, TypeError):
        pass

def has_regular_prices(prices_row):
    """Проверяет, есть ли хотя бы одна ненулевая обычная цена"""
    regular_price_columns = [5, 6, 7, 8, 9, 10]  # Индексы обычных цен в row
    return any(prices_row[i] > 0 for i in regular_price_columns)

def build_api_report():
    """Сбор данных с API InfoPrice"""
    st.header("📊 Сбор данных с API InfoPrice")
    st.write("⏰ Процесс может занять несколько минут...")
    
    # Проверка API
    with st.spinner("Проверка доступности API..."):
        try:
            test_response = requests.get('https://api.infoprice.by', timeout=10)
            if test_response.status_code != 200:
                st.error("❌ API недоступен")
                return None
        except:
            st.error("❌ API недоступен. Проверьте подключение к интернету.")
            return None

    # Получаем группы
    with st.spinner("Получение списка категорий..."):
        main_group = get_main_group()
    
    if not main_group:
        st.error("Не удалось получить данные о группах товаров")
        return None

    # Тестовый режим
    # if st.toggle("🔧 Тестовый режим (3 категории)", value=True):
    #     main_group = dict(list(main_group.items())[:3])
    #     st.info(f"🔧 Тестовый режим: обрабатывается {len(main_group)} категорий")

    columns = [
        'good_id', 'category', 'subcategory', 'name', 'link',
        'sosedi', 'sosedi_promo', 'korona', 'korona_promo', 
        'gippo', 'gippo_promo', 'evroopt', 'evroopt_promo', 
        'santa', 'santa_promo', 'green', 'green_promo'
    ]
    
    data_dict = {}
    total_groups = sum(len(children) for _, children in main_group.values())
    current_group = 0

    # Основной прогресс-бар для всех групп
    main_progress_bar = st.progress(0)
    main_status_text = st.empty()

    st.subheader("📋 Обработка категорий:")
    
    for main_name in main_group.keys():
        with st.expander(f"Категория: {main_name}", expanded=False):
            children = main_group[main_name][1]
            
            for group in children:
                current_group += 1
                group_id = group['GoodsGroupId']
                group_name = group.get('GoodsGroupName', f'Группа {group_id}')
                
                # Обновляем основной прогресс
                progress = current_group / total_groups
                main_progress_bar.progress(progress)
                main_status_text.text(f"Обработка: {group_name} ({current_group}/{total_groups})")
                
                st.write(f"🔄 Обработка группы: {group_name}")
                
                try:
                    # Обработка обычных цен
                    price_data = get_price_group(group_id, "")
                    if price_data is None:
                        st.warning(f"Пропускаем группу {group_name} из-за ошибки")
                        continue

                    pages_count = safe_get_pages_count(price_data)
                    if pages_count == 0:
                        st.write(f" ℹ️ Нет данных в группе {group_name}")
                        continue

                    # Прогресс-бар для страниц обычных цен
                    st.write(f" 📄 Обычные цены: {pages_count} страниц")
                    page_progress_bar = st.progress(0)
                    page_status = st.empty()
                    
                    regular_count = 0
                    valid_products_count = 0  # Счетчик товаров с обычными ценами
                    
                    for page in range(pages_count):
                        page_status.text(f"Страница {page + 1}/{pages_count}")
                        page_progress_bar.progress((page + 1) / pages_count)
                        
                        prices_page = get_price_group(group_id, str(page))
                        if prices_page is None:
                            st.warning(f"Пропускаем страницу {page} группы {group_name}")
                            continue

                        for goods in safe_get_goods_data(prices_page):
                            processed_data = process_goods(goods, main_name)
                            for row in processed_data:
                                # Проверяем, есть ли обычные цены
                                if has_regular_prices(row):
                                    good_id = row[0]
                                    if good_id not in data_dict:
                                        data_dict[good_id] = {col: 0.00 for col in columns}
                                        data_dict[good_id]['good_id'] = good_id
                                        data_dict[good_id]['category'] = row[1]
                                        data_dict[good_id]['subcategory'] = row[2]
                                        data_dict[good_id]['name'] = row[3]
                                        data_dict[good_id]['link'] = row[4]
                                    
                                    # Обновляем обычные цены
                                    data_dict[good_id]['sosedi'] = row[5]
                                    data_dict[good_id]['korona'] = row[6]
                                    data_dict[good_id]['gippo'] = row[7]
                                    data_dict[good_id]['evroopt'] = row[8]
                                    data_dict[good_id]['santa'] = row[9]
                                    data_dict[good_id]['green'] = row[10]
                                    valid_products_count += 1
                                
                                regular_count += 1

                        # Небольшая пауза между страницами
                        time.sleep(0.1)
                    
                    # Убираем прогресс-бар страниц
                    page_progress_bar.empty()
                    page_status.empty()

                    # Обработка промо-цен только если есть товары с обычными ценами
                    promo_count = 0
                    if valid_products_count > 0:
                        price_promo_data = get_price_group(group_id, "", is_promo=True)
                        if price_promo_data:
                            promo_pages_count = safe_get_pages_count(price_promo_data)
                            
                            if promo_pages_count > 0:
                                st.write(f" 🎯 Промо-цены: {promo_pages_count} страниц")
                                promo_progress_bar = st.progress(0)
                                promo_status = st.empty()
                                
                                for page in range(promo_pages_count):
                                    promo_status.text(f"Промо страница {page + 1}/{promo_pages_count}")
                                    promo_progress_bar.progress((page + 1) / promo_pages_count)
                                    
                                    prices_promo_page = get_price_group(group_id, str(page), is_promo=True)
                                    if prices_promo_page is None:
                                        continue

                                    for goods in safe_get_goods_data(prices_promo_page):
                                        processed_promo_data = process_goods(goods, main_name, is_promo=True)
                                        for row in processed_promo_data:
                                            good_id = row[0]
                                            # Обновляем промо-цены только для товаров, которые уже есть в data_dict
                                            if good_id in data_dict:
                                                data_dict[good_id]['sosedi_promo'] = row[1]
                                                data_dict[good_id]['korona_promo'] = row[2]
                                                data_dict[good_id]['gippo_promo'] = row[3]
                                                data_dict[good_id]['evroopt_promo'] = row[4]
                                                data_dict[good_id]['santa_promo'] = row[5]
                                                data_dict[good_id]['green_promo'] = row[6]
                                                promo_count += 1

                                    # Небольшая пауза между страницами
                                    time.sleep(0.1)
                                
                                # Убираем прогресс-бар промо-страниц
                                promo_progress_bar.empty()
                                promo_status.empty()
                    else:
                        st.write(f" ℹ️ В группе {group_name} нет товаров с обычными ценами, промо-цены не обрабатываются")

                    st.success(f" ✅ Группа {group_name} обработана: {valid_products_count} валидных товаров (из {regular_count} всего) + {promo_count} промо")

                except Exception as e:
                    st.error(f" ❌ Ошибка обработки группы {group_name}: {e}")
                    continue
                
                time.sleep(0.5)  # Пауза между группами

    # Убираем основные элементы прогресса
    main_progress_bar.empty()
    main_status_text.empty()
    
    if data_dict:
        st.success(f"✅ Сбор данных завершен! Обработано товаров: {len(data_dict):,}")
        
        # Показываем статистику
        st.subheader("📈 Статистика по магазинам:")
        stats_data = []
        shops = ['sosedi', 'korona', 'gippo', 'evroopt', 'santa', 'green']
        for shop in shops:
            shop_count = sum(1 for product in data_dict.values() if product.get(shop, 0) > 0)
            promo_count = sum(1 for product in data_dict.values() if product.get(f"{shop}_promo", 0) > 0)
            stats_data.append({
                'Магазин': shop,
                'Товаров с обычными ценами': shop_count,
                'Товаров с промо ценами': promo_count
            })
        
        st.dataframe(pd.DataFrame(stats_data))
        
        return {
            'data': data_dict,
            'columns': columns,
            'stats': {
                'total_products': len(data_dict),
                'total_groups': total_groups
            }
        }
    else:
        st.error("❌ Не удалось собрать данные.")
        return None

def post_merge(src_file: Path | str) -> Path:
    """Пост-обработка данных: подтягиваем штрих-коды"""
    src_file = Path(src_file)
    db_file = Path("products.db")

    if not src_file.exists():
        st.error(f"Не найден исходный файл: {src_file}")
        return src_file

    if not db_file.exists():
        st.error(f"Не найдена БД: {db_file}")
        return src_file

    # Чтение данных
    df_main = pd.read_excel(src_file)
    
    with sqlite3.connect(db_file, check_same_thread=False) as conn:
        df_bc = pd.read_sql("SELECT name, barcode FROM barcode", conn)

    # Объединение
    df = pd.merge(df_main, df_bc, how="left", on="name")
    df = df.loc[:, ~df.columns.str.contains("^Unnamed: 0$")]

    # Сохранение
    ts = datetime.datetime.now().strftime("%d%m%Y_%H%M")
    out_file = src_file.with_name(f"full{ts}.xlsx")
    df.to_excel(out_file, index=False)

    st.success(f"Post-merge завершён: {out_file.name}")
    return out_file