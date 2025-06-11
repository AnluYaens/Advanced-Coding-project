import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea base antes de tocar los modelos - evita el import circular
Base = declarative_base()

# SQLite setup con paths absolutos
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir, os.pardir))
DB_FILE = os.path.join(ROOT_DIR, 'budget_tracker.db')

# Crear directorio si no existe
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_FILE}"

# Engine con configuración optimizada
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    echo=False,  # Cambiar a True para debug SQL
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Habilitar WAL mode para SQLite (mejor concurrencia)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Importar modelos después de Base
from .models import Budget, Expense

@contextmanager
def get_db_session():
    """Context manager para manejo seguro de sesiones de BD."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error en la base de datos: {e}")
        raise
    finally:
        session.close()

def init_db() -> None:
    """Crear tablas si no existen."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Base de datos inicializada correctamente")
        
        # Crear datos de ejemplo si es la primera vez
        with get_db_session() as session:
            if session.query(Budget).count() == 0:
                _create_sample_data(session)
                
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        raise

def _create_sample_data(session):
    """Crear datos de ejemplo para demostración."""
    try:
        # Presupuestos por defecto
        default_budgets = [
            Budget(category="total", limit=2000.0),
            Budget(category="groceries", limit=600.0),
            Budget(category="entertainment", limit=300.0),
            Budget(category="electronics", limit=500.0),
            Budget(category="other", limit=200.0),
        ]
        
        for budget in default_budgets:
            session.add(budget)
        
        # Algunos gastos de ejemplo
        sample_expenses = [
            Expense(amount=50.0, category="Groceries", description="Supermercado semanal", date=datetime(2025, 1, 15)),
            Expense(amount=25.0, category="Entertainment", description="Cine", date=datetime(2025, 2, 20)),
            Expense(amount=120.0, category="Electronics", description="Audífonos", date=datetime(2025, 3, 10)),
            Expense(amount=75.0, category="Groceries", description="Compras del mes", date=datetime(2025, 4, 5)),
            Expense(amount=40.0, category="Entertainment", description="Videojuego", date=datetime(2025, 5, 12)),
        ]
        
        for expense in sample_expenses:
            session.add(expense)
            
        logger.info("Datos de ejemplo creados")
        
    except Exception as e:
        logger.error(f"Error creando datos de ejemplo: {e}")

# ──────────────────────── FUNCIONES DE PRESUPUESTO ────────────────────────

def save_budget(budget_dict: Dict[str, float]) -> None:
    """Insertar o actualizar límites de presupuesto."""
    try:
        with get_db_session() as session:
            for category, limit in budget_dict.items():
                if limit < 0:
                    raise ValueError(f"El límite para {category} no puede ser negativo")
                
                obj = (
                    session.query(Budget)
                    .filter(Budget.category == category.lower())
                    .first()
                )
                if obj:
                    obj.limit = limit
                else:
                    obj = Budget(category=category.lower(), limit=limit)
                    session.add(obj)
        
        logger.info(f"Presupuesto guardado: {budget_dict}")
        
    except Exception as e:
        logger.error(f"Error guardando presupuesto: {e}")
        raise

def get_budget() -> Dict[str, float]:
    """Retornar presupuestos como diccionario {category: limit}."""
    try:
        with get_db_session() as session:
            budgets = session.query(Budget).all()
            return {b.category: b.limit for b in budgets}
            
    except Exception as e:
        logger.error(f"Error obteniendo presupuesto: {e}")
        return {}

# ──────────────────────── FUNCIONES DE GASTOS ────────────────────────────

def add_expense(amount: float, category: str, description: str = "") -> None:
    """Persistir una nueva fila de gasto."""
    try:
        if amount <= 0:
            raise ValueError("El monto debe ser mayor que cero")
        
        with get_db_session() as session:
            exp = Expense(
                amount=amount,
                category=category.capitalize(),
                description=description.strip(),
                date=datetime.utcnow(),
            )
            session.add(exp)
        
        logger.info(f"Gasto agregado: ${amount} en {category}")
        
    except Exception as e:
        logger.error(f"Error agregando gasto: {e}")
        raise

