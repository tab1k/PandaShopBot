import logging
import psycopg2
from psycopg2 import Error
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT


logging.basicConfig(level=logging.INFO)

# Функция для подключения к базе данных PostgreSQL
def connect_to_db():
    try:
        connection = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("Connected to PostgreSQL successfully")
        return connection
    except (Exception, Error) as error:
        print("Error while connecting to PostgreSQL", error)
        return None


# Получение информации о продукте по его имени
def get_product_info(name):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM products WHERE name = %s", (name,))
            product = cursor.fetchone()
            if product:
                return {
                    "name": product[1],
                    "price": product[3],
                    "sizes": product[4].split(','),  # Предположим, что размеры хранятся как строка с разделителем
                    "photo": product[5]
                }
            else:
                print(f"Product '{name}' not found in the database.")
                return None
        except (Exception, Error) as error:
            print("Error fetching product information:", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
                print("PostgreSQL connection is closed")
    else:
        return None


def insert_category(name):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO categories (name)
                VALUES (%s)
            """, (name,))
            connection.commit()
            print("Category inserted successfully")
        except (Exception, Error) as error:
            print("Error while inserting category:", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
                print("PostgreSQL connection is closed")


# Функция для вставки нового продукта в базу данных
def insert_product(product_name, category_id, price, sizes, photo_filename):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO products (name, category_id, price, sizes, photo) VALUES (%s, %s, %s, %s, %s)",
                           (product_name, category_id, price, sizes, photo_filename))
            connection.commit()
            return True
        except (Exception, Error) as error:
            print("Error inserting product:", error)
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()
                print("PostgreSQL connection is closed")
    else:
        return False


# Функция для добавления товара в корзину пользователя
def add_to_cart(user_id, product_id):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            logging.info(f"Adding product to cart for user_id: {user_id}, product_id: {product_id}")
            cursor.execute("""
                INSERT INTO carts (user_id, product_id, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, product_id) DO UPDATE
                SET quantity = carts.quantity + 1
            """, (user_id, product_id, 1))
            connection.commit()
            logging.info("Product added to cart successfully")
        except (Exception, Error) as error:
            logging.error("Error while adding product to cart: %s", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
                logging.info("PostgreSQL connection is closed")



# Пример использования:
# add_to_cart(1, 5)  # Добавить товар с ID=5 в корзину пользователя с ID=1


def get_cart_items(user_id):
    """Получает элементы корзины для пользователя."""
    connection = connect_to_db()
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.price, c.quantity
                    FROM carts c
                    JOIN products p ON c.product_id = p.id
                    WHERE c.user_id = %s
                """, (user_id,))
                items = cursor.fetchall()

                # Логирование всех элементов корзины
                for item in items:
                    logging.info(f"Fetched item: {item}")

                return items
        except (Exception, psycopg2.Error) as error:
            logging.error("Error while fetching cart items: %s", error)
            return []
        finally:
            if connection:
                connection.close()
                logging.info("PostgreSQL connection is closed")
    else:
        return []


def save_order(user_id, order_details):
    try:
        connection = connect_to_db()
        if connection:
            cursor = connection.cursor()
            logging.info(f"Saving order for user_id: {user_id} with details: {order_details}")

            # Убедитесь, что все необходимые данные присутствуют
            order_summary = order_details.get('order_summary', '')
            total_amount = order_details.get('total_amount', 0)
            name = order_details.get('name', 'Не указано')
            address = order_details.get('address', 'Не указано')
            phone = order_details.get('phone', 'Не указано')

            # Запишите данные в базу данных
            cursor.execute("""
                INSERT INTO orders (user_id, status, total_amount)
                VALUES (%s, 'pending', %s)
            """, (user_id, total_amount))
            connection.commit()

            logging.info("Order saved successfully.")
    except (Exception, psycopg2.Error) as error:
        logging.error(f"Error while saving order: {error}")
    finally:
        if connection:
            cursor.close()
            connection.close()
            logging.info("PostgreSQL connection is closed")



