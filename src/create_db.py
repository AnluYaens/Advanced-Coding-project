from core.database import engine
from core.models import Base

# Crear todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)

print("Database created successfully!")
