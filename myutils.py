import pandas as pd
from redmail import EmailSender
from pathlib import Path

def load_sku(file_name):
    df = pd.read_excel(file_name)
    return df

def send_letter(receivers, file):
    gmail = EmailSender(
        host='smtp.gmail.com',
        port=587,
        username="a.petrowykh@gmail.com",
        password="dfdgrrybavoryrih"
    )

    gmail.send(
        subject="Parser Report",
        receivers=[receivers],
        text="Парсинг ТОП-100 (Соседи)",
        attachments={
            # From path on disk
            file: Path(file),
            
        }
    )