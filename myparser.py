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

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import selenium.webdriver as webdriver

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
        self.driver = None
        self._start_browser() 

    # -------------------- входная точка --------------------
    def _start_browser(self):
        if self.driver:                # если уже был – закрываем
            self.driver.quit()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-images")        # ← не грузим картинки
        options.add_argument("--disable-javascript")    # ← если JS не нужен
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=256") 
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def reload_tab(self):
        """Переиспользуем ту же вкладку без перезапуска процесса."""
        self.driver.get("about:blank")          # чистим DOM
        time.sleep(0.2)

    def close(self):
        if self.driver:
            self.driver.quit()

    # -------------------- основной метод --------------------
    def get_price(self, url: str) -> PriceInfo:
        self.driver.get(url)
        time.sleep(3)                       # ← даём странице прогрузиться

        # 1. проверка «не найдено»
        if self._exists(_SEL_NOT_FOUND):
            return PriceInfo("Не найден", 0.0, 0.0, {})

        # 2. название (как раньше)
        try:
            name_el = self.driver.find_element(By.CSS_SELECTOR, 'div.max-height')
            name = name_el.text.strip()
        except NoSuchElementException:
            return PriceInfo("Не найден", 0.0, 0.0, {})

        # 3. сети и цены (как раньше, без ожиданий)
        try:
            nets  = self.driver.find_elements(By.XPATH, "//div[@class='logo']//img")[1:]
            prices = self.driver.find_elements(By.CSS_SELECTOR, 'div.price-volume')
            if not nets or not prices:
                return PriceInfo("Не найден", 0.0, 0.0, {})

            list_price = [float(p.text) for p in prices]
            list_net   = [n.get_attribute('alt') or 'unknown' for n in nets]
            shops_dict = dict(zip(list_net, list_price))
            min_price  = min(list_price)
        except Exception:
            return PriceInfo("Не найден", 0.0, 0.0, {})

        # 4. промо (коротко)
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
