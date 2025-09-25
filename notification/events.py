# events.py
from datetime import datetime
from .telegram_logger import telegram_notifier

def notify_login():
    """Уведомление о входе в систему"""
    message = f"""
🛒 <b>SPS System - Вход в систему</b>
👤 <b>Действие:</b> Пользователь вошел в систему
🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
    """.strip()
    return telegram_notifier.send_message(message)

def notify_report_start(report_type: str):
    """Уведомление о начале формирования отчета"""
    message = f"""
🛒 <b>SPS System - Запуск отчета</b>
📊 <b>Тип отчета:</b> {report_type}
🚀 <b>Статус:</b> Запущено формирование
🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
    """.strip()
    return telegram_notifier.send_message(message)

def notify_report_complete(report_type: str, file_size: int = 0):
    """Уведомление о завершении отчета"""
    size_mb = f"{file_size / 1024 / 1024:.2f} MB" if file_size else "unknown"
    message = f"""
🛒 <b>SPS System - Отчет готов</b>
📊 <b>Тип отчета:</b> {report_type}
✅ <b>Статус:</b> Успешно завершено
💾 <b>Размер файла:</b> {size_mb}
🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
    """.strip()
    return telegram_notifier.send_message(message)

def notify_download(filename: str, report_type: str):
    """Уведомление о скачивании файла"""
    message = f"""
🛒 <b>SPS System - Скачивание</b>
📥 <b>Действие:</b> Файл скачан
📄 <b>Файл:</b> {filename}
📊 <b>Тип отчета:</b> {report_type}
🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
    """.strip()
    return telegram_notifier.send_message(message)

def notify_error(error_msg: str, action: str = "General"):
    """Уведомление об ошибке"""
    message = f"""
🛒 <b>SPS System - Ошибка</b>
❌ <b>Действие:</b> {action}
💥 <b>Ошибка:</b> {error_msg}
🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
    """.strip()
    return telegram_notifier.send_message(message)