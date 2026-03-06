from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import datetime
import os
import uuid

from backend.cloudinary_service import upload_image_to_cloudinary

from backend.db.session import get_db, engine
from backend.db import models
from backend.api import schemas

# Create tables
models.Base.metadata.create_all(bind=engine)

# Run migration to add new columns if they don't exist yet (safe for SQLite)
from sqlalchemy import text, inspect

def run_migrations():
    with engine.connect() as conn:
        inspector = inspect(engine)
        # Check for our prefixed table
        t_name = "marketing_clientes_sorteos"
        if t_name in inspector.get_table_names():
            existing_cols = [c["name"] for c in inspector.get_columns(t_name)]
            if "telefono" not in existing_cols:
                conn.execute(text(f"ALTER TABLE {t_name} ADD COLUMN telefono VARCHAR(255)"))
                conn.commit()

try:
    run_migrations()
except Exception as e:
    print(f"[Migration] Skipped or error: {e}")

app = FastAPI(title="Acertemos Sorteos API")

# Ensure assets directory exists and mount it
os.makedirs("assets/receipts", exist_ok=True)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/acertemos_premium_ui", StaticFiles(directory="acertemos_premium_ui"), name="ui")

# Serve index.html at root and /index.html
@app.get("/")
@app.get("/index.html")
def read_index():
    return FileResponse("index.html")

# Serve dashboard.html
@app.get("/dashboard")
@app.get("/dashboard.html")
def read_dashboard():
    return FileResponse("dashboard.html")

@app.get("/terminos")
@app.get("/terminos.html")
def read_terminos():
    return FileResponse("terminos.html")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/check-user/{cedula}", response_model=Optional[schemas.UserBase])
def check_user(cedula: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.cedula == cedula).first()
    if user:
        return user
    return None

