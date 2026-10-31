"""
Online Shopping Management System
Python 3 + SQLite | CLI Major Project

Default admin:
    Username: admin
    Password: Admin@123

Customers can register through the main menu.
The SQLite database is created automatically on first run.
"""

import sqlite3
import hashlib
import hmac
import os
import csv
from datetime import datetime
from pathlib import Path

DB_NAME = "online_shopping.db"
EXPORT_DIR = Path("exports")


# --------------------------- DATABASE LAYER ---------------------------

def get_connection():
    """Create a database connection and enforce foreign-key constraints."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password, salt=None):
    """Hash a password using PBKDF2-HMAC-SHA256."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex() + "$" + digest.hex()


def verify_password(password, stored_hash):
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        calculated = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
        ).hex()
        return hmac.compare_digest(calculated, digest_hex)
    except (ValueError, TypeError):
        return False


def init_db():
    """Create all required tables and insert initial demonstration records."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'customer')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE COLLATE NOCASE
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL CHECK(price >= 0),
            stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(category_id) REFERENCES categories(category_id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL CHECK(total_amount >= 0),
            status TEXT NOT NULL DEFAULT 'Placed'
                CHECK(status IN ('Placed', 'Processing', 'Shipped', 'Delivered', 'Cancelled')),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            unit_price REAL NOT NULL CHECK(unit_price >= 0),
            line_total REAL NOT NULL CHECK(line_total >= 0),
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
                ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(product_id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        );
    """)

    # Seed admin account only when it does not already exist.
    admin = cur.execute("SELECT user_id FROM users WHERE username = 'admin'").fetchone()
    if not admin:
        cur.execute(
            """INSERT INTO users(full_name,email,username,password_hash,role)
               VALUES(?,?,?,?,?)""",
            ("System Administrator", "admin@example.com", "admin",
             hash_password("Admin@123"), "admin")
        )

    # Seed categories and sample products only when the product table is empty.
    if cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO categories(category_name) VALUES(?)",
            [("Electronics",), ("Fashion",), ("Home & Kitchen",), ("Books",), ("Sports",)]
        )

    if cur.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        category_ids = {
            row["category_name"]: row["category_id"]
            for row in cur.execute("SELECT category_id, category_name FROM categories")
        }
        demo_products = [
            ("Wireless Mouse", "Electronics", "2.4 GHz optical mouse", 599.00, 45),
            ("Bluetooth Headphones", "Electronics", "Over-ear wireless headphones", 1499.00, 30),
            ("USB-C Charger", "Electronics", "Fast charging adapter", 899.00, 25),
            ("Cotton T-Shirt", "Fashion", "Regular fit cotton T-shirt", 499.00, 60),
            ("Running Shoes", "Fashion", "Lightweight everyday running shoes", 1899.00, 18),
            ("Water Bottle", "Sports", "Reusable stainless steel bottle", 349.00, 50),
            ("Non-stick Pan", "Home & Kitchen", "Kitchen cooking pan", 799.00, 20),
            ("Python Programming Book", "Books", "Beginner programming guide", 650.00, 15),
        ]
        cur.executemany(
            """INSERT INTO products(product_name,category_id,description,price,stock_quantity)
               VALUES(?,?,?,?,?)""",
            [(name, category_ids[cat], desc, price, stock)
             for name, cat, desc, price, stock in demo_products]
        )

    conn.commit()
    conn.close()


# --------------------------- INPUT HELPERS ---------------------------

def line():
    print("-" * 72)


def pause():
    input("\nPress Enter to continue...")


