import sqlite3
import time
import re

import pandas as pd

from src.Schema import Schema

from . import logger
from src.utils import receive_yes_no


# Mapping SQLite types to pandas types
sqlite_to_pandas = {
    "INTEGER": "int64",
    "TEXT": "object",
    "REAL": "float64",
    "NUMERIC": "float64",
    "BLOB": "object",
}


class SQLiteManager:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = sqlite3.connect(self.db_name)
        self.cursor = self.connection.cursor()

    def list_tables(self):
        if self.tables:
            print("Available tables:")
            for i, table in enumerate(self.tables):
                print(f"{i}. {table}")
        else:
            print("No tables found in the database.")
        return self.tables

    @property
    def tables(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [x[0] for x in self.cursor.fetchall()]

    def enter_new_table_name(self, prompt: str):
        table = input(prompt)
        return table

    def select_table(self, prompt: str):
        # helper function for making sure proper table gets selected
        while True:
            table = input(prompt)
            n_tables = len(self.tables)
            if table in self.tables:
                return table
            try:
                index = int(table)
                if index < 0 or index >= n_tables:
                    raise IndexError(
                        f"No such table index, please specify the name or the index between 0 and {len(self.tables) - 1}"
                    )
                return self.tables[index]
            except IndexError as e:
                logger.error(e)
            except Exception as e:
                logger.error(e)

    def select_condition(self, table_name: str, schema: Schema) -> str:
        """function to select a condition interactively from a table"""
        while True:
            a = input(
                'How would you like to select ("direct", "list","search","cancel")'
            )
            if a in ["direct", "list", "search", "cancel"]:
                break
            logger.warning(f"Unknown option: '{a}'. Please select a valid option.")

        if a == "list":
            self.read(table_name)

        if a == "search":
            r = []
            while len(r) == 0:
                q = input("Query: (format column=contents; e.g 'reeks=\"Asterix\"'):")
                if len(q) == 0:
                    break
                try:
                    column_name, value = [i.strip() for i in q.split("=")]
                    column = schema.column(column_name)
                    if not column:
                        raise Exception(
                            f"Column '{column_name}' not found in schema of '{table_name}'"
                        )
                    query = (
                        f"SELECT * FROM {table_name} "
                        f"WHERE {column.name} "
                        f"{'LIKE' if column.type == 'TEXT' else '='} "
                        f"{'?' if column.type == 'TEXT' else '?'} "
                        f"{'COLLATE NOCASE' if column.type == 'TEXT' else ''};"
                    )
                    params = (f"%{value}%" if column.type == "TEXT" else value,)
                    r = self.query(query, params)
                    df = self._as_dataframe(r, schema)
                    if not df.empty:
                        print(df)

                except sqlite3.OperationalError as e:
                    logger.warning(f"Invalid input: {e}")
                except Exception as e:
                    logger.warning(f"Invalid input: {e}")

        return input("Enter condition (e.g., id=1): ")

    def get_table_schema(self, table_name: str) -> Schema:
        "fetches schema from table in the form (index,name,type,not_null,default,auto_increment)"
        self.cursor.execute(f"PRAGMA table_info({table_name});")
        schema = Schema(table_name, self.cursor.fetchall())
        print(schema)
        return schema

    def create_table(self, table_name):
        if table_name in self.tables:
            logger.warning(
                "Table with this name already exists. Drop the table first, or enter another name."
            )
            return
        print("Define the columns for the table: ")
        print("Leave the column name empty to stop adding columns. ")
        columns = []
        while True:
            column_name = input("Column name: ").strip()
            if len(column_name) == 0:
                break
            column_type = (
                input(
                    "Column type (e.g., TEXT, INTEGER, REAL, BLOB). Add 'NN' or 'NOT NULL' for obligatory columns: "
                )
                .strip()
                .lower()
            )

            is_not_null = column_type.endswith(" nn") or column_type.endswith(
                " not null"
            )
            if is_not_null:
                column_type = re.sub(r"\snn$", "", column_type)
                column_type = re.sub(r"not null$", "", column_type)

            columns.append(
                f"{column_name} {column_type} {'NOT NULL' if is_not_null else ''}"
            )

        add_changed = receive_yes_no("Add a 'updated' column to track update times? ")
        if add_changed:
            columns.append("updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        columns.append("id INTEGER PRIMARY KEY AUTOINCREMENT")

        columns_definition = ", ".join(columns)
        create_table_query = (
            f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_definition});"
        )
        self.cursor.execute(create_table_query)
        self.connection.commit()
        print(f"Table '{table_name}' created successfully.")

    def drop_table(self, table_name):
        confirm = receive_yes_no(
            f"Are you sure you want to drop the table '{table_name}'? This action cannot be undone. (yes/no): "
        )
        if confirm:
            drop_table_query = f"DROP TABLE IF EXISTS {table_name};"
            self.cursor.execute(drop_table_query)
            self.connection.commit()
            print(f"Table '{table_name}' dropped successfully.")
        else:
            print("Operation cancelled.")

    def insert(self, table_name: str, updates: dict[str, str]):
        updates = {k: v for k, v in updates.items() if v}
        columns = ",".join([str(v) for v in updates.keys()])
        values = updates.values()
        placeholders = ", ".join(["?" for _ in values])
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
        try:
            self.cursor.execute(insert_query, list(values))
            self.connection.commit()
            print("Record inserted successfully.")
        except sqlite3.IntegrityError as e:
            logger.error(f"Invalid entry: '{e}'")

    def read(self, table_name: str, n: int = 10) -> pd.DataFrame:
        "read all rows"
        select_query = f"SELECT * FROM {table_name};"
        schema = self.get_table_schema(table_name)
        data = self.query(select_query)

        # Dictionary comprehension for columns mapped to pandas types
        df = self._as_dataframe(data, schema)
        print(df.iloc[:n])
        return

    def _as_dataframe(self, data, schema):
        dtypes = {
            column.name: sqlite_to_pandas.get(column.type.upper(), "object")
            for column in schema.columns
        }
        df = pd.DataFrame(data, columns=[c.name for c in schema.columns])
        df = df.astype(dtypes)

        return df

    def query(self, query: str, params: str = ""):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

        # for row in rows:
        #     print(row)

    def update(self, table_name, condition, updates: dict[str, str]):
        schema = self.get_table_schema(table_name)
        updates = {k: v for k, v in updates.items() if v}

        updates_str = ", ".join([f"{key} = ?" for key in updates.keys()])

        condition_column, condition_value = condition.split("=")
        condition_column = condition_column.strip()
        condition_value = condition_value.strip()
        values = list(updates.values())
        values.append(condition_value)
        update_query = (
            f"UPDATE {table_name} SET {updates_str} WHERE {condition_column} = ?;"
        )
        print(update_query)  # Debugging: Print the query to verify its correctness
        try:
            self.cursor.execute(update_query, values)
            self.connection.commit()
            print("Record updated successfully.")
        except sqlite3.Error as e:
            print(f"Error updating record: {e}")

    def delete(self, table_name, condition):
        delete_query = f"DELETE FROM {table_name} WHERE {condition};"
        self.cursor.execute(delete_query)
        self.connection.commit()
        print("Record deleted successfully.")

    def close(self):
        self.connection.close()


