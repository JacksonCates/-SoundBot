-- Use the newly created database
USE KiwiBot;

-- Create a new login for the user (if it doesn't exist)
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'discordbot')
BEGIN
    CREATE LOGIN discordbot WITH PASSWORD = 'kiwiismyfren';
END

-- Create a user in the database linked to the login
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'discordbot')
BEGIN
    CREATE USER discordbot FOR LOGIN discordbot;
END

-- Grant SELECT, INSERT, and ALTER permissions to the user
GRANT SELECT, INSERT, ALTER, UPDATE TO discordbot;


-- Create the 'sounds' table
CREATE TABLE sounds (
    [name] VARCHAR(255) NOT NULL,
    [id] INT PRIMARY KEY IDENTITY,
    emoji VARCHAR(255) NOT NULL,
    date_added DATETIME NOT NULL,
    mp3 VARCHAR(255) NOT NULL,
    added_by VARCHAR(255) NOT NULL,
    [type] VARCHAR(50) NOT NULL,
    [size] INT NOT NULL,
    [length] FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    is_deleted BIT NOT NULL DEFAULT 0
);

-- Create the 'requests' table
CREATE TABLE requests (
    [id] INT NOT NULL,
    requested_by VARCHAR(255) NOT NULL,
    date_requested DATETIME NOT NULL
);
