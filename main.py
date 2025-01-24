from src.SQLiteManager import SQLiteManager, CLI_manage
import argparse

from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="SQLite Database Manager")
    parser.add_argument(
        "dbpath",
        help="Path to the SQLite database file (created if does not yet exist)",
        type=Path,
    )
    args = parser.parse_args()

    db_manager = SQLiteManager(args.dbpath)

    CLI_manage(db_manager)


if __name__ == "__main__":
    main()
