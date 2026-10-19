import logging
import time
from functools import wraps
# Рівні важливості поведомлень:
# DEBUG — найнижчий рівень, детальна інформація для діагностики під час розробки.
# INFO — підтвердження того, що програма працює штатно (наприклад, успішне завантаження фіда чи виконання команди).
# WARNING — попередження про неочікувані ситуації, які поки не ламають роботу програми (наприклад, відсутність опціонального модуля).
# ERROR — серйозна помилка, через яку певна функція чи команда не змогла виконатися.
# CRITICAL — критична системна помилка.


# Логування - запис всього (що виводиться в консоль) у файл
def setup_logging():
    "Конфігурує глобальне логування для проєкту"
    logging.basicConfig( #Функція basicConfig приймає налаштування (рівень, формат, обробники) і застосовує їх до кореневого логера програми
        level=logging.INFO, # програма буде ігнорувати тип помилкт DEBUG, а починаючи з INFO і вище буде записувати повідомлення
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", #форматує вивід повідомлення(точний час, рівень важливості, імʼя логгера, саме повідомлення)
        handlers=[
            logging.FileHandler("citymove.log", encoding="utf-8"), #відкриває (або створює) файл citymove.log у корені проєкту для запису всіх подій
            logging.StreamHandler() #паралельно виводить ті самі повідомлення в консоль
        ])

setup_logging()

logger = logging.getLogger("citymove") #створюємо логгер з іменем citymove
# Цю змінну logger ми імпортуватимемо в наші обробники або декоратори, щоб писати виклики на зразок logger.info("Текст") замість print("Текст").

def timed(func): #функція - декоратор
    """Декоратор для заміру часу виконання функції та логування результату"""
    @wraps(func)#Застосування декоратора wraps до обгортки
    def wrapper(*args, **kwargs): #Оголошення внутрішньої функції-обгортки wrapper
        start_time = time.perf_counter()
        logger.info(f"Початок виконання функції '{func.__name__}'")#Запис у лог інформаційного повідомлення про те, що почалося виконання функції
        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            runtime = end_time - start_time
            logger.info(f"Функція '{func.__name__}' успішно виконана за {runtime:.4f} секунд")
            return result
        except Exception as e:
            end_time = time.perf_counter()
            runtime = end_time - start_time
            logger.error(f"Помилка у функції '{func.__name__}' після {runtime:.4f} секунд: {e}")
            raise
    return wrapper


def log_call(func):#Оголошення декоратора
    """Декоратор для логування вхідних аргументів та результатів виклику функції."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Виклик '{func.__name__}' з аргументами: args={args}, kwargs={kwargs}")#Запис у лог інформації про сам момент виклику функції та точних значень усіх аргументів, з якими її запустили.
        try:
            result = func(*args, **kwargs)
            logger.info(f"Результат виконання '{func.__name__}': {result}")#Запис у лог успішного завершення та того, що саме функція повернула
            return result
        except Exception as e:
            logger.error(f"Виняток у функції '{func.__name__}': {e}", exc_info=True)
            raise
    return wrapper