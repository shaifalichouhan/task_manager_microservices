-- Create database if it doesn't exist
SELECT 'CREATE DATABASE task_manager' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'task_manager')\gexec

-- Connect to the database
\c task_manager;