def get_nonempty(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Input cannot be empty. Please try again.")


def get_int(prompt, minimum=None, maximum=None):
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
            if minimum is not None and value < minimum:
                print(f"Enter a value greater than or equal to {minimum}.")
                continue
            if maximum is not None and value > maximum:
                print(f"Enter a value less than or equal to {maximum}.")
                continue
            return value
        except ValueError:
            print("Please enter a valid whole number.")


def get_float(prompt, minimum=0):
    while True:
        try:
            value = float(input(prompt).strip())
            if value < minimum:
                print(f"Enter a value greater than or equal to {minimum}.")
                continue
            return round(value, 2)
        except ValueError:
            print("Please enter a valid number.")


def money(value):
    return f"₹{float(value):,.2f}"


# --------------------------- AUTHENTICATION ---------------------------

def register_customer():
    print("\nCUSTOMER REGISTRATION")
    line()
    name = get_nonempty("Full name: ")
    email = get_nonempty("Email: ")
    username = get_nonempty("Username: ")
    password = get_nonempty("Password (minimum 6 characters): ")
    if len(password) < 6:
        print("Password must contain at least 6 characters.")
        return

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO users(full_name,email,username,password_hash,role)
               VALUES(?,?,?,?, 'customer')""",
            (name, email, username, hash_password(password))
        )
        conn.commit()
        print("Registration successful. You can now log in.")
    except sqlite3.IntegrityError:
        print("That email or username is already registered.")
    except sqlite3.Error as exc:
        print(f"Database error during registration: {exc}")
    finally:
        conn.close()


def login():
    print("\nUSER LOGIN")
    line()
    username = get_nonempty("Username: ")
    password = get_nonempty("Password: ")
    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
        if user and verify_password(password, user["password_hash"]):
            print(f"\nWelcome, {user['full_name']}! Role: {user['role'].upper()}")
            return dict(user)
        print("Invalid username or password.")
        return None
    except sqlite3.Error as exc:
        print(f"Database error during login: {exc}")
        return None
    finally:
        conn.close()


# --------------------------- PRODUCT FUNCTIONS ---------------------------

def list_categories():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categories ORDER BY category_name").fetchall()
    conn.close()
    for row in rows:
        print(f"{row['category_id']}. {row['category_name']}")
    return rows


def display_products(search_term=None):
    conn = get_connection()
    query = """
        SELECT p.product_id, p.product_name, c.category_name, p.description,
               p.price, p.stock_quantity
        FROM products p JOIN categories c ON p.category_id = c.category_id
    """
    params = ()
    if search_term:
        query += " WHERE p.product_name LIKE ? OR c.category_name LIKE ?"
        params = (f"%{search_term}%", f"%{search_term}%")
    query += " ORDER BY p.product_id"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    line()
    print(f"{'ID':<5}{'PRODUCT':<27}{'CATEGORY':<18}{'PRICE':>10}{'STOCK':>8}")
    line()
    for r in rows:
        print(f"{r['product_id']:<5}{r['product_name'][:25]:<27}"
              f"{r['category_name'][:16]:<18}{money(r['price']):>10}{r['stock_quantity']:>8}")
    if not rows:
        print("No products found.")
    line()
    return rows


def add_category():
    name = get_nonempty("New category name: ")
    conn = get_connection()
    try:
        conn.execute("INSERT INTO categories(category_name) VALUES(?)", (name,))
        conn.commit()
        print("Category added successfully.")
    except sqlite3.IntegrityError:
        print("This category already exists.")
    finally:
        conn.close()


def add_product():
    print("\nADD PRODUCT")
    list_categories()
    category_id = get_int("Category ID: ", 1)
    name = get_nonempty("Product name: ")
    description = input("Description (optional): ").strip()
    price = get_float("Price: ")
    stock = get_int("Opening stock quantity: ", 0)
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO products(product_name,category_id,description,price,stock_quantity)
               VALUES(?,?,?,?,?)""",
            (name, category_id, description, price, stock)
        )
        conn.commit()
        print("Product added successfully.")
    except sqlite3.IntegrityError as exc:
        print(f"Could not add product. Check the category ID. Details: {exc}")
    finally:
        conn.close()


def update_product():
    display_products()
    product_id = get_int("Product ID to update: ", 1)
    conn = get_connection()
    product = conn.execute("SELECT * FROM products WHERE product_id=?", (product_id,)).fetchone()
    if not product:
        conn.close()
        print("Product ID not found.")
        return

    print("Leave a field blank to keep its current value.")
    name = input(f"Product name [{product['product_name']}]: ").strip() or product["product_name"]
    price_raw = input(f"Price [{product['price']}]: ").strip()
    stock_raw = input(f"Stock [{product['stock_quantity']}]: ").strip()
    description = input(f"Description [{product['description']}]: ").strip() or product["description"]

    try:
        price = float(price_raw) if price_raw else product["price"]
        stock = int(stock_raw) if stock_raw else product["stock_quantity"]
        if price < 0 or stock < 0:
            raise ValueError
        conn.execute(
            """UPDATE products SET product_name=?, price=?, stock_quantity=?, description=?
               WHERE product_id=?""",
            (name, price, stock, description, product_id)
        )
        conn.commit()
        print("Product updated successfully.")
    except ValueError:
        print("Invalid price or stock. Update cancelled.")
    except sqlite3.Error as exc:
        print(f"Database error: {exc}")
    finally:
        conn.close()


