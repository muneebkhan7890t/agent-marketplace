CREATE TABLE installed_agents (
    id SERIAL PRIMARY KEY,
    business_id INTEGER REFERENCES businesses(id),
    agent_id INTEGER REFERENCES agents(id),
    status VARCHAR(50),
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);