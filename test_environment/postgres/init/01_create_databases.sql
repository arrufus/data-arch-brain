-- Create bronze and silver databases
CREATE DATABASE bronze_db;
CREATE DATABASE silver_db;

\c bronze_db;

-- Create bronze schema
CREATE SCHEMA IF NOT EXISTS bronze;

-- Create bronze layer tables (sources)
CREATE TABLE bronze.customers (
    customer_id INTEGER PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country_code VARCHAR(2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bronze.orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date DATE,
    order_amount DECIMAL(10, 2),
    status VARCHAR(50),
    payment_method VARCHAR(50),
    shipping_address VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES bronze.customers(customer_id)
);

CREATE TABLE bronze.order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER,
    product_id INTEGER,
    product_name VARCHAR(255),
    quantity INTEGER,
    unit_price DECIMAL(10, 2),
    total_price DECIMAL(10, 2),
    FOREIGN KEY (order_id) REFERENCES bronze.orders(order_id)
);

-- Insert seed data into bronze layer
INSERT INTO bronze.customers (customer_id, first_name, last_name, email, phone, address, city, state, zip_code, country_code) VALUES
(1, 'John', 'Doe', 'john.doe@email.com', '555-0101', '123 Main St', 'New York', 'NY', '10001', 'US'),
(2, 'Jane', 'Smith', 'jane.smith@email.com', '555-0102', '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'US'),
(3, 'Bob', 'Johnson', 'bob.johnson@email.com', '555-0103', '789 Pine Rd', 'Chicago', 'IL', '60601', 'US'),
(4, 'Alice', 'Williams', 'alice.williams@email.com', '555-0104', '321 Elm St', 'Houston', 'TX', '77001', 'US'),
(5, 'Charlie', 'Brown', 'charlie.brown@email.com', '555-0105', '654 Maple Dr', 'Phoenix', 'AZ', '85001', 'US'),
(6, 'Diana', 'Davis', 'diana.davis@email.com', '555-0106', '987 Cedar Ln', 'Philadelphia', 'PA', '19101', 'US'),
(7, 'Eve', 'Martinez', 'eve.martinez@email.com', '555-0107', '147 Birch Way', 'San Antonio', 'TX', '78201', 'US'),
(8, 'Frank', 'Garcia', 'frank.garcia@email.com', '555-0108', '258 Spruce Ct', 'San Diego', 'CA', '92101', 'US'),
(9, 'Grace', 'Rodriguez', 'grace.rodriguez@email.com', '555-0109', '369 Willow Pl', 'Dallas', 'TX', '75201', 'US'),
(10, 'Henry', 'Wilson', 'henry.wilson@email.com', '555-0110', '741 Ash Blvd', 'San Jose', 'CA', '95101', 'US');

INSERT INTO bronze.orders (order_id, customer_id, order_date, order_amount, status, payment_method, shipping_address) VALUES
(101, 1, '2024-01-15', 150.00, 'completed', 'credit_card', '123 Main St, New York, NY 10001'),
(102, 1, '2024-02-20', 75.50, 'completed', 'credit_card', '123 Main St, New York, NY 10001'),
(103, 2, '2024-01-18', 200.00, 'completed', 'paypal', '456 Oak Ave, Los Angeles, CA 90001'),
(104, 3, '2024-02-10', 125.75, 'completed', 'credit_card', '789 Pine Rd, Chicago, IL 60601'),
(105, 2, '2024-03-05', 300.00, 'shipped', 'credit_card', '456 Oak Ave, Los Angeles, CA 90001'),
(106, 4, '2024-03-12', 89.99, 'processing', 'debit_card', '321 Elm St, Houston, TX 77001'),
(107, 5, '2024-03-15', 450.00, 'completed', 'credit_card', '654 Maple Dr, Phoenix, AZ 85001'),
(108, 6, '2024-03-20', 175.25, 'completed', 'paypal', '987 Cedar Ln, Philadelphia, PA 19101'),
(109, 7, '2024-04-01', 225.50, 'shipped', 'credit_card', '147 Birch Way, San Antonio, TX 78201'),
(110, 8, '2024-04-05', 95.00, 'completed', 'debit_card', '258 Spruce Ct, San Diego, CA 92101'),
(111, 9, '2024-04-10', 310.75, 'processing', 'credit_card', '369 Willow Pl, Dallas, TX 75201'),
(112, 10, '2024-04-15', 125.00, 'completed', 'paypal', '741 Ash Blvd, San Jose, CA 95101'),
(113, 1, '2024-04-20', 275.00, 'shipped', 'credit_card', '123 Main St, New York, NY 10001'),
(114, 3, '2024-04-22', 150.50, 'completed', 'credit_card', '789 Pine Rd, Chicago, IL 60601'),
(115, 5, '2024-04-25', 425.00, 'processing', 'paypal', '654 Maple Dr, Phoenix, AZ 85001');

INSERT INTO bronze.order_items (order_item_id, order_id, product_id, product_name, quantity, unit_price, total_price) VALUES
(1001, 101, 501, 'Laptop', 1, 150.00, 150.00),
(1002, 102, 502, 'Mouse', 2, 25.00, 50.00),
(1003, 102, 503, 'Keyboard', 1, 25.50, 25.50),
(1004, 103, 504, 'Monitor', 1, 200.00, 200.00),
(1005, 104, 505, 'Headphones', 1, 125.75, 125.75),
(1006, 105, 506, 'Desk Chair', 1, 300.00, 300.00),
(1007, 106, 507, 'Webcam', 1, 89.99, 89.99),
(1008, 107, 508, 'Standing Desk', 1, 450.00, 450.00),
(1009, 108, 509, 'USB Hub', 3, 58.42, 175.25),
(1010, 109, 510, 'Cable Management', 5, 45.10, 225.50),
(1011, 110, 511, 'Laptop Stand', 1, 95.00, 95.00),
(1012, 111, 512, 'Docking Station', 1, 310.75, 310.75),
(1013, 112, 513, 'External SSD', 1, 125.00, 125.00),
(1014, 113, 514, 'Graphics Tablet', 1, 275.00, 275.00),
(1015, 114, 515, 'Microphone', 1, 150.50, 150.50),
(1016, 115, 516, 'Ring Light', 2, 212.50, 425.00);

-- Create indexes for better query performance
CREATE INDEX idx_orders_customer_id ON bronze.orders(customer_id);
CREATE INDEX idx_orders_order_date ON bronze.orders(order_date);
CREATE INDEX idx_order_items_order_id ON bronze.order_items(order_id);

\c silver_db;

-- Create silver schema
CREATE SCHEMA IF NOT EXISTS silver;

-- Silver layer tables will be created by dbt models
-- But we can create the schema structure here for reference
COMMENT ON SCHEMA silver IS 'Silver layer - cleaned and conformed data';