@app.post("/upload-receipt")
async def upload_receipt(file: UploadFile = File(...), sorteo_nombre: Optional[str] = Query(None)):
    # Generar nombre único para el archivo
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"comprobante_{uuid.uuid4()}{file_extension}"

    # Leer el contenido del archivo en memoria
    file_bytes = await file.read()

    # Definir la carpeta basado en el sorteo (o 'general' si no viene ninguno)
    folder_name = f"sorteos/{sorteo_nombre.replace(' ', '_')}" if sorteo_nombre else "sorteos/general"

    try:
        # Subir a Cloudinary con el folder dinámico
        public_url = upload_image_to_cloudinary(file_bytes, filename, folder=folder_name)
        return {"url": public_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo imagen a Cloudinary: {str(e)}")

@app.post("/register", response_model=schemas.RegistroResponse)
def register_to_sorteo(data: schemas.RegistroCreate, db: Session = Depends(get_db)):
    # 1. Validate that comprobante is present
    if not data.comprobante_url or not data.comprobante_url.strip():
        raise HTTPException(status_code=400, detail="La foto del ticket es obligatoria para el registro.")

    # 2. Handle User
    user = db.query(models.User).filter(models.User.cedula == data.cedula).first()
    if not user:
        if not data.nombre_completo:
            raise HTTPException(status_code=400, detail="El nombre completo es obligatorio para nuevos usuarios.")
        if not data.telefono:
            raise HTTPException(status_code=400, detail="El teléfono de contacto es obligatorio para nuevos usuarios.")
        user = models.User(
            cedula=data.cedula,
            nombre_completo=data.nombre_completo,
            telefono=data.telefono
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Check for unique ticket number per sorteo
    existing_reg = db.query(models.RegistroSorteo).filter(
        models.RegistroSorteo.sorteo_id == data.sorteo_id,
        models.RegistroSorteo.numero_registro == data.numero_registro
    ).first()
    
    if existing_reg:
        raise HTTPException(
            status_code=400, 
            detail=f"El ticket '{data.numero_registro}' ya ha sido registrado anteriormente."
        )

    # 4. Create the registration
    new_reg = models.RegistroSorteo(
        cedula=data.cedula,
        sorteo_id=data.sorteo_id,
        numero_registro=data.numero_registro,
        comprobante_url=data.comprobante_url
    )
    db.add(new_reg)
    db.commit()
    db.refresh(new_reg)

    # 5. Count total tickets by this cedula in this sorteo
    total_tickets = db.query(func.count(models.RegistroSorteo.id)).filter(
        models.RegistroSorteo.cedula == data.cedula,
        models.RegistroSorteo.sorteo_id == data.sorteo_id
    ).scalar()

    # 6. Calculate remaining tickets for the goal (e.g., 10 for the motorcycle)
    MOTO_GOAL = 10
    tickets_restantes = max(0, MOTO_GOAL - total_tickets)

    return schemas.RegistroResponse(
        id=new_reg.id,
        cedula=new_reg.cedula,
        sorteo_id=new_reg.sorteo_id,
        numero_registro=new_reg.numero_registro,
        comprobante_url=new_reg.comprobante_url,
        fecha_creacion=new_reg.fecha_creacion,
        total_tickets=total_tickets,
        tickets_restantes=tickets_restantes
    )

@app.get("/whatsapp/check-user/{telefono}", response_model=schemas.WhatsAppUserCheck)
def check_user_by_phone(telefono: str, db: Session = Depends(get_db)):
    # Sanitize phone
    clean_tel = telefono.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").strip()
    
    # Search for user by phone
    # Note: Search using LIKE if it's stored differently or just exact match
    user = db.query(models.User).filter(models.User.telefono == clean_tel).first()
    
    if user:
        return schemas.WhatsAppUserCheck(
            exists=True,
            cedula=user.cedula,
            nombre=user.nombre_completo,
            telefono=user.telefono
        )
    return schemas.WhatsAppUserCheck(exists=False)

@app.get("/whatsapp/check-ticket/{numero_sorteo}", response_model=schemas.WhatsAppTicketCheck)
def check_ticket_registration(numero_sorteo: str, db: Session = Depends(get_db)):
    # 1. Find the current active sorteo
    from backend.db.models import get_colombia_time
    today = get_colombia_time().date()
    active_sorteo = db.query(models.SorteoConfig).filter(
        models.SorteoConfig.activo == True,
        models.SorteoConfig.fecha_inicio <= today,
        models.SorteoConfig.fecha_fin >= today
    ).first()

    if not active_sorteo:
        return schemas.WhatsAppTicketCheck(registered=False, mensaje="No hay sorteos activos.")

    # 2. Check if ticket exists in active sorteo
    existing_reg = db.query(models.RegistroSorteo).filter(
        models.RegistroSorteo.sorteo_id == active_sorteo.id,
        models.RegistroSorteo.numero_registro == numero_sorteo
    ).first()

    if existing_reg:
        return schemas.WhatsAppTicketCheck(
            registered=True, 
            mensaje=f"El ticket '{numero_sorteo}' ya ha sido registrado anteriormente."
        )
    
    return schemas.WhatsAppTicketCheck(registered=False, mensaje="Ticket disponible para registro.")

@app.post("/whatsapp/register", response_model=schemas.WhatsAppRegistroResponse)
def register_from_whatsapp(data: schemas.WhatsAppRegistroCreate, db: Session = Depends(get_db)):
    # Sanitize data
    data.cedula = data.cedula.replace(".", "").replace(",", "").replace(" ", "").strip()
    data.telefono = data.telefono.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").strip()
    
    # 1. Direct registration from WhatsApp data
    # Find the current active sorteo automatically
    from backend.db.models import get_colombia_time
    today = get_colombia_time().date()
    active_sorteo = db.query(models.SorteoConfig).filter(
        models.SorteoConfig.activo == True,
        models.SorteoConfig.fecha_inicio <= today,
        models.SorteoConfig.fecha_fin >= today
    ).first()

    if not active_sorteo:
        raise HTTPException(status_code=400, detail="No hay sorteos activos en este momento.")

    # 2. Reuse logic to handle user and registration
    # Check User
    user = db.query(models.User).filter(models.User.cedula == data.cedula).first()
    if not user:
        user = models.User(
            cedula=data.cedula,
            nombre_completo=data.nombre,
            telefono=data.telefono
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update name or phone if provided and different
        user.nombre_completo = data.nombre
        user.telefono = data.telefono
        db.commit()

    # Check for unique ticket
    existing_reg = db.query(models.RegistroSorteo).filter(
        models.RegistroSorteo.sorteo_id == active_sorteo.id,
        models.RegistroSorteo.numero_registro == data.numero_sorteo
    ).first()

    if existing_reg:
        # Instead of error, maybe just return current status but indicating it was already there
        total_tickets = db.query(func.count(models.RegistroSorteo.id)).filter(
            models.RegistroSorteo.cedula == data.cedula,
            models.RegistroSorteo.sorteo_id == active_sorteo.id
        ).scalar()
        MOTO_GOAL = 10
        tickets_restantes = max(0, MOTO_GOAL - total_tickets)
        return schemas.WhatsAppRegistroResponse(
            status="already_registered",
            mensaje=f"El ticket {data.numero_sorteo} ya estaba registrado.",
            total_tickets=total_tickets,
            tickets_restantes=tickets_restantes,
            cedula=user.cedula,
            nombre=user.nombre_completo
        )

    # Create registration
    new_reg = models.RegistroSorteo(
        cedula=data.cedula,
        sorteo_id=active_sorteo.id,
        numero_registro=data.numero_sorteo,
        comprobante_url=data.url_imagen
    )
    db.add(new_reg)
    db.commit()

    # Count total
    total_tickets = db.query(func.count(models.RegistroSorteo.id)).filter(
        models.RegistroSorteo.cedula == data.cedula,
        models.RegistroSorteo.sorteo_id == active_sorteo.id
    ).scalar()

    MOTO_GOAL = 10
    tickets_restantes = max(0, MOTO_GOAL - total_tickets)
    
    msg = f"¡Registro exitoso! Llevas {total_tickets} ticket(s)."
    if tickets_restantes > 0:
        msg += f" Te faltan {tickets_restantes} para participar por la moto."
    else:
        msg += " ¡Ya estás participando por la moto! 🏍️"

    return schemas.WhatsAppRegistroResponse(
        status="success",
        mensaje=msg,
        total_tickets=total_tickets,
        tickets_restantes=tickets_restantes,
        cedula=user.cedula,
        nombre=user.nombre_completo
    )

@app.get("/sorteos", response_model=List[schemas.SorteoConfig])
def get_sorteos(active_only: bool = True, db: Session = Depends(get_db)):
    query = db.query(models.SorteoConfig)
    if active_only:
        # Usar hora de Colombia para determinar qué sorteos están activos
        from backend.db.models import get_colombia_time
        today = get_colombia_time().date()
        query = query.filter(models.SorteoConfig.activo == True, 
                             models.SorteoConfig.fecha_inicio <= today,
                             models.SorteoConfig.fecha_fin >= today)
    return query.all()

@app.post("/sorteos", response_model=schemas.SorteoConfig)
def create_sorteo(sorteo: schemas.SorteoConfigCreate, db: Session = Depends(get_db)):
    db_sorteo = models.SorteoConfig(**sorteo.dict())
    db.add(db_sorteo)
    db.commit()
    db.refresh(db_sorteo)
    return db_sorteo

@app.put("/sorteos/{sorteo_id}", response_model=schemas.SorteoConfig)
def update_sorteo(sorteo_id: int, sorteo_update: schemas.SorteoConfigUpdate, db: Session = Depends(get_db)):
    db_sorteo = db.query(models.SorteoConfig).filter(models.SorteoConfig.id == sorteo_id).first()
    if not db_sorteo:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")
    
    update_data = sorteo_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_sorteo, key, value)
    
    db.commit()
    db.refresh(db_sorteo)
    return db_sorteo

@app.get("/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(sorteo_id: Optional[int] = None, db: Session = Depends(get_db)):
    user_count = db.query(func.count(models.User.cedula)).scalar()
    
    reg_query = db.query(func.count(models.RegistroSorteo.id))
    if sorteo_id:
        reg_query = reg_query.filter(models.RegistroSorteo.sorteo_id == sorteo_id)
    reg_count = reg_query.scalar()
    
    return {"total_usuarios": user_count, "total_registros": reg_count}

@app.get("/dashboard/users", response_model=List[schemas.UserTableItem])
def get_dashboard_users(sorteo_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(
        models.User.cedula,
        models.User.nombre_completo,
        models.User.telefono,
        func.count(models.RegistroSorteo.id).label("count_sorteos"),
        func.count(models.RegistroSorteo.comprobante_url).label("count_receipts"),
        func.max(models.RegistroSorteo.fecha_creacion).label("fecha_ultimo_registro"),
        func.max(models.RegistroSorteo.comprobante_url).label("comprobante_url")
    ).outerjoin(models.RegistroSorteo)
    
    if sorteo_id:
        query = query.filter(models.RegistroSorteo.sorteo_id == sorteo_id)
        
    results = query.group_by(models.User.cedula).all()
    
    return [
        schemas.UserTableItem(
            cedula=r.cedula,
            nombre_completo=r.nombre_completo,
            telefono=r.telefono,
            count_sorteos=r.count_sorteos,
            count_receipts=r.count_receipts,
            comprobante_url=r.comprobante_url,
            fecha_ultimo_registro=r.fecha_ultimo_registro
        ) for r in results
    ]

@app.get("/dashboard/user-receipts/{cedula}", response_model=List[schemas.ReceiptItem])
def get_user_receipts(cedula: str, sorteo_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(
        models.RegistroSorteo.numero_registro,
        models.RegistroSorteo.comprobante_url,
        models.RegistroSorteo.fecha_creacion,
        models.SorteoConfig.nombre_sorteo
    ).join(models.SorteoConfig).filter(models.RegistroSorteo.cedula == cedula)
    
    if sorteo_id:
        query = query.filter(models.RegistroSorteo.sorteo_id == sorteo_id)
        
    results = query.order_by(models.RegistroSorteo.fecha_creacion.desc()).all()
    
    return [
        schemas.ReceiptItem(
            numero_registro=r.numero_registro,
            comprobante_url=r.comprobante_url,
            fecha_creacion=r.fecha_creacion,
            nombre_sorteo=r.nombre_sorteo
        ) for r in results
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
