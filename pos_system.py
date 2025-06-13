import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

# Database Initialization

conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# Create tables with proper schema
c.execute('''CREATE TABLE IF NOT EXISTS items (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             name TEXT UNIQUE,
             price REAL,
             stock INTEGER)''')

# Create transactions table with daily_id
c.execute('''CREATE TABLE IF NOT EXISTS transactions (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             daily_id INTEGER,
             date DATE,
             items TEXT,
             total REAL,
             timestamp DATETIME)''')

# Check and add missing columns

c.execute("PRAGMA table_info(transactions)")
columns = [column[1] for column in c.fetchall()]
if 'daily_id' not in columns:
    c.execute("ALTER TABLE transactions ADD COLUMN daily_id INTEGER")

c.execute('''CREATE TABLE IF NOT EXISTS stock_history (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             item_id INTEGER,
             adjustment INTEGER,
             timestamp DATETIME,
             FOREIGN KEY(item_id) REFERENCES items(id))''')

c.execute('''CREATE TABLE IF NOT EXISTS daily_sales (
             date DATE PRIMARY KEY,
             total_income REAL)''')

conn.commit()


class InventorySystem:

    def __init__(self):
        self.current_transaction = {}

    @staticmethod
    def get_items():
        c.execute("SELECT id, name, price, stock FROM items")
        return c.fetchall()

    @staticmethod
    def add_item(name, price, stock):
        try:
            c.execute("INSERT INTO items (name, price, stock) VALUES (?,?,?)",
                     (name, price, stock))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def update_stock(item_id, adjustment):
        c.execute("UPDATE items SET stock = stock + ? WHERE id = ?", (adjustment, item_id))
        c.execute("INSERT INTO stock_history (item_id, adjustment, timestamp) VALUES (?,?,?)",
                 (item_id, adjustment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()


    @staticmethod
    def remove_item(item_id):
        try:
            c.execute("DELETE FROM stock_history WHERE item_id = ?", (item_id,))
            c.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error removing item: {e}")
            return False

    @staticmethod
    def process_transaction(items, total):
        try:
            today = datetime.now().date().isoformat()

            # Validate stock first
            for item_name, qty in items.items():
                c.execute("SELECT id, stock FROM items WHERE name=?", (item_name,))
                result = c.fetchone()
                if not result:
                    raise ValueError(f"Item {item_name} not found")
                item_id, current_stock = result
                if current_stock < qty:
                    raise ValueError(f"Insufficient stock for {item_name}")

            # Process stock changes
            for item_name, qty in items.items():

                c.execute("SELECT id FROM items WHERE name=?", (item_name,))
                item_id = c.fetchone()[0]
                c.execute("UPDATE items SET stock = stock - ? WHERE id = ?", (qty, item_id))
                c.execute("INSERT INTO stock_history (item_id, adjustment, timestamp) VALUES (?,?,?)",

                         (item_id, -qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


                        # Get next daily_id
            c.execute("SELECT MAX(daily_id) FROM transactions WHERE date = ?", (today,))
            max_daily_id = c.fetchone()[0] or 0
            new_daily_id = max_daily_id + 1

            # Create transaction record
            items_str = ", ".join([f"{name}(x{qty})" for name, qty in items.items()])
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            c.execute('''INSERT INTO transactions
                       (daily_id, date, items, total, timestamp)
                       VALUES (?,?,?,?,?)''',
                     (new_daily_id, today, items_str, total, timestamp))

            # Update daily sales
            c.execute("INSERT OR IGNORE INTO daily_sales (date, total_income) VALUES (?, 0)", (today,))
            c.execute("UPDATE daily_sales SET total_income = total_income + ? WHERE date = ?", (total, today))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e

    @staticmethod
    def get_item_stock(item_id):
        c.execute("SELECT stock FROM items WHERE id=?", (item_id,))
        result = c.fetchone()
        return result[0] if result else 0


class BillingSystem:

    def __init__(self, root):
        self.root = root
        self.inventory = InventorySystem()
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)


    def setup_ui(self):
        self.root.title("Inventory & Billing System")
        self.root.geometry("1200x800")

        # Login Frame
        self.login_frame = ttk.Frame(self.root, padding=20)
        self.login_frame.pack(pady=50)

        ttk.Label(self.login_frame, text="Username:").grid(row=0, column=0)
        self.username_entry = ttk.Entry(self.login_frame)
        self.username_entry.grid(row=0, column=1)

        ttk.Label(self.login_frame, text="Password:").grid(row=1, column=0)
        self.password_entry = ttk.Entry(self.login_frame, show="*")
        self.password_entry.grid(row=1, column=1)

        ttk.Button(self.login_frame, text="Login",
                  command=self.authenticate).grid(row=2, columnspan=2, pady=10)

    def authenticate(self):
        if self.username_entry.get() == "admin" and self.password_entry.get() == "admin123":
            self.login_frame.destroy()
            self.show_main_app()
        else:
            messagebox.showerror("Error", "Invalid credentials")