def delete_product():
    display_products()
    product_id = get_int("Product ID to delete: ", 1)
    confirm = input("Delete this product? (y/n): ").strip().lower()
    if confirm != "y":
        print("Deletion cancelled.")
        return
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM products WHERE product_id=?", (product_id,))
        conn.commit()
        print("Product deleted." if cur.rowcount else "Product ID not found.")
    except sqlite3.IntegrityError:
        print("This product is linked to an order and cannot be deleted.")
    except sqlite3.Error as exc:
        print(f"Database error: {exc}")
    finally:
        conn.close()


# --------------------------- CUSTOMER SHOPPING ---------------------------

def search_products():
    term = input("Enter product name or category to search: ").strip()
    display_products(term if term else None)


def place_order(user):
    display_products()
    cart = {}
    while True:
        product_id = get_int("Enter product ID (0 to finish): ", 0)
        if product_id == 0:
            break
        quantity = get_int("Quantity: ", 1)
        cart[product_id] = cart.get(product_id, 0) + quantity

    if not cart:
        print("Your cart is empty.")
        return

    conn = get_connection()
    try:
        conn.execute("BEGIN")
        validated_items = []
        total = 0.0

        for product_id, quantity in cart.items():
            product = conn.execute(
                "SELECT * FROM products WHERE product_id=?", (product_id,)
            ).fetchone()
            if not product:
                raise ValueError(f"Product ID {product_id} does not exist.")
            if product["stock_quantity"] < quantity:
                raise ValueError(
                    f"Insufficient stock for {product['product_name']}. "
                    f"Available: {product['stock_quantity']}."
                )
            line_total = round(product["price"] * quantity, 2)
            total += line_total
            validated_items.append((product, quantity, line_total))

        cur = conn.execute(
            "INSERT INTO orders(user_id,total_amount,status) VALUES(?,?, 'Placed')",
            (user["user_id"], round(total, 2))
        )
        order_id = cur.lastrowid

        for product, quantity, line_total in validated_items:
            conn.execute(
                """INSERT INTO order_items(order_id,product_id,quantity,unit_price,line_total)
                   VALUES(?,?,?,?,?)""",
                (order_id, product["product_id"], quantity, product["price"], line_total)
            )
            conn.execute(
                "UPDATE products SET stock_quantity=stock_quantity-? WHERE product_id=?",
                (quantity, product["product_id"])
            )

        conn.commit()
        print(f"Order placed successfully! Order ID: {order_id}")
        print(f"Order total: {money(total)}")
    except ValueError as exc:
        conn.rollback()
        print(f"Order not placed: {exc}")
    except sqlite3.Error as exc:
        conn.rollback()
        print(f"Database error. Order not placed: {exc}")
    finally:
        conn.close()


def customer_order_history(user):
    conn = get_connection()
    orders = conn.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY order_date DESC",
        (user["user_id"],)
    ).fetchall()
    if not orders:
        print("You have not placed any orders.")
    for order in orders:
        print(f"\nOrder #{order['order_id']} | {order['order_date']} | "
              f"{money(order['total_amount'])} | {order['status']}")
        items = conn.execute("""
            SELECT p.product_name, oi.quantity, oi.unit_price, oi.line_total
            FROM order_items oi JOIN products p ON p.product_id=oi.product_id
            WHERE oi.order_id=?
        """, (order["order_id"],)).fetchall()
        for item in items:
            print(f"  - {item['product_name']} x {item['quantity']} "
                  f"@ {money(item['unit_price'])} = {money(item['line_total'])}")
    conn.close()


# --------------------------- ADMIN ORDER MANAGEMENT ---------------------------

