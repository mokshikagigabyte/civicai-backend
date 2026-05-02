from database import engine, Base
from sqlalchemy import inspect

def inspect_db():
    inspector = inspect(engine)
    print("Tables in database:")
    for table_name in inspector.get_table_names():
        print(f"Table: {table_name}")
        for column in inspector.get_columns(table_name):
            print(f"  Column: {column['name']} ({column['type']})")

if __name__ == "__main__":
    inspect_db()
