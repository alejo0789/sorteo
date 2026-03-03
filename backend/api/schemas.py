from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

# Sorteo Config Schemas
class SorteoConfigBase(BaseModel):
    nombre_sorteo: str
    fecha_inicio: date
    fecha_fin: date
    activo: bool = True

class SorteoConfigCreate(SorteoConfigBase):
    pass

class SorteoConfigUpdate(BaseModel):
    nombre_sorteo: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    activo: Optional[bool] = None

class SorteoConfig(SorteoConfigBase):
    id: int
    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    cedula: str
    nombre_completo: str
    telefono: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    fecha_registro: datetime
    class Config:
        from_attributes = True

# Registration Schemas
class RegistroCreate(BaseModel):
    cedula: str
    nombre_completo: Optional[str] = None  # Optional if user already exists
    telefono: Optional[str] = None          # Optional if user already exists
    sorteo_id: int
    numero_registro: str
    comprobante_url: str                    # Mandatory: photo is required

class Registro(BaseModel):
    id: int
    cedula: str
    sorteo_id: int
    numero_registro: str
    comprobante_url: Optional[str] = None
    fecha_creacion: datetime
    class Config:
        from_attributes = True

class RegistroResponse(Registro):
    total_tickets: int  # Total tickets registered by this cedula in the sorteo

# Dashboard Schemas
class DashboardStats(BaseModel):
    total_usuarios: int
    total_registros: int

class UserTableItem(BaseModel):
    cedula: str
    nombre_completo: str
    telefono: Optional[str] = None
    count_sorteos: int
    count_receipts: int
    comprobante_url: Optional[str] = None
    fecha_ultimo_registro: Optional[datetime]

class ReceiptItem(BaseModel):
    numero_registro: str
    comprobante_url: Optional[str]
    fecha_creacion: datetime
    nombre_sorteo: str
