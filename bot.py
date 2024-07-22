import logging
import time
from telebot import apihelper
import psycopg2
import telebot
from telebot import types
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import insert_product, get_all_categories, get_products_by_category, get_product_by_id, add_to_cart, \
    get_cart_items, clear_cart, save_order, get_user_info, get_order_info
from config import *
from functools import partial
from admin import add_category, add_product
from admin import bot as admin_bot

bot = admin_bot

logging.basicConfig(level=logging.INFO)


# --------------------------------------------------------------------------------------------------------

# Приветственное сообщение и кнопка "Каталог"
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    catalog_button = types.InlineKeyboardButton("Каталог", callback_data="catalog")
    markup.add(catalog_button)

    # Отправка стикера из файла
    sticker_path = os.path.join(PHOTOS_DIR, 'AnimatedSticker.tgs')
    if os.path.exists(sticker_path):
        with open(sticker_path, 'rb') as sticker:
            bot.send_sticker(message.chat.id, sticker)
    else:
        bot.send_message(message.chat.id, "Не удалось найти стикер.")

    # Проверяем, зарегистрирован ли пользователь
    if not is_user_registered(message.chat.id):
        register_user(message)

    bot.send_message(message.chat.id, "Добро пожаловать в наш магазин PANDA SHOP 🐼", reply_markup=markup)


# Функция для проверки регистрации пользователя
def is_user_registered(chat_id):
    with psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                          database=DB_NAME) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
            return cursor.fetchone() is not None


# Функция для регистрации пользователя
def register_user(message):
    chat_id = message.chat.id
    username = message.chat.username
    first_name = message.chat.first_name
    last_name = message.chat.last_name

    with psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                          database=DB_NAME) as connection:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, first_name, last_name, chat_id) VALUES (%s, %s, %s, %s)",
                           (username, first_name, last_name, chat_id))
            connection.commit()


@bot.message_handler(commands=['stop'])
def handle_stop(message):
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Остановка работы бота.", reply_markup=markup)


# --------------------------------------------------------------------------------------------------------


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    logging.info(f"Handling callback query with data: {call.data}")

    if call.data == "catalog":
        send_catalog(call)
    elif call.data.startswith("add_to_cart_"):
        handle_add_to_cart(call)
    elif call.data.startswith("category_"):
        process_category_callback(call)
    elif call.data == "back_catalog":
        send_catalog(call)
    elif call.data == "view_cart":
        handle_view_cart(call)
    elif call.data == "clear_cart":
        handle_clear_cart(call)
    elif call.data.startswith("order_"):
        if call.data == "order_0":
            handle_order_from_cart(call)
        else:
            handle_order(call)
    elif call.data.startswith("confirm_order_"):
        handle_confirm_order(call)
    elif call.data == "cancel_order":
        handle_cancel_order(call)
    elif call.data.startswith("product_"):
        send_product_info(call, call.data)
    elif call.data.startswith("pay_by_"):
        handle_payment_method(call)
    else:
        bot.send_message(call.message.chat.id, "Неизвестная команда.")








# --------------------------------------------------------------------------------------------------------

# Функция для отправки каталога товаров
def send_catalog(call=None):
    markup = types.InlineKeyboardMarkup()
    categories = get_all_categories()  # Получаем все категории из базы данных

    if categories:
        for category in categories:
            category_button = types.InlineKeyboardButton(category[1], callback_data=f"category_{category[0]}")
            markup.add(category_button)

    back_button = types.InlineKeyboardButton("Назад", callback_data="back_catalog")
    markup.add(back_button)

    if call:
        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            print(f"Error deleting message: {e}")

    bot.send_message(call.message.chat.id, "Что будем покупать?", reply_markup=markup) if call else None


# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
def process_category_callback(call):
    category_id = int(call.data.split('_')[1])
    products = get_products_by_category(category_id)

    if products:
        markup = types.InlineKeyboardMarkup()
        for product in products:
            product_button = types.InlineKeyboardButton(f"{product[1]} - {product[3]} тг.", callback_data=f"product_{product[0]}")
            markup.add(product_button)


        bot.send_message(call.message.chat.id, "Выберите товар:", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "В этой категории пока нет товаров.")


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_catalog')
def back_to_catalog_callback(call):
    send_catalog(call)



