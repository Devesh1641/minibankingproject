import sqlite3
import datetime
import logging
import os
from typing import List, Dict, Any, Optional

# --- Configuration & Logging Setup ---
DB_NAME = 'bank_data.db'
LOGS_DIR = 'logs'
LOG_FILE = os.path.join(LOGS_DIR, 'bank_errors.log')

# Ensure the logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging: INFO messages go to both console and file.
# Warnings and Errors are captured in the file.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler()
    ]
)

# --- 1. Database Management Class ---

class BankDatabase:
    """
    Handles all SQLite connection and table creation logic.
    All database operations are encapsulated here or within BaseEntity methods.
    """
    def __init__(self, db_name: str = DB_NAME):
        """Initializes the database connection and ensures tables exist."""
        # check_same_thread=False is necessary for multi-threaded access (e.g., Flask)
        self.conn = sqlite3.connect(db_name, check_same_thread=False) 
        self.cursor = self.conn.cursor()
        self.create_tables()
        
    def create_tables(self):
        """Creates all necessary tables for the banking system if they do not exist."""
        try:
            # Customers Table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    address TEXT,
                    join_date TEXT NOT NULL
                )
            ''')
            
            # Accounts Table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    balance REAL NOT NULL,
                    account_type TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
                )
            ''')
            
            # Transactions Table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    txn_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (account_id) REFERENCES accounts (account_id)
                )
            ''')

            # Employees Table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    position TEXT,
                    salary REAL
                )
            ''')
            
            # Loans Table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS loans (
                    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    interest_rate REAL NOT NULL,
                    status TEXT NOT NULL, -- Approved, Pending, Paid
                    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
                )
            ''')

            # Credit Cards Table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS credit_cards (
                    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    credit_limit REAL NOT NULL,
                    current_debt REAL NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
                )
            ''')
            
            self.conn.commit()
            logging.info(f"Database '{DB_NAME}' and tables initialized successfully.")
        except sqlite3.Error as e:
            logging.error(f"Failed to create database tables: {e}")

    def close(self):
        """Closes the database connection."""
        self.conn.close()
        logging.info("Database connection closed.")

# --- 2. Core Entities (OOP Model) ---

class BaseEntity:
    """
    Base class providing common methods for database interaction (CRUD).
    Implements core exception handling for SQL operations.
    """
    def __init__(self, db: BankDatabase):
        self._db = db

    def _fetch_record(self, table: str, id_field: str, id_value: int) -> Optional[tuple]:
        """Generic method to fetch a single record by ID."""
        sql = f"SELECT * FROM {table} WHERE {id_field} = ?"
        try:
            self._db.cursor.execute(sql, (id_value,))
            return self._db.cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"SQL Fetch Failed for {table} ID {id_value}: {e}")
            return None

    def _execute_dml(self, sql: str, params: tuple) -> Optional[int]:
        """Generic method to execute DML (Insert/Update) queries with error handling."""
        try:
            self._db.cursor.execute(sql, params)
            self._db.conn.commit()
            # Return the last inserted row ID for INSERT operations
            if sql.strip().upper().startswith("INSERT"):
                return self._db.cursor.lastrowid
            return 1 # Success indicator for UPDATE/DELETE
        except sqlite3.Error as e:
            logging.error(f"SQL DML Failed (Statement: {sql[:50]}...): {e}")
            return None

