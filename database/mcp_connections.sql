CREATE TABLE mcp_connections (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    service_name VARCHAR(100),
    access_token TEXT,
    refresh_token TEXT,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);