# Функция для отправки информации о товаре
def send_product_info(call, product_id_str):
    try:
        # Проверка формата данных
        if not product_id_str.startswith("product_"):
            raise ValueError("Некорректный формат данных для получения информации о товаре.")

        # Извлекаем числовую часть из строки идентификатора товара
        product_id = int(product_id_str.split('_')[1])
        print(f"Fetching product info for ID: {product_id}")

        # Устанавливаем соединение с базой данных
        with psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                              database=DB_NAME) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
                product = cursor.fetchone()

                if product:
                    product_name = product[1]
                    product_price = product[3]
                    product_sizes = product[4]
                    product_photo_filename = product[5]

                    product_photo_url = os.path.join(PHOTOS_DIR, product_photo_filename)

                    print(f"Product photo URL: {product_photo_url}")

                    with open(product_photo_url, 'rb') as photo_file:
                        sizes_text = ", ".join(product_sizes)

                        markup = types.InlineKeyboardMarkup()

                        add_to_cart_button = types.InlineKeyboardButton("В корзину",
                                                                        callback_data=f"add_to_cart_{product_id}")
                        markup.row(add_to_cart_button)

                        bot.send_photo(call.message.chat.id, photo_file,
                                       caption=f"ID товара: {product_id}\n\nНазвание: <b>{product_name}</b>\n\nЦена: {product_price} тг.\n\nРазмеры: {sizes_text}",
                                       parse_mode='HTML', reply_markup=markup)

                else:
                    bot.send_message(call.message.chat.id, "Товар не найден.")

    except ValueError as e:
        bot.send_message(call.message.chat.id, f"Ошибка: {str(e)}")
    except (Exception, psycopg2.Error) as error:
        print(f"Ошибка при получении информации о продукте: {error}")
        bot.send_message(call.message.chat.id, "Произошла ошибка при получении информации о товаре.")




# --------------------------------------------------------------------------------------------------------
# Функция для обработки оформления заказа из корзины
def handle_order_from_cart(call):
    chat_id = call.message.chat.id
    logging.info(f"User {chat_id} requested to order from cart")

    items = get_cart_items(chat_id)
    if not items:
        bot.send_message(chat_id, "Ваша корзина пуста.")
        return

    order_summary = []
    total_amount = 0

    for item in items:
        product_id, name, price, quantity = item
        try:
            price = float(price)
            quantity = int(quantity)
            total_amount += price * quantity
            order_summary.append(f"{name} - {quantity} шт. - {price} тг. за шт.")
        except ValueError:
            logging.error(f"Ошибка преобразования данных для товара {product_id}.")
            order_summary.append(f"{name} - {quantity} шт.")

    order_summary_text = "\n".join(order_summary)

    # Кнопки для выбора способа оплаты
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton('Оплатить картой'), types.KeyboardButton('Оплатить криптовалютой'))

    bot.send_message(chat_id,
                     f"Вы собираетесь оформить заказ:\n\n"
                     f"{order_summary_text}\n\n"
                     f"Итого: {total_amount:.2f} тг. | {total_amount/475:.2f} USDT.\n\n"
                     f"1 USDT ~ 475 тг.\n"
                     "\nПожалуйста, выберите способ оплаты.",
                     reply_markup=markup)

    bot.register_next_step_handler(call.message, handle_payment_method_step, order_summary_text, total_amount)

# Функция для обработки выбранного способа оплаты
def handle_payment_method_step(message, order_summary, total_amount):
    chat_id = message.chat.id
    payment_method = message.text

    if payment_method == 'Оплатить картой':
        bot.send_message(chat_id, "Пожалуйста, отправьте чек о платеже.", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, handle_payment_receipt_step, order_summary, total_amount)
    elif payment_method == 'Оплатить криптовалютой':
        bot.send_message(chat_id, "Для оплаты криптовалютой, пожалуйста, используйте бот @send и отправьте скриншот подтверждения.", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, handle_payment_receipt_step, order_summary, total_amount)
    else:
        bot.send_message(chat_id, "Пожалуйста, выберите правильный способ оплаты.")
        bot.register_next_step_handler(message, handle_payment_method_step, order_summary, total_amount)

