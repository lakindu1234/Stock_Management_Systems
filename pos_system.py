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


    def show_main_app(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)

        # Inventory Tab
        inv_tab = ttk.Frame(notebook)
        self.setup_inventory_tab(inv_tab)

        # Billing Tab
        bill_tab = ttk.Frame(notebook)
        self.setup_billing_tab(bill_tab)

        # Transactions Tab
        trans_tab = ttk.Frame(notebook)
        self.setup_transactions_tab(trans_tab)

        # Daily Sales Tab
        daily_tab = ttk.Frame(notebook)
        self.setup_daily_sales_tab(daily_tab)

        notebook.add(inv_tab, text="Inventory Management")
        notebook.add(bill_tab, text="Billing System")
        notebook.add(trans_tab, text="Transaction History")
        notebook.add(daily_tab, text="Daily Sales")
        notebook.pack(fill=tk.BOTH, expand=True)


    def setup_inventory_tab(self, parent):
        control_frame = ttk.Frame(parent)
        control_frame.pack(pady=10)

        ttk.Button(control_frame, text="Add New Item",
                  command=self.show_add_item_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Update Stock",
                  command=self.show_update_stock_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Remove Item",
                  command=self.show_remove_item_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Refresh",
                  command=self.update_inventory_list).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Name", "Price", "Stock")
        self.inventory_tree = ttk.Treeview(parent, columns=columns, show="headings")
        for col in columns:
            self.inventory_tree.heading(col, text=col)
            self.inventory_tree.column(col, width=100)
        self.inventory_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.update_inventory_list()


    def setup_billing_tab(self, parent):
        bill_frame = ttk.Frame(parent)
        bill_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(bill_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Label(left_frame, text="Select Item:").pack(pady=5)
        self.item_combo = ttk.Combobox(left_frame)
        self.item_combo.pack(pady=5)
        self.update_item_combo()

        ttk.Label(left_frame, text="Quantity:").pack(pady=5)
        self.quantity_entry = ttk.Entry(left_frame)
        self.quantity_entry.pack(pady=5)

        ttk.Button(left_frame, text="Add to Cart",
                  command=self.add_to_cart).pack(pady=10)

        right_frame = ttk.Frame(bill_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        columns = ("Item", "Price", "Quantity", "Subtotal")
        self.cart_tree = ttk.Treeview(right_frame, columns=columns, show="headings")
        for col in columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=120)
        self.cart_tree.pack(fill=tk.BOTH, expand=True)


        total_frame = ttk.Frame(right_frame)
        total_frame.pack(fill=tk.X, pady=10)

        ttk.Label(total_frame, text="Total:", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        self.total_label = ttk.Label(total_frame, text="$0.00", font=('Arial', 12, 'bold'))
        self.total_label.pack(side=tk.RIGHT, padx=10)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Remove Selected",
                  command=self.remove_from_cart).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Process Payment",
                  command=self.process_payment).pack(side=tk.RIGHT, padx=5)

    def setup_transactions_tab(self, parent):
        columns = ("Daily ID", "Date", "Items", "Total", "Timestamp")
        self.trans_tree = ttk.Treeview(parent, columns=columns, show="headings")
        for col in columns:
            self.trans_tree.heading(col, text=col)
            self.trans_tree.column(col, width=150)
        self.trans_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.update_transactions()

    def setup_daily_sales_tab(self, parent):
        columns = ("Date", "Total Income")
        self.daily_tree = ttk.Treeview(parent, columns=columns, show="headings")
        for col in columns:
            self.daily_tree.heading(col, text=col)
            self.daily_tree.column(col, width=150)
        self.daily_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.update_daily_sales()

    def update_item_combo(self):
        items = self.inventory.get_items()
        self.item_combo['values'] = [f"{item[0]} - {item[1]}" for item in items]

    def update_inventory_list(self):
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        for item in self.inventory.get_items():
            self.inventory_tree.insert("", tk.END, values=item)

    def update_transactions(self):
        for item in self.trans_tree.get_children():
            self.trans_tree.delete(item)
        c.execute("SELECT daily_id, date, items, total, timestamp FROM transactions ORDER BY timestamp DESC")
        for trans in c.fetchall():
            self.trans_tree.insert("", tk.END, values=(trans[0], trans[1], trans[2], f"${trans[3]:.2f}", trans[4]))

    def update_daily_sales(self):
        for item in self.daily_tree.get_children():
            self.daily_tree.delete(item)
        c.execute("SELECT * FROM daily_sales ORDER BY date DESC")
        for sale in c.fetchall():
            self.daily_tree.insert("", tk.END, values=(sale[0], f"RS.{sale[1]:.2f}"))


    def show_add_item_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Item")

        ttk.Label(dialog, text="Item Name:").grid(row=0, column=0, padx=5, pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Price:").grid(row=1, column=0, padx=5, pady=5)
        price_entry = ttk.Entry(dialog)
        price_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Initial Stock:").grid(row=2, column=0, padx=5, pady=5)
        stock_entry = ttk.Entry(dialog)
        stock_entry.grid(row=2, column=1, padx=5, pady=5)


        def save_item():
            try:
                name = name_entry.get().strip()
                price = float(price_entry.get())
                stock = int(stock_entry.get())

                if not name:
                    messagebox.showerror("Error", "Item name cannot be empty!")
                    return

                if price <= 0 or stock < 0:
                    messagebox.showerror("Error", "Price and stock must be positive values!")
                    return

                if self.inventory.add_item(name, price, stock):
                    self.update_inventory_list()
                    self.update_item_combo()
                    dialog.destroy()
                    messagebox.showinfo("Success", "Item added successfully!")

                else:
                    messagebox.showerror("Error", "Item with this name already exists!")
            except ValueError:
                messagebox.showerror("Error", "Invalid input values! Please check price and stock.")

        ttk.Button(dialog, text="Save", command=save_item).grid(row=3, columnspan=2, pady=10)


    def show_update_stock_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Stock")
        ttk.Label(dialog, text="Select Item:").grid(row=0, column=0, padx=5, pady=5)

        item_combo = ttk.Combobox(dialog)
        item_combo.grid(row=0, column=1, padx=5, pady=5)

        items = self.inventory.get_items()
        item_combo['values'] = [f"{item[0]} - {item[1]}" for item in items]

        ttk.Label(dialog, text="Quantity to Add:").grid(row=1, column=0, padx=5, pady=5)
        qty_entry = ttk.Entry(dialog)
        qty_entry.grid(row=1, column=1, padx=5, pady=5)


        def update_stock():
            try:
                selected = item_combo.get()
                if not selected:
                    raise ValueError("No item selected")
                item_id = int(selected.split(" - ")[0])
                qty = int(qty_entry.get())
                if qty <= 0:
                    raise ValueError("Quantity must be positive")

                self.inventory.update_stock(item_id, qty)
                self.update_inventory_list()
                dialog.destroy()
                messagebox.showinfo("Success", "Stock updated successfully!")
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        ttk.Bu8tton(dialog, text="Update", command=update_stock).grid(row=2, columnspan=2, pady=10)


    def show_remove_item_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Remove Item")

        ttk.Label(dialog, text="Select Item to Remove:").grid(row=0, column=0, padx=5, pady=5)

        item_combo = ttk.Combobox(dialog)
        item_combo.grid(row=0, column=1, padx=5, pady=5)
        items = self.inventory.get_items()
        item_combo['values'] = [f"{item[0]} - {item[1]}" for item in items]


        def remove_item():
            try:
                selected = item_combo.get()
                if not selected:
                    raise ValueError("No item selected")
                item_id = int(selected.split(" - ")[0])

                if self.inventory.remove_item(item_id):
                    self.update_inventory_list()
                    self.update_item_combo()
                    dialog.destroy()

                    messagebox.showinfo("Success", "Item removed successfully!")

                else:
                    messagebox.showerror("Error", "Failed to remove item")

            except ValueError as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(dialog, text="Remove", command=remove_item).grid(row=1, columnspan=2, pady=10)

    def add_to_cart(self):
        selected = self.item_combo.get()
        if not selected:
            messagebox.showerror("Error", "Please select an item")
            return

        try:
            item_id = int(selected.split(" - ")[0])
            qty = int(self.quantity_entry.get())
            if qty <= 0:
                raise ValueError
            except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return

        stock = self.inventory.get_item_stock(item_id)
        if qty > stock:
            messagebox.showerror("Error", "Insufficient stock")
            return
        item_name = selected.split(" - ")[1]
        if item_name in self.inventory.current_transaction:
          self.inventory.current_transaction[item_name] += qty
        else:
          self.inventory.current_transaction[item_name] = qty
          
        self.update_cart_display()
        self.quantity_entry.delete(0, tk.END)

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:   
          return
          
        item = self.cart_tree.item(selected[0])['values'][0]
        del self.inventory.current_transaction[item]
        self.update_cart_display()
      
    def update_cart_display(self):
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)

        total = 0.0
        c.execute("SELECT name, price FROM items")
        prices = {row[0]: row[1] for row in c.fetchall()}

        for item, qty in self.inventory.current_transaction.items():
            price = prices[item]
            subtotal = price * qty
            total += subtotal
            self.cart_tree.insert("", tk.END,
                                values=(item, f"${price:.2f}", qty, f"${subtotal:.2f}"))
        self.total_label.config(text=f"${total:.2f}")

    def process_payment(self):
        if not self.inventory.current_transaction:
            messagebox.showerror("Error", "Cart is empty")
            return

        total = float(self.total_label.cget("text")[1:])

        try:
            if self.inventory.process_transaction(self.inventory.current_transaction, total):
                self.update_inventory_list()
                self.update_transactions()
                self.update_daily_sales()
                self.inventory.current_transaction.clear()
                self.update_cart_display()
                messagebox.showinfo("Success", "Payment processed successfully!")
              
        except Exception as e:
            messagebox.showerror("Error", f"Transaction failed: {str(e)}")

      def on_close(self):
        today = datetime.now().date().isoformat()
        c.execute("SELECT total_income FROM daily_sales WHERE date = ?", (today,))
        total_income = c.fetchone()
