from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "usuarios"
    
    cedula = Column(String, primary_key=True, index=True)
    nombre_completo = Column(String, nullable=False)
    telefono = Column(String, nullable=True)  # Optional for existing users migrated from old schema
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)
    
    registros = relationship("RegistroSorteo", back_populates="usuario")

class SorteoConfig(Base):
    __tablename__ = "sorteos_config"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre_sorteo = Column(String, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    activo = Column(Boolean, default=True)
    
    registros = relationship("RegistroSorteo", back_populates="sorteo_info")

class RegistroSorteo(Base):
    __tablename__ = "registros_sorteo"
    
    id = Column(Integer, primary_key=True, index=True)
    cedula = Column(String, ForeignKey("usuarios.cedula"), nullable=False)
    sorteo_id = Column(Integer, ForeignKey("sorteos_config.id"), nullable=False)
    numero_registro = Column(String, nullable=False)
    comprobante_url = Column(String, nullable=True) # URL o path de la imagen del comprobante
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)
    
    usuario = relationship("User", back_populates="registros")
    sorteo_info = relationship("SorteoConfig", back_populates="registros")