def get_all_expenses() -> List[Expense]:
    """Obtener todos los gastos."""
    try:
        with get_db_session() as session:
            return session.query(Expense).order_by(Expense.date.desc()).all()
            
    except Exception as e:
        logger.error(f"Error obteniendo gastos: {e}")
        return []

def get_expenses_by_month(month: int, year: int) -> List[Expense]:
    """Obtener gastos de un mes específico."""
    try:
        with get_db_session() as session:
            return (
                session.query(Expense)
                .filter(
                    Expense.date.month == month,
                    Expense.date.year == year
                )
                .order_by(Expense.date.desc())
                .all()
            )
            
    except Exception as e:
        logger.error(f"Error obteniendo gastos del mes {month}/{year}: {e}")
        return []

# ──────────────────────── FUNCIONES DEL CHATBOT ────────────────────────────

def insert_payment(amount: float, category: str, description: str, date: str) -> None:
    """Insertar pago desde el chatbot."""
    try:
        if amount <= 0:
            raise ValueError("El monto debe ser mayor que cero")
        
        # Parsear fecha
        if isinstance(date, str):
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        else:
            date_obj = date
        
        with get_db_session() as session:
            exp = Expense(
                amount=amount,
                category=category.capitalize(),
                description=description.strip(),
                date=date_obj,
            )
            session.add(exp)
        
        logger.info(f"Pago insertado por AI: ${amount} en {category}")
        
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        raise
    except Exception as e:
        logger.error(f"Error insertando pago: {e}")
        raise

def delete_payment(expense_id: int) -> bool:
    """Eliminar pago por ID."""
    try:
        with get_db_session() as session:
            exp = session.query(Expense).filter(Expense.id == expense_id).first()
            if exp:
                session.delete(exp)
                logger.info(f"Gasto eliminado: ID {expense_id}")
                return True
            else:
                logger.warning(f"Gasto no encontrado: ID {expense_id}")
                return False
                
    except Exception as e:
        logger.error(f"Error eliminando pago: {e}")
        raise

def query_expenses_by_category(category: str) -> float:
    """Consultar total de gastos por categoría."""
    try:
        with get_db_session() as session:
            expenses = (
                session.query(Expense)
                .filter(Expense.category == category.capitalize())
                .all()
            )
            total = sum(e.amount for e in expenses)
            
        logger.info(f"Consulta por categoría {category}: ${total}")
        return total
        
    except Exception as e:
        logger.error(f"Error consultando gastos por categoría: {e}")
        return 0.0

def get_expense_summary() -> Dict[str, float]:
    """Obtener resumen de gastos por categoría."""
    try:
        with get_db_session() as session:
            expenses = session.query(Expense).all()
            
        summary = {}
        for expense in expenses:
            category = expense.category
            if category in summary:
                summary[category] += expense.amount
            else:
                summary[category] = expense.amount
                
        return summary
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}")
        return {}

# ──────────────────────── FUNCIONES DE UTILIDAD ────────────────────────────

def reset_database() -> None:
    """Reiniciar la base de datos (solo para testing)."""
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Base de datos reiniciada")
        
    except Exception as e:
        logger.error(f"Error reiniciando base de datos: {e}")
        raise

def check_database_health() -> bool:
    """Verificar que la base de datos esté funcionando."""
    try:
        with get_db_session() as session:
            # Consulta simple para verificar conectividad
            session.query(Budget).first()
        return True
        
    except Exception as e:
        logger.error(f"Error de salud de la base de datos: {e}")
        return False

if __name__ == "__main__":
    # Test básico
    try:
        init_db()
        if check_database_health():
            print("✅ Base de datos funcionando correctamente")
            
            # Mostrar estadísticas
            with get_db_session() as session:
                expense_count = session.query(Expense).count()
                budget_count = session.query(Budget).count()
                print(f"📊 Gastos: {expense_count}, Presupuestos: {budget_count}")
        else:
            print("❌ Error en la base de datos")
            
    except Exception as e:
        print(f"❌ Error: {e}")