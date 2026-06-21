from utils.Chunks_vectorization import store_text_as_vectors, process_query
from utils.gemini_handler import (
    generate_answer,
    generate_sql_from_query,
    classify_query
)
from models.table_processor import TableProcessor
from models.db import get_connection
from utils.chroma_utils import delete_chroma_folder

import sys
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

# Before running the main file run the below statement on terminal one time
# python -c "from models.db import init_db; init_db()"
# Make a .env and add "GEMINI_API_KEY" from "https://aistudio.google.com/api-keys"

current_file = None

def select_file_via_gui():
    """Opens a GUI to select a file."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a File",
        filetypes=[
            ("All Supported", "*.pdf *.docx *.xlsx *.xls *.csv"),
            ("PDF files", "*.pdf"),
            ("Word documents", "*.docx"),
            ("Excel spreadsheets", "*.xlsx *.xls"),  # Corrected typo
            ("CSV files", "*.csv"),
        ],
    )
    return file_path


def get_table_schema():
    """Retrieves the schema for all tables in the SQLite database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    schema = ""
    for (table_name,) in tables:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schema += f"Table: {table_name}\n"
        for col in columns:
            schema += f"  - {col[1]} ({col[2]})\n"
    return schema


def select_table(tables):
    """
    Prompts the user to select a table from a list.
    Returns the selected table name or None if no tables are available.
    """
    if not tables:
        print("No tables found in the database.")
        return None

    if len(tables) == 1:
        return tables[0]

    print("\nAvailable tables:")
    for i, table_name in enumerate(tables, 1):
        print(f"  {i}. {table_name}")

    while True:
        try:
            selection_str = input(
                f"Enter table number to query (1-{len(tables)}), or press Enter for the first: "
            ).strip()
            if not selection_str:
                print("Using first table by default.")
                return tables[0]

            selection_idx = int(selection_str) - 1
            if 0 <= selection_idx < len(tables):
                return tables[selection_idx]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def handle_sql_query(query, table_processor):
    """Handles a query that appears to be a SQL request."""
    # It's better to have a public method for this.
    # For now, we'll use the private one as in the original code.
    tables = table_processor._get_available_tables()

    table_name = select_table(tables)
    if not table_name:
        return

    try:
        table_schema = get_table_schema()
        sql_query = generate_sql_from_query(
            f"{query} (use table: {table_name})", table_schema
        )
        print("\nGenerated SQL:\n", sql_query)
    except Exception as e:
        print(f"Error generating SQL query: {e}")
        return

    try:
        result = table_processor.execute_sql(sql_query)
        print("\nQuery Result:")
        print(result)
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return

    # Assuming `result` is a pandas DataFrame, as suggested by `.to_csv`
    if result is not None and not result.empty:
        save = input("\nSave results to file? (y/n): ").lower()
        if save == "y":
            output_file = input(
                "Enter output filename (e.g., results.csv): "
            ).strip()
            if output_file:
                try:
                    result.to_csv(output_file, index=False)
                    print(f"Results saved to {output_file}")
                except Exception as e:
                    print(f"Error saving file: {e}")


def handle_text_query(query, selected_file):
    """Handles a general text query using vector search."""
    try:
        responses = process_query(query, selected_file)
        if not responses:
            print("No relevant content found.")
            return

        context = "\n\n".join(item["text"]for item in responses)
        prompt = f"Based on the following content, answer the user's question:\n\n{context}\n\nQuestion: {query}"
        answer = generate_answer(prompt)
        print("\nGemini says:\n")
        print(answer)
        print("\nSources:")

        for item in responses:
            meta = item["metadata"]
            print(
                f"- {meta['source']} "
                f"(Chunk {meta['chunk_id'] + 1}/"
                f"{meta['total_chunks']})"
            )
    except Exception as e:
        print(f"An error occurred while generating the answer: {e}")


def remove_existing_file(table_processor):
    """Handles the logic for removing an existing file and its data."""
    existing_files = get_existing_files()
    if not existing_files:
        print("\nNo files found in the database to remove.")
        return

    print("\nPlease choose a file to remove:")
    for i, file_name in enumerate(existing_files, 1):
        print(f"  {i}. {file_name}")

    while True:
        try:
            choice_str = input(
                f"Enter file number (1-{len(existing_files)}), or 'b' to go back: "
            ).strip().lower()
            if choice_str == 'b':
                return

            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(existing_files):
                selected_file_stem = existing_files[choice_idx]
                confirm = input(
                    f"Are you sure you want to permanently remove '{selected_file_stem}'? (y/n): "
                ).strip().lower()
                if confirm in ['y', 'yes']:
                    print(f"\nRemoving data for '{selected_file_stem}'...")
                    delete_chroma_folder(f"chroma_db/{selected_file_stem}")
                    table_processor.delete_tables_for_file(selected_file_stem)
                    print(f"Successfully removed '{selected_file_stem}'.")
                else:
                    print("Removal cancelled.")
                return  # Return to main menu after action
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_existing_files():
    """Returns a list of existing file stems from the chroma_db directory."""
    db_root = Path("chroma_db")
    if not db_root.exists():
        return []
    return [d.name for d in db_root.iterdir() if d.is_dir()]