def clear_cart(chat_id):
    try:
        connection = connect_to_db()
        if connection:
            cursor = connection.cursor()
            logging.info(f"Clearing cart for chat_id: {chat_id}")
            cursor.execute("DELETE FROM carts WHERE user_id = %s", (chat_id,))
            connection.commit()
            logging.info("Cart cleared successfully.")
    except (Exception, psycopg2.Error) as error:
        logging.error(f"Error while clearing cart: {error}")
    finally:
        if connection:
            cursor.close()
            connection.close()
            logging.info("PostgreSQL connection is closed")





def clear_cart(chat_id):
    try:
        with psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, database=DB_NAME) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM carts WHERE user_id = %s", (chat_id,))
                connection.commit()
    except (Exception, psycopg2.Error) as error:
        logging.error("Ошибка при очистке корзины: %s", error)









# Функция для получения всех продуктов из базы данных
def get_all_products():
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM products")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
            return rows
        except (Exception, Error) as error:
            print("Error while fetching data:", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
                print("PostgreSQL connection is closed")


def get_all_categories():
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM categories")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
            return rows
        except (Exception, Error) as error:
            print("Error while fetching data:", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
                print("PostgreSQL connection is closed")


# Функция для получения продуктов по ID категории
def get_products_by_category(category_id):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM products WHERE category_id = %s", (category_id,))
            rows = cursor.fetchall()
            return rows
        except (Exception, Error) as error:
            print("Error while fetching data:", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
    return None


def get_product_by_id(product_id):
    try:
        # Подключение к базе данных
        connection = psycopg2.connect(
            user="tab1k",
            password="TOBI8585",
            host="localhost",
            port="5432",
            database="bot_db"
        )

        cursor = connection.cursor()

        # Запрос к базе данных для получения информации о продукте по ID
        cursor.execute(f"SELECT * FROM products WHERE id = {product_id}")
        product = cursor.fetchone()  # Получаем одну строку с информацией о продукте

        # Закрываем курсор и соединение с базой данных
        cursor.close()
        connection.close()

        return product  # Возвращаем информацию о продукте (кортеж)

    except (Exception, Error) as error:
        print("Ошибка при получении информации о продукте:", error)
        return None  # В случае ошибки возвращаем None




def delete_product_by_id(product_id):
    connection = psycopg2.connect(
        dbname="bot_db",
        user="tab1k",
        password="TOBI8585"
    )

    try:
        with connection.cursor() as cursor:
            # Удаляем продукт из корзин
            cursor.execute("DELETE FROM carts WHERE product_id = %s", (product_id,))
            # Удаляем продукт из основной таблицы
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            connection.commit()
            print(f"Product {product_id} deleted successfully.")
    except psycopg2.Error as e:
        print(f"Error deleting product {product_id}: {e}")
    finally:
        connection.close()


def clear_cart(user_id):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM carts WHERE user_id = %s", (user_id,))
            connection.commit()
            logging.info(f"Cart cleared for user {user_id}")
        except (Exception, psycopg2.Error) as error:
            logging.error("Error while clearing cart: %s", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
                logging.info("PostgreSQL connection is closed")





# Функция для получения информации о заказе из базы данных
def get_order_info(chat_id):
    order_info = None
    try:
        with psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                              database=DB_NAME) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM orders WHERE chat_id = %s", (chat_id,))
                order_info = cursor.fetchone()
    except (Exception, psycopg2.Error) as error:
        print(f"Error retrieving order information: {error}")

    return order_info


# Получение адреса и телефона
def get_user_info(chat_id):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            logging.info(f"Fetching user info for chat_id: {chat_id}")  # Логирование запроса
            cursor.execute("SELECT username, first_name, last_name FROM users WHERE chat_id = %s", (chat_id,))
            result = cursor.fetchone()
            logging.info(f"Query result: {result}")  # Логирование результата запроса

            if result:
                username = result[0] if result[0] else 'Не указано'
                first_name = result[1] if result[1] else 'Не указано'
                last_name = result[2] if result[2] else 'Не указано'

                user_info = {
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name
                }
                logging.info(f"User info retrieved: {user_info}")  # Логирование полученных данных
                return user_info
            else:
                logging.info("User not found.")
                return None
        except (Exception, psycopg2.Error) as error:
            logging.error("Error while fetching user info: %s", error)
            return None
        finally:
            if connection:
                cursor.close()
                connection.close()
                logging.info("PostgreSQL connection is closed")
    else:
        logging.error("Failed to connect to the database.")
        return None