class Customer(BaseEntity):
    """Represents a bank customer."""
    def __init__(self, db: BankDatabase, customer_id: Optional[int] = None, first_name: str = '', last_name: str = '', address: str = '', join_date: Optional[str] = None):
        super().__init__(db)
        self._customer_id = customer_id
        self._first_name = first_name
        self._last_name = last_name
        self._address = address
        self._join_date = join_date if join_date else datetime.date.today().isoformat()
        
    # --- Getters ---
    @property
    def customer_id(self) -> Optional[int]: return self._customer_id
    @property
    def full_name(self) -> str: return f"{self._first_name} {self._last_name}"
    @property
    def address(self) -> str: return self._address
    
    # --- Setters (Example for Address with DB update) ---
    @address.setter
    def address(self, new_address: str):
        self._address = new_address
        if self._customer_id:
            sql = "UPDATE customers SET address = ? WHERE customer_id = ?"
            if self._execute_dml(sql, (new_address, self._customer_id)):
                logging.info(f"Customer {self._customer_id} address updated.")

    def save_new(self) -> Optional[int]:
        """Inserts a new customer record into the database."""
        sql = "INSERT INTO customers (first_name, last_name, address, join_date) VALUES (?, ?, ?, ?)"
        params = (self._first_name, self._last_name, self._address, self._join_date)
        new_id = self._execute_dml(sql, params)
        if new_id:
            self._customer_id = new_id
            logging.info(f"Customer {self.full_name} saved with ID {new_id}")
        return new_id
    
    @classmethod
    def load(cls, db: BankDatabase, customer_id: int) -> Optional['Customer']:
        """Loads a customer from the database by ID."""
        record = cls(db)._fetch_record('customers', 'customer_id', customer_id)
        if record:
            # record: (id, first_name, last_name, address, join_date)
            return cls(db, *record)
        logging.warning(f"Customer with ID {customer_id} not found.")
        return None

class Account(BaseEntity):
    """Represents a bank account (Checking or Savings)."""
    def __init__(self, db: BankDatabase, account_id: Optional[int] = None, customer_id: Optional[int] = None, balance: float = 0.0, account_type: str = 'Checking', is_active: int = 1):
        super().__init__(db)
        self._account_id = account_id
        self._customer_id = customer_id
        self._balance = balance
        self._account_type = account_type
        self._is_active = is_active
        
    # --- Getters ---
    @property
    def account_id(self) -> Optional[int]: return self._account_id
    @property
    def balance(self) -> float: return self._balance
    @property
    def account_type(self) -> str: return self._account_type
        
    def _record_transaction(self, txn_type: str, amount: float):
        """Records a transaction in the transactions table."""
        timestamp = datetime.datetime.now().isoformat()
        sql = "INSERT INTO transactions (account_id, txn_type, amount, timestamp) VALUES (?, ?, ?, ?)"
        self._execute_dml(sql, (self._account_id, txn_type, amount, timestamp))

    def deposit(self, amount: float) -> bool:
        """Adds funds to the account balance."""
        if amount <= 0: 
            logging.warning(f"Deposit failed for Account {self._account_id}: Amount must be positive.")
            return False
        
        sql = "UPDATE accounts SET balance = balance + ? WHERE account_id = ?"
        if self._execute_dml(sql, (amount, self._account_id)):
            self._balance += amount
            self._record_transaction('Deposit', amount)
            logging.info(f"Account {self._account_id}: Deposited ${amount:.2f}. New balance: ${self._balance:.2f}")
            return True
        return False

    def withdraw(self, amount: float) -> bool:
        """Removes funds from the account balance."""
        if amount <= 0: 
            logging.warning(f"Withdrawal failed for Account {self._account_id}: Amount must be positive.")
            return False
        if amount > self._balance:
            logging.warning(f"Withdrawal failed for Account {self._account_id}: Insufficient funds (Needed: ${amount:.2f}, Has: ${self._balance:.2f})")
            return False
            
        sql = "UPDATE accounts SET balance = balance - ? WHERE account_id = ?"
        if self._execute_dml(sql, (amount, self._account_id)):
            self._balance -= amount
            self._record_transaction('Withdrawal', amount)
            logging.info(f"Account {self._account_id}: Withdrew ${amount:.2f}. New balance: ${self._balance:.2f}")
            return True
        return False

    def save_new(self) -> Optional[int]:
        """Inserts a new account record into the database."""
        sql = "INSERT INTO accounts (customer_id, balance, account_type) VALUES (?, ?, ?)"
        params = (self._customer_id, self._balance, self._account_type)
        new_id = self._execute_dml(sql, params)
        if new_id:
            self._account_id = new_id
            logging.info(f"New {self._account_type} account opened with ID {new_id} for Customer {self._customer_id}")
        return new_id
    
    @classmethod
    def load(cls, db: BankDatabase, account_id: int) -> Optional['Account']:
        """Loads an account from the database by ID."""
        record = cls(db)._fetch_record('accounts', 'account_id', account_id)
        if record:
            # record: (id, customer_id, balance, account_type, is_active)
            return cls(db, *record)
        logging.warning(f"Account with ID {account_id} not found.")
        return None

