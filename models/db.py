import sqlite3
import atexit
import os

# Construct a robust path to the database file, assuming it's in the project root.
# This makes the script runnable from any directory.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_PROJECT_ROOT, 'data.db')

_connection = None

def get_connection():
    """
    Returns a singleton database connection.
    The connection is automatically closed when the program exits.
    """
    global _connection
    if _connection is None or is_connection_closed():
        try:
            _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
            # Register the closing function to be called on program exit.
            atexit.register(_close_connection)
        except sqlite3.OperationalError as e:
            print(f"Error: Could not connect to database at '{DB_PATH}'.")
            print(f"Details: {e}")
            # Re-raise the exception to halt execution if the DB is critical.
            raise
    return _connection

def _close_connection():
    """Closes the global database connection if it is open."""
    global _connection
    if _connection:
        _connection.close()
        _connection = None

def init_db():
    """Initializes the database using the schema.sql file."""
    try:
        conn = get_connection()
        # Construct a robust path to the schema file.
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
        with open(schema_path) as f:
            conn.executescript(f.read())
    except FileNotFoundError:
        print(f"Error: 'schema.sql' not found. Make sure it is in the 'models' directory.")
    except sqlite3.Error as e:
        print(f"An error occurred during DB initialization: {e}")

def is_connection_closed():
    global _connection

    if _connection is None:
        return True

    try:
        _connection.execute("SELECT 1")
        return False
    except sqlite3.ProgrammingError:
        return True
