-- Schema defining the final Analytical Base Table for the FLEMMS Data Science Project

CREATE TABLE flemms_analytical_base_table (
    id SERIAL PRIMARY KEY,
    region VARCHAR(100),
    province VARCHAR(100),
    municipality VARCHAR(100),
    household_serial_number VARCHAR(50),
    
    -- Demographics
    age INT,
    age_group VARCHAR(50),
    educational_attainment VARCHAR(100),
    
    -- Digital Divide Indicators
    has_internet_at_home BOOLEAN,
    owns_smartphone BOOLEAN,
    owns_computer BOOLEAN,
    digital_access_score FLOAT,
    
    -- Literacy Outcomes
    functional_literacy_score FLOAT,
    literacy_tier VARCHAR(50)
);