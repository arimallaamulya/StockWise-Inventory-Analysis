import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import mysql.connector
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "inventory_db")
    )

def query(sql, params=(), fetch=True):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall() if fetch else None
    if not fetch:
        conn.commit()
    cur.close()
    conn.close()
    return rows

def get_products():
    return query("""
        SELECT p.product_id, p.sku, p.product_name, p.category, p.reorder_level,
               p.unit_cost, p.opening_stock,
               p.opening_stock + COALESCE(SUM(
                   CASE WHEN t.transaction_type='IN' THEN t.quantity
                        WHEN t.transaction_type='OUT' THEN -t.quantity ELSE 0 END
               ),0) AS current_stock
        FROM products p
        LEFT JOIN stock_transactions t ON p.product_id=t.product_id
        GROUP BY p.product_id
        ORDER BY p.product_name
    """)

@app.route("/")
def dashboard():
    products = get_products()
    suppliers = query("SELECT COUNT(*) AS total FROM suppliers")[0]["total"]
    total_stock = sum(int(p["current_stock"]) for p in products)
    value = sum(float(p["current_stock"]) * float(p["unit_cost"]) for p in products)
    low_stock = [p for p in products if p["current_stock"] <= p["reorder_level"]]
    recent = query("""
        SELECT t.transaction_date, t.transaction_type, t.quantity, p.product_name
        FROM stock_transactions t JOIN products p ON p.product_id=t.product_id
        ORDER BY t.transaction_date DESC, t.transaction_id DESC LIMIT 6
    """)
    return render_template("dashboard.html", products=products, suppliers=suppliers,
                           total_stock=total_stock, value=value, low_stock=low_stock, recent=recent)

@app.route("/products", methods=["GET", "POST"])
def products_page():
    if request.method == "POST":
        try:
            query("""INSERT INTO products
                (sku, product_name, category, reorder_level, unit_cost, opening_stock)
                VALUES (%s,%s,%s,%s,%s,%s)""",
                (request.form["sku"].strip(), request.form["product_name"].strip(),
                 request.form.get("category","").strip(), int(request.form["reorder_level"]),
                 float(request.form["unit_cost"]), int(request.form["opening_stock"])), fetch=False)
            flash("Product added successfully.", "success")
        except Exception as e:
            flash(f"Could not add product: {e}", "error")
        return redirect(url_for("products_page"))
    return render_template("products.html", products=get_products())

@app.route("/suppliers", methods=["GET", "POST"])
def suppliers_page():
    if request.method == "POST":
        try:
            query("INSERT INTO suppliers (supplier_name, contact_name, email, phone) VALUES (%s,%s,%s,%s)",
                  (request.form["supplier_name"].strip(), request.form.get("contact_name","").strip(),
                   request.form.get("email","").strip(), request.form.get("phone","").strip()), fetch=False)
            flash("Supplier added successfully.", "success")
        except Exception as e:
            flash(f"Could not add supplier: {e}", "error")
        return redirect(url_for("suppliers_page"))
    suppliers = query("SELECT * FROM suppliers ORDER BY supplier_name")
    return render_template("suppliers.html", suppliers=suppliers)

