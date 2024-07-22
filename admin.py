import telebot
from psycopg2._psycopg import Error
from telebot import types
from config import API_TOKEN, ADMIN_IDS, PHOTOS_DIR
from database import insert_product, insert_category, get_all_categories, connect_to_db, delete_product_by_id
import os

# --------------------------------------------------------------------------------------------------------

bot = telebot.TeleBot(API_TOKEN)

# --------------------------------------------------------------------------------------------------------


# Добавление новой категории
@bot.message_handler(commands=['add_category'])
def add_category(message):
    if str(message.from_user.id) in ADMIN_IDS:
        bot.send_message(message.chat.id, "Введите название новой категории:")
        bot.register_next_step_handler(message, process_category_name)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


def process_category_name(message):
    category_name = message.text.strip()
    print(f"Trying to insert category: {category_name}")

    if insert_category(category_name):
        bot.send_message(message.chat.id, f"Категория '{category_name}' успешно добавлена.")
    else:
        bot.send_message(message.chat.id, f"Категория '{category_name}' успешно добавлена.")

# --------------------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------------------


# Добавление нового товара
@bot.message_handler(commands=['add_product'])
def add_product(message):
    if str(message.from_user.id) in ADMIN_IDS:
        bot.send_message(message.chat.id, "Вы вошли в админ панель. Добавьте новый товар.")
        bot.send_message(message.chat.id, "Введите название товара:")
        bot.register_next_step_handler(message, process_product_name)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


def process_product_name(message):
    product_name = message.text.strip()

    # Получаем список категорий из базы данных
    categories = get_all_categories()
    if categories:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in categories:
            markup.add(types.KeyboardButton(category[1]))
        bot.send_message(message.chat.id, "Выберите категорию товара:", reply_markup=markup)
        bot.register_next_step_handler(message, lambda m: process_category_selection(m, product_name, categories))
    else:
        bot.send_message(message.chat.id, "Ошибка: Нет доступных категорий.")


def process_category_selection(message, product_name, categories):
    selected_category = message.text.strip()
    category_id = None
    for category in categories:
        if category[1] == selected_category:
            category_id = category[0]
            break

    if category_id is not None:
        bot.send_message(message.chat.id, "Введите цену товара:")
        bot.register_next_step_handler(message, lambda m: process_product_price(m, product_name, category_id))
    else:
        bot.send_message(message.chat.id, "Ошибка при выборе категории. Попробуйте снова.")


def process_product_price(message, product_name, category_id):
    try:
        price = float(message.text.strip())
        bot.send_message(message.chat.id, "Введите доступные размеры (разделите запятой):", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, lambda m: process_product_sizes(m, product_name, category_id, price))
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный формат цены. Попробуйте снова.")
        bot.register_next_step_handler(message, lambda m: process_product_price(m, product_name, category_id))


def process_product_sizes(message, product_name, category_id, price):
    sizes = [size.strip() for size in message.text.split(',')]
    bot.send_message(message.chat.id, "Загрузите фотографию товара:")
    bot.register_next_step_handler(message, lambda m: process_product_photo(m, product_name, category_id, price, sizes))


def process_product_photo(message, product_name, category_id, price, sizes):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        photo_path = os.path.join(PHOTOS_DIR, '')
        if not os.path.exists(photo_path):
            os.makedirs(photo_path)

        photo_file_path = os.path.join(photo_path, product_name.lower() + '.jpg')
        with open(photo_file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        photo_filename = product_name.lower() + '.jpg'

        # Добавление товара в базу данных
        if insert_product(product_name, category_id, price, sizes, photo_filename):
            bot.send_message(message.chat.id, f"Товар '{product_name}' успешно добавлен.")
        else:
            bot.send_message(message.chat.id, "Ошибка при добавлении товара в базу данных.")
    else:
        bot.send_message(message.chat.id, "Фотография не загружена. Попробуйте снова.")


# --------------------------------------------------------------------------------------------------------


# Обработка команды /delete_product

@bot.message_handler(commands=['delete_product'])
def delete_product(message):
    if str(message.chat.id) in ADMIN_IDS:
        bot.send_message(message.chat.id, "Введите ID продукта для удаления:")
        bot.register_next_step_handler(message, process_delete_product)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


def process_delete_product(message):
    try:
        product_id = int(message.text.strip())
        delete_product_by_id(product_id)
        bot.send_message(message.chat.id, f"Продукт с ID {product_id} успешно удален.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при удалении продукта: {str(e)}")