def show_tables_for_file(file_stem, table_processor):
    """Displays the tables associated with a given file stem."""
    safe_file_stem = "".join(c if c.isalnum() else "_" for c in file_stem)
    all_tables = table_processor._get_available_tables()
    file_tables = [
        table for table in all_tables if table.startswith(f"{safe_file_stem}_table_")
    ]
    if file_tables:
        print(f"\nTables found in '{file_stem}':")
        for table_name in file_tables:
            print(f"  - {table_name}")
    else:
        print(f"\nNo tables found in '{file_stem}'.")


def work_with_existing_files(table_processor):
    """Handles the logic for selecting and working with an existing file."""
    global current_file
    existing_files = get_existing_files()
    if not existing_files:
        print("\nNo files found in the database.")
        return False

    print("\nPlease choose an existing file to work with:")
    for i, file_name in enumerate(existing_files, 1):
        print(f"  {i}. {file_name}")

    while True:
        try:
            choice_str = input(f"Enter file number (1-{len(existing_files)}), or 'b' to go back: ").strip().lower()
            if choice_str == 'b':
                return False
            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(existing_files):
                selected_file = existing_files[choice_idx]
                current_file = selected_file
                print(f"\nYou have selected '{selected_file}'.")
                show_tables_for_file(selected_file, table_processor)
                return True  # Proceed to chat
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def add_new_file(table_processor):
    """Handles the logic for adding a new file."""
    global current_file
    file_path = select_file_via_gui()
    if not file_path:
        print("No file selected.")
        return False  # Go back to main menu

    file_obj = Path(file_path)
    file_stem = file_obj.stem
    current_file = file_stem

    existing_files = get_existing_files()
    if file_stem in existing_files:
        choice = input(
            f"A file named '{file_stem}' already exists. Do you want to remove it and replace it? (y/n): "
        ).strip().lower()
        if choice not in ['y', 'yes']:
            print("Operation cancelled.")
            return False  # Go back to main menu

        # Delete old data
        print(f"Removing existing data for '{file_stem}'...")
        delete_chroma_folder(f"chroma_db/{file_stem}")
        table_processor.delete_tables_for_file(file_stem)
        print("Existing data removed.")

    print("\nProcessing new file... This may take a moment.")
    store_text_as_vectors(file_path)
    table_processor.process_file(file_path)
    print("File processed successfully.")
    show_tables_for_file(file_stem, table_processor)
    return True  # Proceed to chat


def start_chat_session(table_processor):
    """The main query loop for the chatbot."""
    global current_file
    while True:
        query = input("\nAsk something (or type 'back' to return to the main menu, 'exit' to quit): ").strip()
        if not query:
            continue
        if query.lower() == "exit":
            print("Exiting chatbot. Goodbye!")
            sys.exit(0)
        if query.lower() == 'back':
            print("\nReturning to main menu...")
            break

        try:
            classification = classify_query(query)
            print(f"\nDetected Query Type: {classification}")
            if classification == "SQL":
                handle_sql_query(query, table_processor)
            else:
                handle_text_query(query, current_file)
        except Exception as e:
            print(f"\nAn unexpected error occurred while processing your query: {e}")
            print("Please try a different query or restart the application.")


def main():
    print("=== Simple Chatbot ===")
    try:
        table_processor = TableProcessor()

        while True:
            print("\n--- Main Menu ---")
            print("1. Work with an existing file")
            print("2. Add a new file")
            print("3. Remove an existing file")
            print("4. Exit")
            choice = input("Please choose an option (1-4): ").strip()

            if choice == '1':
                if work_with_existing_files(table_processor):
                    start_chat_session(table_processor)
            elif choice == '2':
                if add_new_file(table_processor):
                    start_chat_session(table_processor)
            elif choice == '3':
                remove_existing_file(table_processor)
            elif choice == '4':
                print("Exiting chatbot. Goodbye!")
                break
            else:
                print("Invalid choice. Please enter a number from 1 to 4.")

    except Exception as e:
        print(f"A critical error occurred: {e}")


if __name__ == "__main__":
    main()