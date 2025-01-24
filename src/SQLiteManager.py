import sqlite3
import time
import re
from . import logger


def receive_yes_no(question: str) -> bool:
    yes_values = ["true", "1", "t", "y", "yes"]
    no_values = ["false", "0", "f", "n", "no"]

    while True:
        answer = input(question).lower().strip()
        if answer in yes_values or answer in no_values:
            break
        print(f"Unknown answer '{answer}'")

    return answer in yes_values


class Column:
    def __init__(self, name: str, _type: str, not_null: bool = False):
        self.name = name
        self.type = _type
        self.not_null = not_null == 1
        self.primary_key = False
        self.visible = self.name != "updated" and name != "id"

    def enter(self, isupdate=False):
        while True:
            value = input(f"Value for {self.name}: ({self.type})").strip()
            if isupdate or (len(value) > 0 and self.not_null) or not self.not_null:
                return value

            logger.warning(
                f"A value for '{self.name}' is required and cannot be empty."
            )

    def __str__(self):
        return (
            f"<Column {self.name}:{self.type} {'!REQUIRED!' if self.not_null else ''}>"
        )


class Schema:
    def __init__(self, name: str, columns: list[tuple]):
        self.name = name
        self.columns = [Column(name=c[1], _type=c[2], not_null=c[3]) for c in columns]

    def has_changed(self) -> bool:
        # returns whether or not this table has an update column named 'updated'
        return len([x.name == "updated" for x in self.columns]) > 0

    def enter_values(self) -> dict[str, str]:
        updates = {}
        for c in self.columns:
            if c.visible:
                updates[c.name] = c.enter()

        if self.has_changed():
            updates["updated"] = time.time()
        return updates

    def re_enter_values(self) -> dict[str, str]:
        updates = {}
        for c in self.columns:
            if c.visible:
                updates[c.name] = c.enter(isupdate=True)

        if self.has_changed():
            updates["updated"] = time.time()
        return updates

    def __str__(self):
        print(f"Schema for table '{self.name}':")
        for column in filter(lambda x: x.visible, self.columns):
            print(f"\t{column}")
        return ""


class Table:
    pass


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

    def select_table(self, prompt: str):
        # helper function for making sure proper table gets selected
        table = input(prompt)
        if table.isnumeric():
            return self.tables[int(table)]
        return table

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

    def read(self, table_name):
        select_query = f"SELECT * FROM {table_name};"
        self.cursor.execute(select_query)
        rows = self.cursor.fetchall()
        for row in rows:
            print(row)

    def update(self, table_name, condition, updates: dict[str, str]):
        self.get_table_schema(table_name)
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


def CLI_manage(db_manager):
    while True:
        print("-" * 25)
        print("1. List Tables")
        print("2. Create Table")
        print("3. Drop Table")
        print("4. Insert Record")
        print("5. Read Records")
        print("6. Update Record")
        print("7. Delete Record")
        print("8. Exit")

        choice = input("What do you want to do? ")

        if choice == "1":
            db_manager.list_tables()
        elif choice == "2":
            table_name = db_manager.select_table("Enter table name: ")
            db_manager.create_table(table_name)
        elif choice == "3":
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name to drop: ")
            db_manager.drop_table(table_name)
        elif choice == "4":
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name: ")
            schema = db_manager.get_table_schema(table_name)
            updates = schema.enter_values()
            db_manager.insert(table_name, updates)
        elif choice == "5":
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name: ")
            db_manager.read(table_name)
        elif choice == "6":
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name: ")
            schema = db_manager.get_table_schema(table_name)

            condition = input("Enter condition (e.g., id=1): ")
            updates = schema.re_enter_values()
            db_manager.update(table_name, condition, updates)
        elif choice == "7":
            db_manager.list_tables()
            table_name = db_manager.select_table("Enter table name: ")
            condition = input("Enter condition (e.g., id=1): ")
            db_manager.delete(table_name, condition)
        elif choice == "8":
            db_manager.close()
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please try again.")
