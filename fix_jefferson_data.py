import os
import sys
from sqlalchemy.orm import sessionmaker

# 1. Asegurar que Python encuentre el paquete 'backend'
sys.path.append(os.getcwd())

from backend.db.session import SessionLocal
from backend.db.models import RegistroSorteo, WhatsAppSession, User

def fix_data():
    db = SessionLocal()
    try:
        incorrect_cedula = "hola"
        correct_cedula = "94450968"
        
        print(f"--- Iniciando correccion de datos para Jefferson Correa ---")
        
        # 1. Buscar si existe el usuario "hola"
        user_hola = db.query(User).filter(User.cedula == incorrect_cedula).first()
        
        if user_hola:
            print(f"OK: Se encontro el usuario con cedula 'hola': {user_hola.nombre_completo}")
            
            # Actualizar registros de sorteo
            registros = db.query(RegistroSorteo).filter(RegistroSorteo.cedula == incorrect_cedula).all()
            for reg in registros:
                reg.cedula = correct_cedula
                print(f"  - Ticket {reg.numero_registro} movido a la cedula correcta.")
            
            # Actualizar sesiones de WhatsApp si existen
            sesiones = db.query(WhatsAppSession).filter(WhatsAppSession.cedula == incorrect_cedula).all()
            for ses in sesiones:
                ses.cedula = correct_cedula
                print(f"  - Sesion de WhatsApp actualizada.")

            # Eliminar el usuario "hola" ya que sus registros fueron movidos
            db.delete(user_hola)
            print(f"OK: Usuario corrupto ('hola') eliminado.")
            
            db.commit()
            print(f"\n--- Correccion completada con exito ---")
        else:
            print(f"WARN: No se encontro ningun usuario con cedula 'hola'.")
            
    except Exception as e:
        db.rollback()
        print(f"ERROR: Error durante la correccion: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_data()
