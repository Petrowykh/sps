# db.py
import sqlite3, pandas as pd

conn = sqlite3.connect('products.db', check_same_thread=False, uri=True)

def get_products() -> pd.DataFrame:
    return pd.read_sql('SELECT barcode, name FROM products', conn)

def count_products() -> int:
    return conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]