class Employee(BaseEntity):
    """Represents a bank employee."""
    def __init__(self, db: BankDatabase, employee_id: Optional[int] = None, first_name: str = '', last_name: str = '', position: str = '', salary: float = 0.0):
        super().__init__(db)
        self._employee_id = employee_id
        self._first_name = first_name
        self._last_name = last_name
        self._position = position
        self._salary = salary

    @property
    def employee_id(self) -> Optional[int]: return self._employee_id
    @property
    def full_name(self) -> str: return f"{self._first_name} {self._last_name}"
    
    def save_new(self) -> Optional[int]:
        """Inserts a new employee record into the database."""
        sql = "INSERT INTO employees (first_name, last_name, position, salary) VALUES (?, ?, ?, ?)"
        params = (self._first_name, self._last_name, self._position, self._salary)
        new_id = self._execute_dml(sql, params)
        if new_id:
            self._employee_id = new_id
            logging.info(f"Employee {self.full_name} onboarded with ID {new_id}")
        return new_id

class Loan(BaseEntity):
    """Represents a loan service offered to a customer."""
    def __init__(self, db: BankDatabase, loan_id: Optional[int] = None, customer_id: Optional[int] = None, amount: float = 0.0, interest_rate: float = 0.05, status: str = 'Pending'):
        super().__init__(db)
        self._loan_id = loan_id
        self._customer_id = customer_id
        self._amount = amount
        self._interest_rate = interest_rate
        self._status = status
        
    @property
    def loan_id(self) -> Optional[int]: return self._loan_id
    @property
    def status(self) -> str: return self._status

    def approve(self) -> bool:
        """Approves the loan and updates the status in the DB."""
        if self._status == 'Pending' and self._loan_id:
            self._status = 'Approved'
            sql = "UPDATE loans SET status = ? WHERE loan_id = ?"
            if self._execute_dml(sql, (self._status, self._loan_id)):
                logging.info(f"Loan {self._loan_id} approved for Customer {self._customer_id}.")
                return True
        logging.warning(f"Loan {self._loan_id} could not be approved (Status: {self._status}).")
        return False
        
    def save_new(self) -> Optional[int]:
        """Submits a new loan application (Pending status)."""
        sql = "INSERT INTO loans (customer_id, amount, interest_rate, status) VALUES (?, ?, ?, ?)"
        params = (self._customer_id, self._amount, self._interest_rate, self._status)
        new_id = self._execute_dml(sql, params)
        if new_id:
            self._loan_id = new_id
            logging.info(f"Loan application for ${self._amount:.2f} submitted (ID {new_id})")
        return new_id

class CreditCard(BaseEntity):
    """Represents a credit card service."""
    def __init__(self, db: BankDatabase, card_id: Optional[int] = None, customer_id: Optional[int] = None, credit_limit: float = 1000.0, current_debt: float = 0.0, is_active: int = 1):
        super().__init__(db)
        self._card_id = card_id
        self._customer_id = customer_id
        self._credit_limit = credit_limit
        self._current_debt = current_debt
        self._is_active = is_active
        
    @property
    def credit_limit(self) -> float: return self._credit_limit
    @property
    def available_credit(self) -> float: return self._credit_limit - self._current_debt
    
    def make_purchase(self, amount: float) -> bool:
        """Simulates a purchase, increasing current debt."""
        if amount <= 0:
            logging.warning("Credit card purchase failed: Amount must be positive.")
            return False
            
        if amount > self.available_credit:
            logging.warning(f"Purchase failed for Card {self._card_id}: Exceeds available credit (Limit: ${self.available_credit:.2f})")
            return False
        
        self._current_debt += amount
        sql = "UPDATE credit_cards SET current_debt = ? WHERE card_id = ?"
        if self._execute_dml(sql, (self._current_debt, self._card_id)):
            logging.info(f"Card {self._card_id}: Purchase of ${amount:.2f} successful. New debt: ${self._current_debt:.2f}")
            return True
        return False

    def save_new(self) -> Optional[int]:
        """Inserts a new credit card record into the database."""
        sql = "INSERT INTO credit_cards (customer_id, credit_limit, current_debt) VALUES (?, ?, ?)"
        params = (self._customer_id, self._credit_limit, self._current_debt)
        new_id = self._execute_dml(sql, params)
        if new_id:
            self._card_id = new_id
            logging.info(f"Credit Card (Limit ${self._credit_limit:.2f}) issued with ID {new_id} for Customer {self._customer_id}")
        return new_id


