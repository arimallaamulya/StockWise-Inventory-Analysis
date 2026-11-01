CREATE DATABASE IF NOT EXISTS stockwise_v2_db;
USE stockwise_v2_db;

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(120) NOT NULL,
    contact_name VARCHAR(120),
    email VARCHAR(120),
    phone VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(100),
    reorder_level INT NOT NULL DEFAULT 0,
    unit_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
    opening_stock INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stock_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    transaction_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_type ENUM('IN','OUT') NOT NULL,
    quantity INT NOT NULL,
    supplier_id INT NULL,
    CONSTRAINT fk_transaction_product FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT fk_transaction_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    CONSTRAINT chk_transaction_quantity CHECK (quantity > 0)
);

INSERT IGNORE INTO suppliers (supplier_name, contact_name, email, phone)
VALUES ('Bright Office Supplies','Sales Team','sales@example.com','9000000001'),
       ('Campus Tech Traders','Support Team','support@example.com','9000000002');

INSERT IGNORE INTO products (sku, product_name, category, reorder_level, unit_cost, opening_stock)
VALUES ('PEN-001','Blue Ball Pen','Stationery',20,5.50,100),
       ('NOTE-001','Notebook A4','Stationery',15,42.00,50),
       ('USB-001','USB Drive 32GB','Electronics',5,350.00,12);
