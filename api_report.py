import pandas as pd
import requests
import streamlit as st
from api import post_json, PARAMS, HEADERS
from pathlib import Path
import datetime


def get_main_group():
    try:
        data_group = '{"CRC":"","Packet":{"FromId":"10003001","ServerKey":"omt5W465fjwlrtxcEco97kew2dkdrorqqq","Data":{}}}'
        response = requests.post('https://api.infoprice.by/InfoPrice.GoodsGroup', params=PARAMS, headers=HEADERS, data=data_group)
        response.raise_for_status()
        main_group = response.json()
        return {i['GoodsGroupName']: [i['GoodsGroupId'], i['Child']] for i in main_group['Table']}
    except Exception as e:
        st.write(f"Ошибка при получении главных групп: {e}")
        return {}

def create_data_group(group_id, page="", is_promo=False):
    promo_flag = 1 if is_promo else 0
    data = f'{{"CRC":"","Packet":{{"FromId":"10003001","ServerKey":"omt5W465fjwlrtxcEco97kew2dkdrorqqq","Data":{{"ContractorId":"","GoodsGroupId":"{group_id}","Page":"{page}","Search":"","OrderBy":0,"OrderByContractor":0,"CompareСontractorId":72631,"CatalogType":1,"IsAgeLimit":0,"IsPromotionalPrice":{promo_flag}}}}}}}'
    return data.encode()

def get_price_group(group_id, page, is_promo=False):
    data = create_data_group(group_id, page=page, is_promo=is_promo)
    resp = post_json("https://api.infoprice.by/InfoPrice.Goods", data)
    resp.raise_for_status()
    return resp.json()

def process_goods(goods, main_name, is_promo=False):
    processed_data = []
    for data_good in goods['GoodsOffer']:
        goods_group_name = data_good['GoodsGroupName']
        goods_name = data_good['GoodsName'].rstrip()
        goods_id = data_good['GoodsId']
        prices = {72494: 0.00, 72512: 0.00, 72511: 0.00, 72517: 0.00, 72468: 0.00, 72526: 0.00}
        for price_contractor in data_good['Offers']:
            if price_contractor['ContractorId'] in prices:
                if not is_promo or (is_promo and price_contractor['IsPromotionalPrice']):
                    prices[price_contractor['ContractorId']] = float(price_contractor['Price'])
        link = 'https://infoprice.by/?search=' + "+".join(goods_name.split(" "))
        if is_promo:
            processed_data.append((goods_id, *prices.values()))
        else:
            processed_data.append((goods_id, main_name, goods_group_name, goods_name, link, *prices.values()))
    return processed_data

def st_progress(iterable, *, desc=None, total=None):
    """
    Drop-in замена tqdm → st.progress.
    Возвращает генератор, совместимый с `for item in tqdm(...):`
    """
    if total is None:
        total = len(iterable) if hasattr(iterable, "__len__") else 100

    bar = st.progress(0)
    if desc:
        st.text(desc)          # показываем подпись над полоской

    for i, item in enumerate(iterable):
        yield item
        bar.progress((i + 1) / total)

# ---------- пост-обработка ----------
def post_merge(src_file: Path | str) -> Path:
    """
    src_file – путь к свежему api-отчёту (например, api_report_2209_1430.xlsx)
    возвращает путь к итоговому файлу ughДДММГГГГ_ЧЧММ.xlsx
    """
    src_file = Path(src_file)
    const_file = Path("excel/ready_bc_main.xlsx")  # пока рядом, потом заменим на БД/ENV

    if not src_file.exists():
        st.error(f"Не найден исходный файл: {src_file}")
        return src_file

    if not const_file.exists():
        st.error(f"Не найден файл-константа: {const_file}")
        return src_file

    df_main = pd.read_excel(src_file)
    df_bc = pd.read_excel(const_file)

    df = pd.merge(df_main, df_bc, how="left", on="name")

    ts = datetime.datetime.now().strftime("%d%m%Y")
    out_file = src_file.with_name(f"ugh{ts}.xlsx")
    df.to_excel(out_file, index=False)

    st.success(f"Post-merge завершён: {out_file.name}")
    return out_file

# ---------- основная функция ----------
def build_api_report(file_path: str):
    """Построить полный отчёт и сохранить в file_path."""
    file_path = Path(file_path)

    main_group = get_main_group()
    if not main_group:
        st.stop()

    columns = [
        "good_id", "category", "subcategory", "name", "link",
        "sosedi", "sosedi_promo", "korona", "korona_promo", "gippo", "gippo_promo",
        "evroopt", "evroopt_promo", "santa", "santa_promo", "green", "green_promo",
    ]
    data_dict: dict = {}

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        for main_name in main_group:
            st.write(f"Обработка категории: **{main_name}**")
            for group in st_progress(main_group[main_name][1], desc=f"Группы в {main_name}"):
                gid = group["GoodsGroupId"]

                # 1. обычные цены
                price = get_price_group(gid, "")
                if price is None:
                    continue
                for page in st_progress(
                    range(price["Table"][0]["GeneralData"][0]["AmountPages"]),
                    desc="Обычные цены",
                ):
                    data = get_price_group(gid, str(page))
                    if data is None:
                        break
                    for goods in data["Table"]:
                        if goods["GeneralData"][0]["AmountGoods"] and "GoodsOffer" in goods:
                            for row in process_goods(goods, main_name):
                                good_id = row[0]
                                if good_id not in data_dict:
                                    data_dict[good_id] = {col: 0.0 for col in columns}
                                    (
                                        data_dict[good_id]["good_id"],
                                        data_dict[good_id]["category"],
                                        data_dict[good_id]["subcategory"],
                                        data_dict[good_id]["name"],
                                        data_dict[good_id]["link"],
                                    ) = row[:5]
                                # заполняем цены
                                for idx, col in enumerate(columns[5:11], start=5):
                                    data_dict[good_id][col] = row[idx]

                # 2. промо-цены
                price_promo = get_price_group(gid, "", is_promo=True)
                if price_promo is None:
                    continue
                for page in st_progress(
                    range(price_promo["Table"][0]["GeneralData"][0]["AmountPages"]),
                    desc="Промо-цены",
                ):
                    data = get_price_group(gid, str(page), is_promo=True)
                    if data is None:
                        break
                    for goods in data["Table"]:
                        if goods["GeneralData"][0]["AmountGoods"] and "GoodsOffer" in goods:
                            for row in process_goods(goods, main_name, is_promo=True):
                                good_id = row[0]
                                if good_id in data_dict:
                                    for idx, col in enumerate(columns[11:], start=1):
                                        data_dict[good_id][col] = row[idx]

        # сохраняем
        df = pd.DataFrame(data_dict.values(), columns=columns)
        df.to_excel(writer, sheet_name="AllData", index=False)

    st.success(f"Файл сохранён: {file_path.name}")