def handle_payment_receipt_step(message, order_summary, total_amount):
    chat_id = message.chat.id
    receipt_photo = message.photo[-1].file_id if message.photo else None

    if not receipt_photo:
        bot.send_message(chat_id, "Пожалуйста, отправьте фотографию чека.")
        bot.register_next_step_handler(message, handle_payment_receipt_step, order_summary, total_amount)
        return

    bot.send_message(chat_id, "Пожалуйста, введите ваше имя.")
    bot.register_next_step_handler(message, handle_name_step, order_summary, total_amount, receipt_photo)

def handle_name_step(message, order_summary, total_amount, receipt_photo):
    chat_id = message.chat.id
    user_name = message.text

    bot.send_message(chat_id, "Пожалуйста, введите ваш адрес.")
    bot.register_next_step_handler(message, handle_address_step, order_summary, total_amount, receipt_photo, user_name)

def handle_address_step(message, order_summary, total_amount, receipt_photo, user_name):
    chat_id = message.chat.id
    address = message.text

    bot.send_message(chat_id, "Пожалуйста, введите ваш номер телефона.")
    bot.register_next_step_handler(message, handle_phone_step, order_summary, total_amount, receipt_photo, user_name, address)

def handle_phone_step(message, order_summary, total_amount, receipt_photo, user_name, address):
    chat_id = message.chat.id
    phone = message.text

    order_details = {
        'order_summary': order_summary,
        'total_amount': total_amount,
        'name': user_name,
        'address': address,
        'phone': phone
    }

    save_order(chat_id, order_details)
    clear_cart(chat_id)

    bot.send_message(chat_id, "Ваш заказ был успешно оформлен. Спасибо за покупку!")
    admin_chat_id = GROUP_ID
    formatted_order_details = (
        f"Пользователь {user_name} оформил заказ:\n\n"
        f"Товары:\n{order_summary}\n\n"
        f"Итого: {total_amount:.2f} тг.\n"
        f"Имя: {user_name}\n"
        f"Адрес: {address}\n"
        f"Телефон: {phone}"
    )
    bot.send_message(admin_chat_id, formatted_order_details)


def handle_payment_receipt_step(message, order_summary, total_amount):
    chat_id = message.chat.id
    receipt_photo = message.photo[-1].file_id if message.photo else None

    if not receipt_photo:
        bot.send_message(chat_id, "Пожалуйста, отправьте фотографию чека.")
        bot.register_next_step_handler(message, handle_payment_receipt_step, order_summary, total_amount)
        return

    bot.send_message(chat_id, "Пожалуйста, введите ваше имя.")
    bot.register_next_step_handler(message, handle_name_step, order_summary, total_amount, receipt_photo)

def handle_name_step(message, order_summary, total_amount, receipt_photo):
    chat_id = message.chat.id
    user_name = message.text

    bot.send_message(chat_id, "Пожалуйста, введите ваш адрес.")
    bot.register_next_step_handler(message, handle_address_step, order_summary, total_amount, receipt_photo, user_name)

def handle_address_step(message, order_summary, total_amount, receipt_photo, user_name):
    chat_id = message.chat.id
    address = message.text

    bot.send_message(chat_id, "Пожалуйста, введите ваш номер телефона.")
    bot.register_next_step_handler(message, handle_phone_step, order_summary, total_amount, receipt_photo, user_name, address)

