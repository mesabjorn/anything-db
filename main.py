from src.SQLiteManager import SQLiteManager, CLI_manage
import argparse


def main():
    parser = argparse.ArgumentParser(description="SQLite Database Manager")
    parser.add_argument("name", help="Name of the SQLite database file")
    args = parser.parse_args()

    db_manager = SQLiteManager(args.name)

    CLI_manage(db_manager)


if __name__ == "__main__":
    main()
