import bs4
import requests

import logging, urllib3, time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ChromeOptions, Chrome

logging.basicConfig(filename="parse.log", level=logging.INFO, filemode='w')
urllib3.disable_warnings()

class Parse:

    def __init__(self):
        # init parser
        self.session = requests.Session()
        self.session.headers = {'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36'}

    def get_page(self, page_url):
        # text of page
        try:
            r = self.session.get(page_url, verify=False)
            r.encoding = 'utf-8'
            html_page = r.text
        except Exception as E:
            html_page = ""
            logging.exception(E)
        return html_page
    
class ParserGippo(Parse):

    def get_price(self, html):

        soup = bs4.BeautifulSoup(html, 'lxml')
        price = soup.find('div', class_="price").text.split(' ')[0]
        try:
            price = float(price)
        except:
            price = 0
        return price
    
class ParserEurotorg:

    def __init__(self) -> None:
        self.options = ChromeOptions()
        self.options.add_argument('--no-sandbox')
        self.options.headless = True
        self.driver = Chrome(options=self.options)
    
    def get_price(self, html, flag):
        #TODO: may be add first enter to __init__
        # FIXME kjlkdfldkjf
        self.driver.get(html)
        #time.sleep(1)
        if flag:
            time.sleep(1)
            self.driver.find_element(By.XPATH, '//span[text()="Принять"]').click()
        price = self.driver.find_element(By.CSS_SELECTOR, 'span.price_main__5jwcE').text.split(' ')[0].replace(',','.')
        try:
            price = float(price)
        except:
            price = 0
        return price
        
class ParserInfo:
    def __init__(self) -> None:
        # self.options = ChromeOptions()
        # self.options.add_argument('--no-sandbox')
        # self.options.headless = True
        # self.driver = Chrome(options=self.options)
        self.driver = Chrome()
        

    def get_price(self, html):

        self.driver.get(html)
        time.sleep(5)
        list_price = []
        list_net = []
        name = self.driver.find_element(By.CSS_SELECTOR, "div.description").find_element(By.CSS_SELECTOR, 'div.max-height').text()
        nets = self.driver.find_elements(By.XPATH, "//div[@class='logo']//img")[1:]
        prices = self.driver.find_elements(By.CSS_SELECTOR, 'div.price-volume')
        for net, price in zip(nets, prices):
             
            list_price.append(price.text)
            list_net.append(net.get_attribute('alt'))
        #print(price)
        return name, dict(zip(list_net, list_price))