def movement(kind):
    if request.method == "POST":
        try:
            product_id = int(request.form["product_id"])
            quantity = int(request.form["quantity"])
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
            conn = get_db()
            cur = conn.cursor()
            conn.start_transaction()
            cur.execute("""
                SELECT p.opening_stock + COALESCE(SUM(
                    CASE WHEN t.transaction_type='IN' THEN t.quantity
                         WHEN t.transaction_type='OUT' THEN -t.quantity ELSE 0 END
                ),0)
                FROM products p LEFT JOIN stock_transactions t ON p.product_id=t.product_id
                WHERE p.product_id=%s GROUP BY p.product_id FOR UPDATE
            """, (product_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError("Please select a valid product.")
            current = int(row[0])
            if kind == "OUT" and quantity > current:
                raise ValueError(f"Insufficient stock. Available quantity: {current}.")
            supplier_id = request.form.get("supplier_id") or None
            cur.execute("""INSERT INTO stock_transactions
                (product_id, transaction_date, transaction_type, quantity, supplier_id)
                VALUES (%s,%s,%s,%s,%s)""",
                (product_id, datetime.now(), kind, quantity, supplier_id if kind == "IN" else None))
            conn.commit()
            flash(f"Stock {kind.lower()} recorded successfully.", "success")
            cur.close()
            conn.close()
        except Exception as e:
            try:
                conn.rollback()
                cur.close()
                conn.close()
            except Exception:
                pass
            flash(str(e), "error")
        return redirect(url_for("add_stock" if kind == "IN" else "remove_stock"))
    products = get_products()
    suppliers = query("SELECT * FROM suppliers ORDER BY supplier_name")
    return render_template("movement.html", products=products, suppliers=suppliers, kind=kind)

@app.route("/stock-in", methods=["GET", "POST"])
def add_stock():
    return movement("IN")

@app.route("/stock-out", methods=["GET", "POST"])
def remove_stock():
    return movement("OUT")

@app.route("/transactions")
def transactions():
    rows = query("""SELECT t.*, p.product_name, p.sku, s.supplier_name
                    FROM stock_transactions t JOIN products p ON p.product_id=t.product_id
                    LEFT JOIN suppliers s ON s.supplier_id=t.supplier_id
                    ORDER BY t.transaction_date DESC, t.transaction_id DESC""")
    return render_template("transactions.html", rows=rows)

@app.route("/search")
def search():
    term = request.args.get("q","").strip()
    rows = []
    if term:
        like = f"%{term}%"
        rows = query("""SELECT p.*, p.opening_stock + COALESCE(SUM(
            CASE WHEN t.transaction_type='IN' THEN t.quantity
                 WHEN t.transaction_type='OUT' THEN -t.quantity ELSE 0 END
            ),0) AS current_stock
            FROM products p LEFT JOIN stock_transactions t ON p.product_id=t.product_id
            WHERE p.product_name LIKE %s OR p.sku LIKE %s OR p.category LIKE %s
            GROUP BY p.product_id ORDER BY p.product_name""", (like, like, like))
    return render_template("search.html", rows=rows, term=term)

@app.route("/graphs")
def graphs():
    products = get_products()
    movement_rows = query("""SELECT transaction_type, SUM(quantity) AS total
                             FROM stock_transactions GROUP BY transaction_type""")
    monthly = query("""SELECT DATE_FORMAT(transaction_date,'%Y-%m') AS month,
                       SUM(CASE WHEN transaction_type='IN' THEN quantity ELSE 0 END) AS stock_in,
                       SUM(CASE WHEN transaction_type='OUT' THEN quantity ELSE 0 END) AS stock_out
                       FROM stock_transactions GROUP BY month ORDER BY month""")
    os.makedirs(os.path.join("static","charts"), exist_ok=True)
    # Chart 1: current stock by product
    plt.figure(figsize=(9,4))
    if products:
        plt.bar([p["product_name"] for p in products], [p["current_stock"] for p in products])
        plt.xticks(rotation=25, ha="right")
    else:
        plt.text(.5,.5,"No products available",ha="center",va="center")
    plt.title("Current Stock by Product"); plt.tight_layout()
    plt.savefig("static/charts/current_stock.png"); plt.close()
    # Chart 2: stock in vs out
    totals = {r["transaction_type"]: r["total"] for r in movement_rows}
    plt.figure(figsize=(6,4))
    plt.bar(["Stock In","Stock Out"], [totals.get("IN",0), totals.get("OUT",0)])
    plt.title("Stock In vs Stock Out"); plt.tight_layout()
    plt.savefig("static/charts/movement.png"); plt.close()
    # Chart 3: monthly movement
    plt.figure(figsize=(9,4))
    if monthly:
        plt.plot([r["month"] for r in monthly], [r["stock_in"] for r in monthly], marker="o", label="Stock In")
        plt.plot([r["month"] for r in monthly], [r["stock_out"] for r in monthly], marker="o", label="Stock Out")
        plt.legend()
    else:
        plt.text(.5,.5,"Record stock movements to see monthly trends",ha="center",va="center")
    plt.title("Monthly Stock Movement"); plt.xticks(rotation=25); plt.tight_layout()
    plt.savefig("static/charts/monthly.png"); plt.close()
    return render_template("graphs.html", products=products)

@app.route("/reports")
def reports():
    products = get_products()
    low_stock = [p for p in products if p["current_stock"] <= p["reorder_level"]]
    total_value = sum(float(p["current_stock"]) * float(p["unit_cost"]) for p in products)
    return render_template("reports.html", products=products, low_stock=low_stock, total_value=total_value)

@app.errorhandler(Exception)
def handle_error(error):
    app.logger.exception(error)
    return render_template("error.html", message=str(error)), 500

if __name__ == "__main__":
    app.run(debug=True)
