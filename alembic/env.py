from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Asegúrate de que 'Base' y los modelos estén correctamente importados
from src.core.models import Base  # Cambia 'core' por el nombre correcto de tu módulo

# Obtiene la configuración de Alembic
config = context.config  # Esto obtiene la configuración de 'alembic.ini'

# Asigna el metadata de Base a target_metadata
target_metadata = Base.metadata  # Esto le dice a Alembic qué tablas migrar

# Configuración de los logs
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")  # Obtiene la URL de la base de datos desde alembic.ini
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),  # Usa la configuración de alembic.ini
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# Ejecutar en modo offline u online según corresponda
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
