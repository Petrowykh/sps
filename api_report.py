import pandas as pd
import requests
import streamlit as st
from api import post_json, PARAMS, HEADERS
from pathlib import Path
import datetime
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    pass

def timeout_handler():
    raise TimeoutException("Таймаут операции")

def run_with_timeout(func, timeout_seconds, *args, **kwargs):
    """Выполняет функцию с таймаутом"""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            raise TimeoutException(f"Таймаут после {timeout_seconds} секунд")

# Глобальная сессия с повторными попытками
def create_session():
    """Создает сессию с повторными попытками и таймаутами"""
    session = requests.Session()
    
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    retry_strategy = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# Создаем глобальную сессию
SESSION = create_session()

def get_main_group():
    try:
        data_group = '{"CRC":"","Packet":{"FromId":"10003001","ServerKey":"omt5W465fjwlrtxcEco97kew2dkdrorqqq","Data":{}}}'
        response = SESSION.post('https://api.infoprice.by/InfoPrice.GoodsGroup', params=PARAMS, headers=HEADERS, data=data_group, timeout=30)
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
    """Получение данных группы с улучшенной обработкой ошибок"""
    max_retries = 2
    base_timeout = 45
    
    for attempt in range(max_retries):
        try:
            data = create_data_group(group_id, page=page, is_promo=is_promo)
            timeout = base_timeout * (attempt + 1)
            
            response = SESSION.post(
                'https://api.infoprice.by/InfoPrice.Goods', 
                params=PARAMS, 
                headers=HEADERS, 
                data=data,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                st.error(f"Таймаут после {max_retries} попыток для группы {group_id}, страница {page}")
                raise
            else:
                wait_time = 3 * (attempt + 1)
                st.warning(f"Таймаут попытка {attempt + 1}/{max_retries}. Ждем {wait_time} сек...")
                time.sleep(wait_time)
                
        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                st.error(f"Ошибка соединения после {max_retries} попыток для группы {group_id}")
                raise
            else:
                wait_time = 5 * (attempt + 1)
                st.warning(f"Ошибка соединения попытка {attempt + 1}/{max_retries}. Ждем {wait_time} сек...")
                time.sleep(wait_time)
                
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"Ошибка после {max_retries} попыток для группы {group_id}: {e}")
                raise
            else:
                wait_time = 2 * (attempt + 1)
                st.warning(f"Ошибка попытка {attempt + 1}/{max_retries}. Ждем {wait_time} сек...")
                time.sleep(wait_time)
    
    return None

def process_goods(goods, main_name, is_promo=False):
    processed_data = []
    
    if 'GoodsOffer' not in goods or not goods['GoodsOffer']:
        return processed_data
        
    for data_good in goods['GoodsOffer']:
        goods_group_name = data_good.get('GoodsGroupName', '')
        goods_name = data_good.get('GoodsName', '').rstrip()
        goods_id = data_good.get('GoodsId', '')
        
        if not goods_id:
            continue
            
        prices = {72494: 0.00, 72512: 0.00, 72511: 0.00, 72517: 0.00, 72468: 0.00, 72526: 0.00}
        has_any_price = False
        has_promo_price = False
        
        if 'Offers' in data_good and data_good['Offers']:
            for price_contractor in data_good['Offers']:
                contractor_id = price_contractor.get('ContractorId')
                if contractor_id in prices:
                    price_value = float(price_contractor.get('Price', 0))
                    is_promo_price = price_contractor.get('IsPromotionalPrice', False)
                    
                    if not is_promo:
                        # Для обычного запроса - берем все цены
                        prices[contractor_id] = price_value
                        if price_value > 0:
                            has_any_price = True
                    else:
                        # Для промо-запроса - берем только промо-цены
                        if is_promo_price:
                            prices[contractor_id] = price_value
                            has_promo_price = True
        
        # Для обычного режима: добавляем если есть хотя бы одна цена
        if not is_promo:
            if not has_any_price:
                continue
        # Для промо-режима: добавляем только если есть промо-цены
        else:
            if not has_promo_price:
                continue
        
        link = 'https://infoprice.by/?search=' + "+".join(goods_name.split(" "))
        
        if is_promo:
            processed_data.append((goods_id, *prices.values()))
        else:
            processed_data.append((goods_id, main_name, goods_group_name, goods_name, link, *prices.values()))
    
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

def _store_row(row: tuple, cols: list, dd: dict) -> None:
    gid = row[0]
    if gid not in dd:
        dd[gid] = {c: 0.0 for c in cols}
        dd[gid]["good_id"], dd[gid]["category"], dd[gid]["subcategory"], dd[gid]["name"], dd[gid]["link"] = row[:5]
    for idx, col in enumerate(cols[5:11], start=5):
        dd[gid][col] = row[idx]

def _store_promo(row: tuple, cols: list, dd: dict) -> None:
    gid = row[0]
    # Добавляем промо-цены ТОЛЬКО если товар уже существует
    if gid in dd:
        for idx, col in enumerate(cols[11:], start=1):
            # Обновляем только если промо-цена не нулевая
            if row[idx] > 0:
                dd[gid][col] = row[idx]