def view_all_orders():
    conn = get_connection()
    rows = conn.execute("""
        SELECT o.order_id, u.full_name, u.email, o.order_date, o.total_amount, o.status
        FROM orders o JOIN users u ON o.user_id=u.user_id
        ORDER BY o.order_date DESC
    """).fetchall()
    line()
    print(f"{'ORDER':<8}{'CUSTOMER':<22}{'DATE':<22}{'TOTAL':>12}  STATUS")
    line()
    for r in rows:
        print(f"{r['order_id']:<8}{r['full_name'][:20]:<22}{r['order_date'][:19]:<22}"
              f"{money(r['total_amount']):>12}  {r['status']}")
    if not rows:
        print("No orders have been placed.")
    line()
    conn.close()


def update_order_status():
    view_all_orders()
    order_id = get_int("Order ID: ", 1)
    statuses = ["Placed", "Processing", "Shipped", "Delivered", "Cancelled"]
    print("Available statuses:", ", ".join(statuses))
    status = get_nonempty("New status: ").title()
    if status not in statuses:
        print("Invalid status.")
        return

    conn = get_connection()
    try:
        order = conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        if not order:
            print("Order not found.")
            return
        if order["status"] == "Cancelled" and status != "Cancelled":
            print("A cancelled order cannot be reopened in this version.")
            return
        if status == "Cancelled" and order["status"] != "Cancelled":
            items = conn.execute(
                "SELECT product_id, quantity FROM order_items WHERE order_id=?", (order_id,)
            ).fetchall()
            for item in items:
                conn.execute(
                    "UPDATE products SET stock_quantity=stock_quantity+? WHERE product_id=?",
                    (item["quantity"], item["product_id"])
                )
        conn.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
        conn.commit()
        print("Order status updated.")
    except sqlite3.Error as exc:
        conn.rollback()
        print(f"Database error: {exc}")
    finally:
        conn.close()


# --------------------------- ANALYTICS AND EXPORT ---------------------------

def analytics_dashboard():
    conn = get_connection()
    print("\nSALES & BUSINESS ANALYTICS")
    line()
    summary = conn.execute("""
        SELECT COUNT(*) AS order_count,
               COALESCE(SUM(total_amount),0) AS revenue,
               COALESCE(AVG(total_amount),0) AS average_order_value
        FROM orders WHERE status != 'Cancelled'
    """).fetchone()
    product_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    customer_count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role='customer'"
    ).fetchone()[0]
    stock_units = conn.execute(
        "SELECT COALESCE(SUM(stock_quantity),0) FROM products"
    ).fetchone()[0]

    print(f"Total orders             : {summary['order_count']}")
    print(f"Total revenue            : {money(summary['revenue'])}")
    print(f"Average order value      : {money(summary['average_order_value'])}")
    print(f"Number of products       : {product_count}")
    print(f"Registered customers     : {customer_count}")
    print(f"Units currently in stock : {stock_units}")

    print("\nMONTHLY SALES")
    rows = conn.execute("""
        SELECT strftime('%Y-%m', order_date) AS sales_month,
               COUNT(*) AS orders, SUM(total_amount) AS revenue
        FROM orders
        WHERE status != 'Cancelled'
        GROUP BY strftime('%Y-%m', order_date)
        ORDER BY sales_month DESC LIMIT 12
    """).fetchall()
    for r in rows:
        print(f"{r['sales_month']}: {r['orders']} orders | {money(r['revenue'])}")

    print("\nTOP 5 SELLING PRODUCTS")
    rows = conn.execute("""
        SELECT p.product_name, SUM(oi.quantity) AS units_sold,
               SUM(oi.line_total) AS sales_value
        FROM order_items oi
        JOIN products p ON p.product_id=oi.product_id
        JOIN orders o ON o.order_id=oi.order_id
        WHERE o.status != 'Cancelled'
        GROUP BY p.product_id, p.product_name
        ORDER BY units_sold DESC LIMIT 5
    """).fetchall()
    for r in rows:
        print(f"{r['product_name']}: {r['units_sold']} units | {money(r['sales_value'])}")

    print("\nLOW STOCK PRODUCTS (5 OR FEWER UNITS)")
    low = conn.execute("""
        SELECT product_name, stock_quantity FROM products
        WHERE stock_quantity <= 5 ORDER BY stock_quantity
    """).fetchall()
    if low:
        for r in low:
            print(f"{r['product_name']}: {r['stock_quantity']} units")
    else:
        print("No low-stock products.")
    line()
    conn.close()


