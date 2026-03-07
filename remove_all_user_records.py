import os
import sys
from sqlalchemy.orm import sessionmaker

# 1. Asegurar que Python encuentre el paquete 'backend'
sys.path.append(os.getcwd())

from backend.db.session import engine, SessionLocal
from backend.db.models import RegistroSorteo, WhatsAppSession, User

def delete_user_data(cedula: str):
    db = SessionLocal()
    
    try:
        print(f"--- Iniciando eliminación total de registros para la cédula: {cedula} ---")
        
        # 1. Borrar registros de sorteo asociados a la cédula
        registros_borrados = db.query(RegistroSorteo).filter(RegistroSorteo.cedula == cedula).delete()
        print(f"✅ Se eliminaron {registros_borrados} tickets registrados.")
        
        # 2. Borrar sesión de WhatsApp activa para este usuario
        # (Esto reinicia el flujo del bot si el usuario vuelve a escribir)
        sesiones_borradas = db.query(WhatsAppSession).filter(WhatsAppSession.cedula == cedula).delete()
        print(f"✅ Se eliminaron {sesiones_borradas} sesiones de WhatsApp.")
        
        # 3. Opcional: Borrar al usuario de la tabla de clientes (Si prefieres dejarlo como nuevo)
        # Si prefieres conservar al usuario y solo borrar sus tickets, comenta la siguiente línea:
        usuarios_borrados = db.query(User).filter(User.cedula == cedula).delete()
        print(f"✅ Se eliminó al usuario de la tabla de clientes.")

        db.commit()
        print(f"\n--- Limpieza completada con éxito para {cedula} ---")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante la eliminación: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Cédula de prueba enviada por el usuario
    CEDULA_TARGET = "1113783425"
    delete_user_data(CEDULA_TARGET)
