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