def export_analytics_csv():
    EXPORT_DIR.mkdir(exist_ok=True)
    conn = get_connection()
    exports = {
        "sales_summary.csv": """
            SELECT o.order_id, o.order_date, u.full_name AS customer_name,
                   u.email, o.status, o.total_amount
            FROM orders o JOIN users u ON u.user_id=o.user_id
            ORDER BY o.order_date
        """,
        "order_items.csv": """
            SELECT o.order_id, o.order_date, o.status, p.product_name,
                   c.category_name, oi.quantity, oi.unit_price, oi.line_total
            FROM order_items oi
            JOIN orders o ON o.order_id=oi.order_id
            JOIN products p ON p.product_id=oi.product_id
            JOIN categories c ON c.category_id=p.category_id
            ORDER BY o.order_date
        """,
        "product_inventory.csv": """
            SELECT p.product_id, p.product_name, c.category_name,
                   p.price, p.stock_quantity
            FROM products p JOIN categories c ON c.category_id=p.category_id
            ORDER BY p.product_name
        """
    }
    try:
        for filename, query in exports.items():
            rows = conn.execute(query).fetchall()
            path = EXPORT_DIR / filename
            with path.open("w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                if rows:
                    writer.writerow(rows[0].keys())
                    writer.writerows([tuple(row) for row in rows])
                else:
                    # Keep a header for empty exports.
                    writer.writerow([d[0] for d in conn.execute(query).description])
            print(f"Exported: {path}")
        print("\nImport these CSV files into Power BI for dashboard creation.")
    except (sqlite3.Error, OSError) as exc:
        print(f"Export failed: {exc}")
    finally:
        conn.close()


# --------------------------- MENUS ---------------------------

def admin_menu(user):
    while True:
        print("\n" + "=" * 72)
        print("ADMIN DASHBOARD")
        print("=" * 72)
        print("1. View products")
        print("2. Add product")
        print("3. Update product")
        print("4. Delete product")
        print("5. Add category")
        print("6. View all orders")
        print("7. Update order status")
        print("8. Sales and analytics dashboard")
        print("9. Export analytics data to CSV")
        print("0. Logout")
        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                display_products()
                pause()
            elif choice == "2":
                add_product()
                pause()
            elif choice == "3":
                update_product()
                pause()
            elif choice == "4":
                delete_product()
                pause()
            elif choice == "5":
                add_category()
                pause()
            elif choice == "6":
                view_all_orders()
                pause()
            elif choice == "7":
                update_order_status()
                pause()
            elif choice == "8":
                analytics_dashboard()
                pause()
            elif choice == "9":
                export_analytics_csv()
                pause()
            elif choice == "0":
                print("Logged out.")
                break
            else:
                print("Invalid menu selection.")
        except (sqlite3.Error, ValueError) as exc:
            print(f"Operation could not be completed: {exc}")


def customer_menu(user):
    while True:
        print("\n" + "=" * 72)
        print(f"CUSTOMER DASHBOARD - {user['full_name']}")
        print("=" * 72)
        print("1. Browse all products")
        print("2. Search products")
        print("3. Place an order")
        print("4. View my order history")
        print("0. Logout")
        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                display_products()
                pause()
            elif choice == "2":
                search_products()
                pause()
            elif choice == "3":
                place_order(user)
                pause()
            elif choice == "4":
                customer_order_history(user)
                pause()
            elif choice == "0":
                print("Logged out.")
                break
            else:
                print("Invalid menu selection.")
        except (sqlite3.Error, ValueError) as exc:
            print(f"Operation could not be completed: {exc}")


def main():
    init_db()
    while True:
        print("\n" + "=" * 72)
        print("ONLINE SHOPPING MANAGEMENT SYSTEM")
        print("=" * 72)
        print("1. Customer registration")
        print("2. Login")
        print("0. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            register_customer()
            pause()
        elif choice == "2":
            user = login()
            if user:
                if user["role"] == "admin":
                    admin_menu(user)
                elif user["role"] == "customer":
                    customer_menu(user)
            pause()
        elif choice == "0":
            print("Thank you for using the Online Shopping Management System.")
            break
        else:
            print("Invalid menu selection. Please choose 1, 2 or 0.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted. Goodbye.")
    except Exception as exc:
        print(f"Unexpected application error: {exc}")
