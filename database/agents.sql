CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    category VARCHAR(100),
    monthly_price DECIMAL(10,2),
    status VARCHAR(50)
);