import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Carpeta core/Database.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Subir dos niveles para llegar a la raiz del proyecto
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir, os.pardir))
DB_FILE = os.path.join(ROOT_DIR, 'budget_tracker.db')


DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Soporte multihilo de SQLite
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
Base = declarative_base()

# Crear tablas si no existen
def init_db():
    Base.metadata.create_all(bind=engine)