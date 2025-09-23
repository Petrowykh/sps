"""
myparser.py  –  HTTP-only версия (без Chrome)
python -m pip install requests
"""
from __future__ import annotations

import logging
import requests
from dataclasses import dataclass
from typing import Dict
from api import post_json, PARAMS, HEADERS, API_URL

# ---------- настройки API ----------
API_URL = "https://api.infoprice.by/InfoPrice.Goods"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
}

logging.basicConfig(
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("myparser")

# ---------- тип возвращаемых данных ----------
@dataclass(slots=True)
class PriceInfo:
    name: str
    min_price: float
    min_promo: float
    shops: Dict[str, float]


# ---------- основной метод ----------
API_URL = "https://api.infoprice.by/InfoPrice.Goods"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
}

def create_data_barcode(barcode: str, page: str = "", is_promo: bool = False) -> str:
    promo_flag = 1 if is_promo else 0
    data = (
        f'{{"CRC":"","Packet":{{"FromId":"10003001","ServerKey":"omt5W465fjwlrtxcEco97kew2dkdrorqqq",'
        f'"Data":{{"ContractorId":"","GoodsGroupId":"","Page":"{page}","Search":"{barcode}","OrderBy":0,'
        f'"OrderByContractor":0,"CompareСontractorId":72631,"CatalogType":1,"IsAgeLimit":0,'
        f'"IsPromotionalPrice":{promo_flag}}}}}}}'
    )
    return data

def get_price(barcode: str) -> PriceInfo:
    """min_price – минимум обычных цен, min_promo – минимум промо-цен."""
    # 1. обычные цены
    data = _get_price_api(barcode, is_promo=False)
    shops, min_price = _extract_prices(data)

    # 2. промо-цены
    data_promo = _get_price_api(barcode, is_promo=True)
    promo_shops, min_promo = _extract_prices(data_promo)

    return PriceInfo(
        name=_get_name_from_data(data),
        min_price=min_price,
        min_promo=min_promo,
        shops=shops,
    )

# ---------- вспомогательные ----------
def _get_price_api(barcode: str, is_promo: bool = False) -> dict:
    data = create_data_barcode(barcode, page="", is_promo=is_promo)
    resp = post_json(API_URL, data)
    resp.raise_for_status()
    return resp.json()

def _extract_prices(data: dict) -> tuple[dict, float]:
    """Возвращает (словарь цен по магазину, минимальная цена)."""
    shops = {"Соседи": 0.0, "Корона": 0.0, "Гиппо": 0.0,
             "Евроопт": 0.0, "Санта": 0.0, "Грин": 0.0, "Emall": 0.0}
    mapper = {72494: "Соседи", 72512: "Корона", 72511: "Гиппо",
              72517: "Евроопт", 72468: "Санта", 72526: "Грин", 72631: "Emall"}

    min_val = 0.0
    for offer in data.get("Table", []):
        for off in offer.get("GoodsOffer", []):
            for o in off.get("Offers", []):
                cid = o["ContractorId"]
                price = float(o["Price"])
                shop = mapper.get(cid)
                if shop:
                    # записываем цену в магазин
                    shops[shop] = price
                    # считаем минимум
                    if min_val == 0.0 or price < min_val:
                        min_val = price
    return shops, min_val

def _get_name_from_data(data: dict) -> str:
    try:
        return data["Table"][0]["GoodsOffer"][0]["GoodsName"].strip()
    except (KeyError, IndexError):
        return "Не найден"
    
# ---------- удобная обёртка ----------
def get_price_by_barcode(barcode: str) -> PriceInfo:
    """Drop-in замена старому get_price(url)."""
    return get_price(barcode)