def CLI_manage(db_manager: SQLiteManager):
    while True:
        print("Press any key to continue..")
        input("")
        print("-" * 25)
        print("1. List Tables")
        print("2. Create Table")
        print("3. Drop Table")
        print("4. Insert Record")
        print("5. Read Records")
        print("6. Update Record")
        print("7. Delete Record")
        print("8. Exit")
        print("-" * 25)
        choice = input("What do you want to do? ")
        print("-" * 25)

        if choice == "1":
            db_manager.list_tables()
        elif choice == "2":  # create table
            table_name = db_manager.enter_new_table_name("Enter table name to create: ")
            db_manager.create_table(table_name)
        elif choice == "3":  # drop table
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name to drop: ")
            db_manager.drop_table(table_name)
        elif choice == "4":  # insert record into table
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name: ")
            schema = db_manager.get_table_schema(table_name)
            updates = schema.enter_values()
            db_manager.insert(table_name, updates)
        elif choice == "5":  # read records from table
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name: ")
            if table_name:
                db_manager.read(table_name)
        elif choice == "6":  # update record in table
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name: ")
            schema = db_manager.get_table_schema(table_name)
            condition = db_manager.select_condition(table_name, schema)
            if condition:
                updates = schema.re_enter_values()
                db_manager.update(table_name, condition, updates)
        elif choice == "7":
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name: ")
            schema = db_manager.get_table_schema(table_name)
            condition = db_manager.select_condition(table_name, schema)
            if condition:
                db_manager.delete(table_name, condition)
        elif choice == "8":
            db_manager.close()
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please try again.")
        print("-" * 25)
