import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Añadir el directorio raíz al path para importar modelos
sys.path.append(os.getcwd())

from backend.db.models import RegistroSorteo, WhatsAppSession
from backend.db.database import SQLALCHEMY_DATABASE_URL

def delete_user_data(cedula: str):
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print(f"--- Iniciando eliminación de datos para la cédula: {cedula} ---")
        
        # 1. Borrar registros de sorteo
        registros_borrados = db.query(RegistroSorteo).filter(RegistroSorteo.cedula == cedula).delete()
        print(f"✅ Se eliminaron {registros_borrados} registros de sorteo.")
        
        # 2. Borrar sesión de WhatsApp (para que el flujo reinicie desde cero si quieres)
        sesiones_borradas = db.query(WhatsAppSession).filter(WhatsAppSession.cedula == cedula).delete()
        print(f"✅ Se eliminaron {sesiones_borradas} sesiones de WhatsApp activas.")
        
        db.commit()
        print(f"\n--- Limpieza completada con éxito para {cedula} ---")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante la eliminación: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    CEDULA_A_BORRAR = "1113783425"
    delete_user_data(CEDULA_A_BORRAR)