def handle_phone_step(message, order_summary, total_amount, receipt_photo, user_name, address):
    chat_id = message.chat.id
    phone = message.text

    # Сохраняем детали заказа
    order_details = {
        'order_summary': order_summary,
        'total_amount': total_amount,
        'name': user_name,
        'address': address,
        'phone': phone
    }

    save_order(chat_id, order_details)
    clear_cart(chat_id)

    # Форматируем текстовое сообщение с деталями заказа
    formatted_order_details = (
        f"Пользователь {user_name} оформил заказ:\n\n"
        f"Товары:\n{order_summary}\n\n"
        f"Итого: {total_amount:.2f} тг.\n"
        f"Имя: {user_name}\n"
        f"Адрес: {address}\n"
        f"Телефон: {phone}"
    )

    # Отправляем сообщение и фото чека в группу администраторов
    admin_chat_id = GROUP_ID
    if isinstance(admin_chat_id, list):
        admin_chat_id = admin_chat_id[0]  # Убедитесь, что это одно число

    try:
        bot.send_message(admin_chat_id, formatted_order_details)
        bot.send_photo(admin_chat_id, receipt_photo, caption="Фото чека от пользователя.")
        bot.send_message(chat_id, "Ваш заказ был успешно оформлен. Спасибо за покупку!")
    except Exception as e:
        bot.send_message(chat_id, "Произошла ошибка при отправке информации в группу.")
        logging.error(f"Ошибка при отправке информации в группу: {e}")