# --- 3. Main Application Class and Menu Logic ---

class BankSystem:
    """Manages the overall operations of the bank and provides the user interface."""
    def __init__(self, db_name: str = DB_NAME):
        """Initializes the database connection."""
        self.db = BankDatabase(db_name)

    # --- Customer Menu Functions ---
    def create_customer(self):
        """Prompts for customer details and saves a new Customer record."""
        print("\n--- NEW CUSTOMER ENROLLMENT ---")
        first_name = input("Enter first name: ").strip()
        last_name = input("Enter last name: ").strip()
        address = input("Enter address: ").strip()

        if not first_name or not last_name:
            logging.warning("Customer creation failed: First and last names are required.")
            return

        customer = Customer(self.db, first_name=first_name, last_name=last_name, address=address)
        customer.save_new()

    def view_customer(self):
        """Prompts for customer ID and displays customer details."""
        try:
            customer_id = int(input("Enter Customer ID to view: "))
            customer = Customer.load(self.db, customer_id)
            if customer:
                print("\n--- CUSTOMER DETAILS ---")
                print(f"ID: {customer.customer_id}")
                print(f"Name: {customer.full_name}")
                print(f"Address: {customer.address}")
            else:
                logging.warning(f"Customer {customer_id} not found.")
        except ValueError:
            logging.error("Invalid input. Please enter a numerical ID.")
        except Exception as e:
            logging.error(f"Error viewing customer: {e}")

    # --- Account Menu Functions ---
    def create_account(self):
        """Prompts for account details and opens a new Account."""
        print("\n--- OPEN NEW ACCOUNT ---")
        try:
            customer_id = int(input("Enter Customer ID for the new account: "))
            if not Customer.load(self.db, customer_id):
                logging.warning(f"Cannot open account: Customer ID {customer_id} not found.")
                return

            account_type = input("Enter account type (Checking/Savings): ").strip().capitalize()
            initial_deposit = float(input("Enter initial deposit amount: "))

            if account_type not in ['Checking', 'Savings']:
                logging.warning("Invalid account type. Must be 'Checking' or 'Savings'.")
                return

            account = Account(self.db, customer_id=customer_id, balance=initial_deposit, account_type=account_type)
            account.save_new()
        except ValueError:
            logging.error("Invalid input. Please ensure ID and deposit amount are numbers.")
        except Exception as e:
            logging.error(f"Error creating account: {e}")

    def perform_transaction(self):
        """Handles deposit and withdrawal transactions."""
        print("\n--- ACCOUNT TRANSACTION ---")
        try:
            account_id = int(input("Enter Account ID: "))
            account = Account.load(self.db, account_id)

            if not account:
                logging.warning(f"Transaction failed: Account ID {account_id} not found.")
                return

            action = input("Perform (D)eposit or (W)ithdrawal? ").strip().upper()
            amount = float(input("Enter transaction amount: "))

            if action == 'D':
                account.deposit(amount)
            elif action == 'W':
                account.withdraw(amount)
            else:
                logging.warning("Invalid transaction type. Use 'D' for Deposit or 'W' for Withdrawal.")

        except ValueError:
            logging.error("Invalid input. Please enter numerical values for ID and amount.")
        except Exception as e:
            logging.error(f"Error performing transaction: {e}")

    # --- Employee Menu Functions ---
    def add_employee(self):
        """Prompts for employee details and saves a new Employee record."""
        print("\n--- ADD NEW EMPLOYEE ---")
        first_name = input("Enter first name: ").strip()
        last_name = input("Enter last name: ").strip()
        position = input("Enter position: ").strip()
        try:
            salary = float(input("Enter salary: "))
            emp = Employee(self.db, first_name=first_name, last_name=last_name, position=position, salary=salary)
            emp.save_new()
        except ValueError:
            logging.error("Invalid input for salary. Please enter a number.")
        except Exception as e:
            logging.error(f"Error adding employee: {e}")

    # --- Services Menu Functions ---
    def apply_for_loan(self):
        """Prompts for loan application details."""
        print("\n--- LOAN APPLICATION ---")
        try:
            customer_id = int(input("Enter Customer ID applying for loan: "))
            if not Customer.load(self.db, customer_id):
                logging.warning("Loan application failed: Customer ID not found.")
                return

            amount = float(input("Enter loan amount: "))
            rate = float(input("Enter interest rate (e.g., 0.05 for 5%): "))

            loan = Loan(self.db, customer_id=customer_id, amount=amount, interest_rate=rate)
            loan.save_new()

            # Optional: Automatic approval for demonstration purposes
            if input("Approve loan now? (y/n): ").strip().lower() == 'y':
                loan.approve()

        except ValueError:
            logging.error("Invalid input. Please enter numerical values for ID, amount, and rate.")

    def issue_credit_card(self):
        """Prompts for credit card issuance details."""
        print("\n--- ISSUE CREDIT CARD ---")
        try:
            customer_id = int(input("Enter Customer ID for credit card: "))
            if not Customer.load(self.db, customer_id):
                logging.warning("Credit card issuance failed: Customer ID not found.")
                return

            credit_limit = float(input("Enter credit limit: "))
            
            card = CreditCard(self.db, customer_id=customer_id, credit_limit=credit_limit)
            card.save_new()

        except ValueError:
            logging.error("Invalid input. Please enter numerical values for ID and limit.")
        except Exception as e:
            logging.error(f"Error issuing credit card: {e}")

    # --- Main Menu Loop ---
    def run_menu(self):
        """The main interactive menu loop for the banking system."""
        while True:
            print("\n==============================================")
            print("         BANK MANAGEMENT SYSTEM MENU")
            print("==============================================")
            print("1. Customer Management (Enroll/View)")
            print("2. Account Operations (Open/Deposit/Withdraw)")
            print("3. Employee Management (Onboard)")
            print("4. Service Applications (Loan/Credit Card)")
            print("5. Exit")
            
            choice = input("Enter your choice (1-5): ").strip()

            if choice == '1':
                self._customer_menu()
            elif choice == '2':
                self._account_menu()
            elif choice == '3':
                self.add_employee()
            elif choice == '4':
                self._services_menu()
            elif choice == '5':
                self.db.close()
                print("Exiting Banking System. Goodbye!")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")

    def _customer_menu(self):
        """Sub-menu for customer operations."""
        while True:
            print("\n--- CUSTOMER MENU ---")
            print("1. Create New Customer")
            print("2. View Customer Details")
            print("3. Back to Main Menu")
            sub_choice = input("Enter choice (1-3): ").strip()

            if sub_choice == '1':
                self.create_customer()
            elif sub_choice == '2':
                self.view_customer()
            elif sub_choice == '3':
                break
            else:
                print("Invalid choice.")

    def _account_menu(self):
        """Sub-menu for account operations."""
        while True:
            print("\n--- ACCOUNT MENU ---")
            print("1. Open New Account")
            print("2. Perform Deposit/Withdrawal")
            print("3. Back to Main Menu")
            sub_choice = input("Enter choice (1-3): ").strip()

            if sub_choice == '1':
                self.create_account()
            elif sub_choice == '2':
                self.perform_transaction()
            elif sub_choice == '3':
                break
            else:
                print("Invalid choice.")

    def _services_menu(self):
        """Sub-menu for loan and credit card services."""
        while True:
            print("\n--- SERVICE APPLICATIONS MENU ---")
            print("1. Apply for Loan")
            print("2. Issue Credit Card")
            print("3. Back to Main Menu")
            sub_choice = input("Enter choice (1-3): ").strip()

            if sub_choice == '1':
                self.apply_for_loan()
            elif sub_choice == '2':
                self.issue_credit_card()
            elif sub_choice == '3':
                break
            else:
                print("Invalid choice.")


if __name__ == '__main__':
    # Initialize the system and run the interactive menu
    bank = BankSystem()
    bank.run_menu()