def safe_process_group(gid, gname, main_name, data_dict, columns):
    """Обработка группы с защитой от зависаний"""
    
    def process_single_group(group_id, group_name, is_promo=False):
        """Обработка одной группы (обычные или промо цены)"""
        try:
            # Получаем общую информацию с таймаутом
            general_data = run_with_timeout(
                get_price_group, 120, group_id, "", is_promo
            )
            
            if not general_data:
                return 0
                
            pages_count = safe_get_pages_count(general_data)
            if pages_count == 0:
                return 0
            
            processed_goods = 0
            
            # Обрабатываем страницы с индивидуальными таймаутами
            for page in range(pages_count):
                try:
                    page_data = run_with_timeout(
                        get_price_group, 180, group_id, str(page), is_promo
                    )
                    
                    if page_data:
                        for goods in safe_get_goods_data(page_data):
                            rows = process_goods(goods, main_name, is_promo)
                            for row in rows:
                                if is_promo:
                                    # Для промо-цен добавляем ТОЛЬКО если товар уже есть в словаре
                                    _store_promo(row, columns, data_dict)
                                else:
                                    # Для обычных цен добавляем новый товар
                                    _store_row(row, columns, data_dict)
                            processed_goods += len(rows)
                    
                    # Прогресс внутри группы
                    if pages_count > 5 and page % 5 == 0:
                        st.write(f"  📄 Обработано {page + 1}/{pages_count} страниц")
                    
                    # Пауза между страницами
                    if page < pages_count - 1:
                        time.sleep(0.3)
                        
                except TimeoutException:
                    st.error(f"  ⏰ Таймаут страницы {page}. Пропускаем остальные.")
                    break
                except Exception as e:
                    st.warning(f"  ⚠️ Ошибка страницы {page}: {e}")
                    continue
                    
            return processed_goods
            
        except TimeoutException:
            st.error(f"  ❌ Таймаут получения данных для {group_name}")
            return 0
        except Exception as e:
            st.error(f"  ❌ Ошибка обработки {group_name}: {e}")
            return 0
    
    try:
        st.write(f" 🔄 Обработка группы: {gname}")
        start_time = time.time()
        
        # Обрабатываем обычные цены (ВСЕ товары)
        regular_count = process_single_group(gid, f"{gname} (обычные)", is_promo=False)
        
        # Пауза между типами цен
        time.sleep(0.5)
        
        # Обрабатываем промо-цены (ТОЛЬКО для товаров, которые уже есть в словаре)
        promo_count = process_single_group(gid, f"{gname} (промо)", is_promo=True)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        st.write(f" ✅ Группа {gname} обработана: {regular_count} обычных + {promo_count} промо товаров (время: {processing_time:.1f}с)")
        return True
        
    except TimeoutException:
        st.error(f" ⏰ Общий таймаут группы {gname}. Пропускаем.")
        return False
    except Exception as e:
        st.error(f" ❌ Критическая ошибка группы {gname}: {e}")
        return False

def skip_problematic_groups(main_group):
    """Пропускает известные проблемные группы"""
    # 3507 - проблемная группа из предыдущих ошибок
    # 3516 - Хозяйственные товары (последняя зависшая группа)
    skipped_ids = ['3507', '3516']
    
    filtered_groups = {}
    skipped_count = 0
    
    for name, (gid, children) in main_group.items():
        filtered_children = []
        for child in children:
            if str(child['GoodsGroupId']) in skipped_ids:
                skipped_count += 1
                st.warning(f"Пропускаем проблемную группу: {child.get('GoodsGroupName', 'Unknown')} (ID: {child['GoodsGroupId']})")
                continue
            filtered_children.append(child)
        
        if filtered_children:
            filtered_groups[name] = [gid, filtered_children]
    
    if skipped_count > 0:
        st.info(f"Автоматически пропущено проблемных групп: {skipped_count}")
    
    return filtered_groups

def st_progress(iterable, *, desc=None, total=None):
    """Прогресс-бар для Streamlit"""
    if total is None:
        total = len(iterable) if hasattr(iterable, "__len__") else 100

    bar = st.progress(0)
    if desc:
        st.text(desc)

    for i, item in enumerate(iterable):
        yield item
        bar.progress((i + 1) / total)

def post_merge(src_file: Path | str) -> Path:
    """Пост-обработка данных"""
    src_file = Path(src_file)
    const_file = Path("excel/ready_bc_main.xlsx")

    if not src_file.exists():
        st.error(f"Не найден исходный файл: {src_file}")
        return src_file

    if not const_file.exists():
        st.error(f"Не найден файл-константа: {const_file}")
        return src_file

    df_main = pd.read_excel(src_file)
    df_bc = pd.read_excel(const_file)

    df = pd.merge(df_main, df_bc, how="left", on="name")
    if 'Unnamed: 0' in df.columns:
        df = df.drop(columns=['Unnamed: 0'])
    ts = datetime.datetime.now().strftime("%d%m%Y_%H%M")
    out_file = src_file.with_name(f"full{ts}.xlsx")
    df.to_excel(out_file, index=False)  # Убедитесь что index=False

    st.success(f"Post-merge завершён: {out_file.name}")
    return out_file

