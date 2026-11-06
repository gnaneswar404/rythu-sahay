from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Worker

settings = get_settings()
database_url = settings.supabase_database_url or settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_compatible_schema():
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    binary_type = "BYTEA" if engine.dialect.name == "postgresql" else "BLOB"
    with engine.begin() as connection:
        if "farmers" in tables:
            columns = {column["name"] for column in inspector.get_columns("farmers")}
            for name, column_type in (
                ("latitude", "FLOAT"),
                ("longitude", "FLOAT"),
                ("username", "VARCHAR(32)"),
                ("password_hash", "VARCHAR(255)"),
                ("profile_photo_data", binary_type),
                ("profile_photo_media_type", "VARCHAR(32)"),
                ("allow_phone_contact", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ):
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE farmers ADD COLUMN {name} {column_type}"))
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_farmers_username ON farmers (username)"
            ))

        if "workers" in tables:
            columns = {column["name"] for column in inspector.get_columns("workers")}
            for name, column_type in (
                ("username", "VARCHAR(32)"),
                ("password_hash", "VARCHAR(255)"),
                ("profile_photo_data", binary_type),
                ("profile_photo_media_type", "VARCHAR(32)"),
                ("allow_phone_contact", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ):
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE workers ADD COLUMN {name} {column_type}"))
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_workers_username ON workers (username)"
            ))

    if "workers" in tables and engine.dialect.name == "sqlite":
        phone_column = next(
            (column for column in inspector.get_columns("workers") if column["name"] == "phone"),
            None,
        )
        if phone_column is not None and not phone_column["nullable"]:
            columns = [column.name for column in Worker.__table__.columns]
            column_list = ", ".join(columns)
            with engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.commit()
                try:
                    with connection.begin():
                        connection.exec_driver_sql(
                            f"CREATE TABLE workers_compat AS SELECT {column_list} FROM workers"
                        )
                        connection.exec_driver_sql("DROP TABLE workers")
                        Worker.__table__.create(connection)
                        connection.exec_driver_sql(
                            f"INSERT INTO workers ({column_list}) SELECT {column_list} FROM workers_compat"
                        )
                        connection.exec_driver_sql("DROP TABLE workers_compat")
                finally:
                    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    elif "workers" in tables and engine.dialect.name == "postgresql":
        phone_column = next(
            (column for column in inspector.get_columns("workers") if column["name"] == "phone"),
            None,
        )
        if phone_column is not None and not phone_column["nullable"]:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE workers ALTER COLUMN phone DROP NOT NULL"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
