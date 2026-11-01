# StockWise – Inventory and Stock Analysis System

A Flask + MySQL inventory transaction and analysis application.

## Features
- Dashboard with product, stock, supplier and valuation summaries
- Product and supplier management
- Stock-in and stock-out transactions
- Prevents stock from becoming negative
- Product search by name, SKU or category
- Separate graphs and reports pages
- Low-stock reporting

## Setup (Windows PowerShell)
1. Open this folder in VS Code.
2. Create a virtual environment: `py -m venv .venv`
3. Activate it: `.\.venv\Scripts\Activate.ps1`
4. Install packages: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and enter your MySQL password.
6. In MySQL Workbench, run `schema.sql`.
7. Start the app: `python app.py`
8. Open `http://127.0.0.1:5000`

The app stores products, suppliers and stock transactions in MySQL. Do not commit `.env`.
