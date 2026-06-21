import pandas as pd
from utils.File_handling import Filehandle
import pdfplumber
from pathlib import Path
import re
import logging
from .db import get_connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TableProcessor:
    def __init__(self):
        self.conn = get_connection()  # Use the shared connection from db.py
        self.file_handler = Filehandle()

    def _extract_from_pdf(self, file_path):
        """Extracts tables from a PDF file and returns them as a list of DataFrames."""
        tables = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted_tables = page.extract_tables()
                    if not extracted_tables:
                        continue
                    for tbl_data in extracted_tables:
                        if not tbl_data:
                            continue
                        # Convert list of lists to DataFrame, assuming first row is header
                        header = tbl_data[0]
                        data = tbl_data[1:]
                        if not header or not any(h for h in header if h is not None):
                            df = pd.DataFrame(tbl_data)
                        else:
                            df = pd.DataFrame(data, columns=header)
                        df.dropna(how="all", axis=0, inplace=True)
                        df.dropna(how="all", axis=1, inplace=True)
                        if not df.empty:
                            tables.append(df)
        except Exception as e:
            logger.error(f"Error processing PDF file {file_path}: {e}")
        return tables

    def _extract_from_excel(self, file_path):
        """Extracts tables from an Excel file."""
        try:
            xls = pd.ExcelFile(file_path)
            tables = [pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names]
            return [table for table in tables if not table.empty]
        except Exception as e:
            logger.error(f"Error processing Excel file {file_path}: {e}")
            return []

    def _extract_from_csv(self, file_path):
        """Extracts table from a CSV file."""
        try:
            table = pd.read_csv(file_path)
            return [table] if not table.empty else []
        except Exception as e:
            logger.error(f"Error processing CSV file {file_path}: {e}")
            return []

    def _extract_from_docx(self, file_path):
        """Extracts tables from a DOCX file by parsing its text content."""
        try:
            text = self.file_handler.file_path(file_path)
            return self._text_to_tables(text)
        except Exception as e:
            logger.error(f"Error processing DOCX file {file_path}: {e}")
            return []

    def process_file(self, file_path):
        """
        Extracts tables from a given file and stores them in the SQLite database.
        """
        file_obj = Path(file_path)
        file_name = file_obj.stem  # Use stem to get name without extension
        file_ext = file_obj.suffix.lower()

        tables = []
        if file_ext == '.pdf':
            tables = self._extract_from_pdf(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            tables = self._extract_from_excel(file_path)
        elif file_ext == '.docx':
            tables = self._extract_from_docx(file_path)
        elif file_ext == '.csv':
            tables = self._extract_from_csv(file_path)
        else:
            logger.warning(f"Unsupported file format for table extraction: {file_ext}")
            return

        if not tables:
            logger.info(f"No tables found or extracted from {file_obj.name}.")
            return

        self._store_tables(tables, file_name)

    def _store_tables(self, tables, base_name):
        """Saves a list of DataFrames to the database."""
        safe_name = "".join(c if c.isalnum() else "_" for c in base_name)

        for i, table in enumerate(tables):
            if isinstance(table, pd.DataFrame) and not table.empty:
                table.columns = (
                    table.columns.str.strip()
                    .str.replace(" ", "_")
                    .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
                )
                table_name = f"{safe_name}_table_{i}"
                try:
                    table.to_sql(table_name, self.conn, if_exists="replace", index=False)
                    logger.info(f"Stored table '{table_name}' in database.")
                except Exception as e:
                    logger.error(f"Failed to store table '{table_name}': {e}")
            else:
                logger.warning(
                    f"Skipping empty or invalid table object at index {i} for {base_name}."
                )

    def _text_to_tables(self, text):
        """
        Attempts to convert plain text to tables by detecting patterns.
        This is a simple heuristic and may not be accurate.
        """
        lines = text.split("\n")
        tables = []
        current_table_data = []

        for line in lines:
            if "\t" in line or line.count("  ") > 2:
                parts = [x.strip() for x in line.split("\t") if x.strip()]
                if not parts:
                    parts = [x.strip() for x in re.split(r"\s{2,}", line) if x.strip()]

                if len(parts) > 1:
                    current_table_data.append(parts)
            else:
                if len(current_table_data) > 1:
                    try:
                        header = current_table_data[0]
                        data = current_table_data[1:]
                        if all(len(row) == len(header) for row in data):
                            df = pd.DataFrame(data, columns=header)
                            tables.append(df)
                    except Exception as e:
                        logger.warning(f"Could not form a DataFrame from text block: {e}")
                current_table_data = []

        if len(current_table_data) > 1:
            try:
                header = current_table_data[0]
                data = current_table_data[1:]
                if all(len(row) == len(header) for row in data):
                    df = pd.DataFrame(data, columns=header)
                    tables.append(df)
            except Exception as e:
                logger.warning(f"Could not form a DataFrame from final text block: {e}")

        return tables

    def _get_available_tables(self):
        """Lists all available tables in the database."""
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            tables_df = pd.read_sql(query, self.conn)
            return tables_df["name"].tolist()
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []

    def delete_tables_for_file(self, file_stem: str):
        """Deletes all tables associated with a given file stem from the database."""
        # The file_stem here is the raw stem, which needs to be sanitized
        # to match the table naming convention.
        safe_name = "".join(c if c.isalnum() else "_" for c in file_stem)
        tables_to_drop = [
            table for table in self._get_available_tables()
            if table.startswith(f"{safe_name}_table_")
        ]

        if not tables_to_drop:
            logger.info(f"No SQL tables to delete for file stem '{file_stem}'.")
            return

        try:
            cursor = self.conn.cursor()
            for table_name in tables_to_drop:
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                logger.info(f"Dropped table '{table_name}'.")
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error dropping tables for file stem '{file_stem}': {e}")
            self.conn.rollback()

    def execute_sql(self, sql_query: str):
        """
        Executes a SQL query on the database.
        Raises ValueError on failure.
        """
        try:
            result = pd.read_sql(sql_query, self.conn)
            return result
        except Exception as e:
            available_tables = self._get_available_tables()
            error_message = (
                f"Error executing query: {e}. "
                f"Please check your SQL syntax. Available tables are: {available_tables}"
            )
            logger.error(error_message)
            raise ValueError(error_message) from e
