"""
myparser.py  –  упрощённый и ускоренный вариант
python -m pip install selenium webdriver-manager
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ---------- настройки ----------
SITE_URL = "https://infoprice.by/"
PROMO_PARAM = "&promoPrice=1"
TIMEOUT = 12
HEADLESS = True

# селекторы
_SEL_SEARCH_FORM = (By.CLASS_NAME, "form-search")
_SEL_BTN_PRIMARY = (By.CLASS_NAME, "btn-primary")
_SEL_NOT_FOUND   = (By.CSS_SELECTOR, "div.text-not-found")
_SEL_NAME        = (By.CSS_SELECTOR, "div.max-height")
_SEL_NET_LOGO    = (By.XPATH, ".//div[@class='logo']//img")
_SEL_PRICE_VOL   = (By.CSS_SELECTOR, "div.price-volume")

logging.basicConfig(
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("myparser")

# ---------- типы возвращаемых данных ----------
@dataclass(slots=True)
class PriceInfo:
    name: str
    min_price: float
    min_promo: float
    shops: Dict[str, float]


class ParserInfoAll:
    """Контекст-менеджер: with ParserInfoAll() as p:"""

    def __init__(self) -> None:
        log.info("Запуск драйвера")
        options = Options()
        if HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

        self._wait = WebDriverWait(self.driver, TIMEOUT)
        self._init_start_page()

    # -------------------- входная точка --------------------
    def _init_start_page(self) -> None:
        """Прожать кнопку «Принять» на стартовой странице."""
        self.driver.get(SITE_URL)
        try:
            search_form = self._wait.until(EC.element_to_be_clickable(_SEL_SEARCH_FORM))
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", search_form)
            search_form.click()

            btn = self._wait.until(EC.element_to_be_clickable(_SEL_BTN_PRIMARY))
            btn.click()
            log.info("Стартовая инициализация пройдена")
        except TimeoutException as exc:
            self._dump_page("init_error")
            raise RuntimeError("Не удалось пройти стартовую инициализацию") from exc

    # -------------------- основной метод --------------------
    def get_price(self, url: str) -> PriceInfo:
        """Вернуть PriceInfo для переданного URL."""
        self.driver.get(url)

        # 1. быстрая проверка «не найдено»
        if self._exists(_SEL_NOT_FOUND):
            return PriceInfo("Не найден", 0.0, 0.0, {})

        # 2. название товара
        name_el = self._get_one(_SEL_NAME)
        if name_el is None:
            return PriceInfo("Не найден", 0.0, 0.0, {})
        name = name_el.text.strip()

        # 3. обычные цены
        shops, prices = self._parse_prices_grid()

        min_price = min(prices) if prices else 0.0
        shops_dict = dict(zip(shops, prices))

        # 4. промо-ценовой вариант той же страницы
        promo_min = self._parse_promo(url)

        return PriceInfo(name, min_price, promo_min, shops_dict)

    # -------------------- внутренние helper-ы --------------------
    def _parse_prices_grid(self) -> Tuple[list[str], list[float]]:
        """Парсит блоки с сетями и ценами."""
        logos = self.driver.find_elements(*_SEL_NET_LOGO)[1:]  # пропускаем «Инфоцен»
        price_blocks = self.driver.find_elements(*_SEL_PRICE_VOL)

        shops, prices = [], []
        for logo, price in zip(logos, price_blocks):
            shops.append(logo.get_attribute("alt") or "unknown")
            try:
                prices.append(float(price.text.replace(",", ".")))
            except ValueError:
                continue
        return shops, prices

    def _parse_promo(self, base_url: str) -> float:
        """Переходит на ?promoPrice=1 и забирает минимальную цену."""
        self.driver.get(base_url + PROMO_PARAM)
        _, prices = self._parse_prices_grid()
        return min(prices) if prices else 0.0

    # ---------- selenium helpers ----------
    def _exists(self, selector: Tuple[str, str]) -> bool:
        return bool(self.driver.find_elements(*selector))

    def _get_one(self, selector: Tuple[str, str]) -> WebElement | None:
        try:
            return self._wait.until(EC.presence_of_element_located(selector))
        except TimeoutException:
            return None

    def _dump_page(self, prefix: str) -> None:
        """Сохранить HTML при ошибке."""
        file = Path(f"{prefix}_{int(time.time())}.html")
        file.write_text(self.driver.page_source, encoding="utf-8")
        log.warning("Дамп страницы сохранён: %s", file)

    # ---------- контекст-менеджер ----------
    def close(self) -> None:
        if hasattr(self, "driver"):
            self.driver.quit()
            log.info("Драйвер остановлен")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ---------- удобный drop-in replacement для старого кода ----------
def get_price(url: str) -> PriceInfo:
    with ParserInfoAll() as p:
        return p.get_price(url)


if __name__ == "__main__":
    # быстрый самотест
    print(get_price("https://infoprice.by/?search=4820043730018"))