def build_api_report(file_path: str):
    """Построение отчета с улучшенной обработкой ошибок"""
    file_path = Path(file_path)
    
    st.header("📊 Сбор данных с API InfoPrice")
    st.write("⏰ Процесс может занять несколько минут...")
    
    # Проверка API
    with st.spinner("Проверка доступности API..."):
        try:
            test_response = requests.get('https://api.infoprice.by', timeout=10)
            if test_response.status_code == 200:
                st.success("✅ API доступен")
            else:
                st.warning(f"⚠️ API возвращает статус: {test_response.status_code}")
        except:
            st.error("❌ API недоступен. Проверьте подключение к интернету.")
            return

    # Получаем группы
    with st.spinner("Получение списка категорий..."):
        main_group = get_main_group()
    
    if not main_group:
        st.error("Не удалось получить данные о группах товаров")
        return

    # Фильтруем проблемные группы
    main_group = skip_problematic_groups(main_group)
    
    if not main_group:
        st.error("После фильтрации не осталось групп для обработки")
        return

    columns = [
        "good_id", "category", "subcategory", "name", "link",
        "sosedi", "sosedi_promo", "korona", "korona_promo", "gippo", "gippo_promo",
        "evroopt", "evroopt_promo", "santa", "santa_promo", "green", "green_promo",
    ]
    data_dict = {}

    total_main = len(main_group)
    successful_groups = 0
    failed_groups = 0
    total_groups = sum(len(children) for _, children in main_group.values())

    # Элементы интерфейса
    progress_bar = st.progress(0)
    status_text = st.empty()
    stats_text = st.empty()

    st.subheader("📋 Обработка категорий:")
    
    current_group = 0
    for i, main_name in enumerate(main_group.keys()):
        with st.expander(f"Категория {i+1}/{total_main}: {main_name}", expanded=False):
            children = main_group[main_name][1]
            
            for j, group in enumerate(children):
                current_group += 1
                gid = group["GoodsGroupId"]
                gname = group.get("GoodsGroupName", f"Группа {gid}")
                
                # Прогресс
                progress = current_group / total_groups
                progress_bar.progress(progress)
                status_text.text(f"Обработка: {gname} ({current_group}/{total_groups})")
                
                # Обработка группы
                try:
                    success = safe_process_group(gid, gname, main_name, data_dict, columns)
                except Exception as e:
                    st.error(f" ❌ Необработанная ошибка: {e}")
                    success = False
                
                if success:
                    successful_groups += 1
                else:
                    failed_groups += 1
                
                # Статистика
                stats_text.text(f"""
                📊 Статистика обработки:
                ✅ Успешных групп: {successful_groups}
                ❌ Ошибок: {failed_groups}  
                📦 Товаров собрано: {len(data_dict):,}
                ⏳ Прогресс: {current_group}/{total_groups} ({progress:.1%})
                """)
                
                # Принудительное обновление интерфейса
                time.sleep(0.1)

    # Убираем элементы прогресса после завершения
    progress_bar.empty()
    status_text.empty()
    
    # Сохранение результатов
    if data_dict:
        st.subheader("💾 Сохранение результатов...")
        try:
            df = pd.DataFrame(data_dict.values(), columns=columns)
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="AllData", index=False)
            
            st.success(f"✅ Файл успешно сохранён: {file_path.name}")
            st.info(f"""
            **Итоговая статистика:**
            - Обработано товаров: {len(data_dict):,}
            - Успешных групп: {successful_groups}
            - Групп с ошибками: {failed_groups}
            - Всего групп: {total_groups}
            - Прогресс: {current_group}/{total_groups} групп обработано
            """)
            
            # Автоматическая пост-обработка
            st.subheader("🔧 Автоматическая пост-обработка...")
            with st.spinner("Выполняется пост-обработка данных..."):
                try:
                    final_file = post_merge(file_path)
                    st.success(f"✅ Финальный файл готов!")
                    
                    # Ссылка для скачивания
                    with open(final_file, "rb") as file:
                        file_data = file.read()
                    
                    st.download_button(
                        label="📥 Скачать финальный файл",
                        data=file_data,
                        file_name=final_file.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
                    st.info(f"**Файл:** {final_file.name}")
                    
                except Exception as e:
                    st.error(f"❌ Ошибка при пост-обработке: {e}")
                    
        except Exception as e:
            st.error(f"❌ Ошибка сохранения: {e}")
    else:
        st.error("❌ Не удалось собрать данные.")

def safe_build_api_report(file_path: str):
    """Безопасная обертка"""
    try:
        build_api_report(file_path)
    except KeyboardInterrupt:
        st.warning("⚠️ Процесс прерван пользователем")
    except Exception as e:
        st.error(f"❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")