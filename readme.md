Simple OOP Banking System Model

This project implements a simple, object-oriented model of a banking system using Python. It demonstrates key OOP principles (Encapsulation, Inheritance) combined with persistent data storage using SQLite and robust logging.

Features

Entities: Models core banking entities: Customer, Account, Employee, Loan, and CreditCard.

Persistence: All data (customers, accounts, transactions, etc.) is stored in a serverless SQLite database (bank_data.db).

Transactions: Implements atomic deposit and withdraw operations with validation (e.g., sufficient funds).

Encapsulation: Properties are accessed via @property getters and updated via setter methods and direct transactional logic.

Logging: Uses the built-in logging module to output general information to the console and capture errors/warnings into a dedicated log file.

Project Structure

File/Folder

Description

banking_system.py

Contains all class definitions, the database management logic, and the main execution code (BankSystem).

bank_data.db

(Generated at runtime) The SQLite database file storing all records.

logs/

(Generated at runtime) Folder containing bank_errors.log.

logs/bank_errors.log

Log file recording all WARNING and ERROR messages during execution.

README.md

This documentation file.

How the Program Works

The banking_system.py file is structured into three main sections:

1. Database Management (BankDatabase)

This class initializes the SQLite connection and creates all necessary tables upon instantiation. The data structure includes:

customers

accounts

employees

loans

credit_cards

transactions

2. Core Entities (Customer, Account, Loan, CreditCard, Employee)

These classes represent the data entities. They inherit from BaseEntity, which provides generic methods (_fetch_record, _execute_dml) for interacting with the database cursor. All business logic (e.g., balance checks in withdraw, credit limit checks in make_purchase) is implemented here.

3. Main Application (BankSystem)

The run_simulation() method orchestrates a demonstration:

Creates employees and customers.

Opens checking and savings accounts.

Performs deposits (success) and withdrawals (success and failure).

Applies for and approves loans.

Issues credit cards and attempts purchases (success and exceeding limit).

Execution and Logging

Running the Program

The program is executable directly:

python banking_system.py


Logging Implementation

The logging system is configured to meet the following requirements:

Log Level

Destination

Purpose

INFO

Console & bank_errors.log

Confirms successful operations (Customer creation, deposit, loan approval).

WARNING

Console & bank_errors.log

Captures expected failures in business logic (Insufficient funds, credit limit exceeded).

ERROR

Console & bank_errors.log

Captures critical failures (SQLite database connection errors, SQL syntax errors).

After running the script, the logs/bank_errors.log file will contain a chronological record of all database errors and warning events, providing a clear audit trail.