@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_by_"))
def handle_payment_method(call):
    chat_id = call.message.chat.id
    if call.data == "pay_by_card":
        bot.send_message(chat_id,
                         "Пожалуйста, отправьте чек о платеже.",
                         reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(call.message, handle_payment_receipt)
    elif call.data == "pay_by_crypto":
        bot.send_message(chat_id,
                         "Для оплаты криптовалютой перейдите в бот @send и выполните оплату. После этого отправьте чек о платеже.",
                         reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(call.message, handle_payment_receipt)

def handle_payment_receipt(message, order_summary, total_amount):
    chat_id = message.chat.id
    receipt_photo = message.photo[-1].file_id if message.photo else None

    if not receipt_photo:
        bot.send_message(chat_id, "Пожалуйста, отправьте фотографию чека.")
        bot.register_next_step_handler(message, handle_payment_receipt, order_summary, total_amount)
        return

    # Отправляем фото чека в группу администраторов
    admin_chat_id = GROUP_ID
    if isinstance(admin_chat_id, list):
        admin_chat_id = admin_chat_id[0]  # Убедитесь, что это одно число

    bot.send_photo(admin_chat_id, receipt_photo, caption="Фото чека от пользователя.")

    bot.send_message(chat_id, "Пожалуйста, введите ваше имя.")
    bot.register_next_step_handler(message, handle_name_step, order_summary, total_amount, receipt_photo)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_order_"))
def handle_confirm_order(call):
    try:
        data = call.data.split('_')
        if len(data) != 3 or data[0] != 'confirm' or data[1] != 'order':
            raise ValueError("Некорректный формат данных для подтверждения заказа.")

        product_id = int(data[2])
        logging.info(f"Confirming order for product_id: {product_id}")

        chat_id = call.message.chat.id
        user_info = get_user_info(chat_id)
        if not user_info:
            bot.send_message(chat_id, "Ошибка: не удалось получить информацию о пользователе.")
            return

        username = user_info.get('username', 'Не указано')

        with psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, database=DB_NAME) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
                product = cursor.fetchone()

                if product:
                    product_name = product[1]
                    product_price = product[3]

                    # Сохранение заказа
                    order_details = {
                        'order_summary': f"{product_name} - {product_price} тг.",
                        'total_amount': str(product_price),  # Убедитесь, что это строка
                        'username': username
                    }
                    save_order(chat_id, order_details)

                    bot.send_message(chat_id, "Ваш заказ был успешно оформлен. Спасибо за покупку!")

                    # Уведомление администратора
                    admin_chat_id = GROUP_ID
                    if isinstance(admin_chat_id, list):
                        admin_chat_id = admin_chat_id[0]  # Убедитесь, что это одно число
                    logging.info(f"Sending order details to admin chat_id: {admin_chat_id}")
                    bot.send_message(admin_chat_id, f"Новый заказ:\n\n{order_details}")

                else:
                    bot.send_message(chat_id, "Товар не найден.")
    except ValueError as e:
        bot.send_message(chat_id, f"Ошибка: {str(e)}")
    except (Exception, psycopg2.Error) as error:
        logging.error(f"Ошибка при подтверждении заказа: {error}")
        bot.send_message(chat_id, "Произошла ошибка при подтверждении заказа.")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_order")
def handle_cancel_order(call):
    bot.send_message(call.message.chat.id, "Заказ отменен.")



# --------------------------------------------------------------------------------------------------------


# Обработчик для выбора оплаты криптовалютой

@bot.message_handler(func=lambda message: message.text == "Оплатить криптовалютой")
def pay_with_crypto(message):
    instructions = """
    Выбран способ оплаты криптовалютой. Пожалуйста, следуйте инструкциям на экране:

    1. Откройте бота @send в Telegram.
    2. Выберите криптовалюту для оплаты.
    3. Скопируйте адрес получателя.
    4. Отправьте указанное количество криптовалюты на этот адрес.
    5. После завершения транзакции, отправьте сюда чек о проведении платежа.
    """

    bot.send_message(message.chat.id, instructions, parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(content_types=['photo'])
def handle_payment_receipt(message):
    chat_id = message.chat.id

    logging.info(f"Received photo from chat_id {chat_id}")

    if is_user_registered(chat_id):
        user_info = get_user_info(chat_id)
        if user_info is None:
            logging.error("Failed to get user info.")
            bot.send_message(chat_id, "Не удалось получить информацию о пользователе.")
            return

        items = get_cart_items(chat_id)
        if not items:
            logging.info("Cart is empty.")
            bot.send_message(chat_id, "Ваша корзина пуста.")
            return

        order_summary = []
        total_amount = 0
        for item in items:
            product_id, name, price, quantity = item
            try:
                price = float(price)
                quantity = int(quantity)
                total_amount += price * quantity
                order_summary.append(f"{name} - {quantity} шт. - {price} тг. за шт.")
            except ValueError:
                order_summary.append(f"{name} - {quantity} шт.")

        order_summary_text = "\n".join(order_summary)
        order_details = {
            'order_summary': order_summary_text,
            'total_amount': total_amount,
            'name': user_info.get('name', 'Не указано'),
            'address': user_info.get('address', 'Не указано'),
            'phone': user_info.get('phone', 'Не указано')
        }

        try:
            save_order(chat_id, order_details)
            logging.info("Order saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save order: {e}")

        admin_chat_id = GROUP_ID
        bot.forward_message(admin_chat_id, chat_id, message.message_id)
        bot.send_message(admin_chat_id, f"Пользователь оплатил заказ:\n\n{order_details}")

        bot.send_message(chat_id, "Спасибо за покупку! Ваш чек отправлен администратору.")
    else:
        bot.send_message(chat_id, "Вы не зарегистрированы. Пожалуйста, нажмите /start для регистрации.")


# --------------------------------------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_cart_"))
def handle_add_to_cart(call):
    try:
        # Получаем product_id из callback_data
        data = call.data.split('_')
        logging.info(f"Callback data: {data}")

        if len(data) != 4 or data[0] != 'add' or data[1] != 'to' or data[2] != 'cart':
            logging.error("Ошибка: некорректный формат callback_data.")
            bot.send_message(call.message.chat.id, "Ошибка: некорректный формат данных.")
            return

        product_id_str = data[3]
        logging.info(f"Extracted product_id_str: {product_id_str}")

        try:
            product_id = int(product_id_str)
            logging.info(f"Converted product_id: {product_id}")
        except ValueError as e:
            logging.error(f"Ошибка преобразования product_id: {e}")
            bot.send_message(call.message.chat.id, "Ошибка: некорректный идентификатор товара.")
            return

        chat_id = call.message.chat.id  # Получаем chat_id пользователя

        logging.info(f"Handling add to cart for user {chat_id} and product {product_id}")

        # Проверяем, существует ли пользователь в таблице users
        with psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                              database=DB_NAME) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
                user = cursor.fetchone()

                if user:
                    # Пользователь существует, добавляем товар в корзину
                    add_to_cart(chat_id, product_id)

                    # Создаем клавиатуру с кнопкой "Посмотреть корзину"
                    markup = types.InlineKeyboardMarkup()
                    view_cart_button = types.InlineKeyboardButton(
                        "Посмотреть корзину",
                        callback_data="view_cart"
                    )
                    markup.add(view_cart_button)

                    bot.send_message(
                        chat_id,
                        f"Товар с ID {product_id} добавлен в корзину.",
                        reply_markup=markup
                    )
                else:
                    # Пользователь не найден в базе данных
                    bot.send_message(chat_id, "Ошибка: вы не зарегистрированы. Нажмите /start для регистрации.")
    except (Exception, psycopg2.Error) as error:
        logging.error("Ошибка при обработке запроса: %s", error)
        bot.send_message(call.message.chat.id,
                         "Произошла ошибка при добавлении товара в корзину. Пожалуйста, попробуйте позже.")


@bot.callback_query_handler(func=lambda call: call.data == "view_cart")
def handle_view_cart(call):
    chat_id = call.message.chat.id
    logging.info(f"User {chat_id} requested to view cart")

    items = get_cart_items(chat_id)
    if items:
        response = "Ваша корзина:\n ----------------- \n"
        total_amount = 0
        markup = types.InlineKeyboardMarkup()

        for item in items:
            product_id, name, price, quantity = item
            try:
                price = float(price)
                quantity = int(quantity)
                total_amount += price * quantity
                response += (f" {name} "
                             f"\n Кол-во: {quantity} шт."
                             f"\n Цена: {price} тг. за шт.\n")
            except ValueError:
                logging.error(f"Ошибка преобразования данных для товара {product_id}.")
                response += f"{name} - {quantity} шт.\n"

        response += f" ----------------- \nИтого: {total_amount:.2f} тг."

        clear_cart_button = types.InlineKeyboardButton("Очистить корзину", callback_data="clear_cart")
        checkout_button = types.InlineKeyboardButton("Оформить заказ", callback_data="order_0")  # Передаем правильный идентификатор
        markup.add(clear_cart_button, checkout_button)

        bot.send_message(chat_id, response, reply_markup=markup)
    else:
        bot.send_message(chat_id, "Ваша корзина пуста.")


@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def handle_clear_cart(call):
    chat_id = call.message.chat.id
    logging.info(f"User {chat_id} requested to clear cart")

    try:
        clear_cart(chat_id)
        bot.send_message(chat_id, "Ваша корзина была очищена.")
    except Exception as e:
        logging.error(f"Ошибка при очистке корзины: {e}")
        bot.send_message(chat_id, "Произошла ошибка при очистке корзины. Пожалуйста, попробуйте позже.")







# Обработка команды /admin
@bot.message_handler(commands=['admin'])
def admin_commands(message):
    if str(message.chat.id) in ADMIN_IDS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('/add_category'))
        markup.add(types.KeyboardButton('/add_product'))
        # markup.add(types.KeyboardButton('/edit_product'))
        markup.add(types.KeyboardButton('/delete_product'))
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")





# Запуск бота
# def start_bot():
#     while True:
#         try:
#             logging.info("Запуск бота...")
#             bot.polling(none_stop=True, interval=0, timeout=20)
#         except apihelper.ApiTelegramException as e:
#             if e.result.status_code == 409:
#                 logging.error("Ошибка 409: Конфликт. Бот уже запущен в другом месте.")
#                 break  # Остановите цикл, если обнаружена ошибка 409
#             else:
#                 logging.error(f"ApiTelegramException: {e}")
#                 time.sleep(5)
#         except Exception as e:
#             logging.error(f"Ошибка при запуске бота: {e}")
#             time.sleep(5)




if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    bot.polling(none_stop=True, interval=0, timeout=60)
    # logging.basicConfig(level=logging.INFO)
    # start_bot()







