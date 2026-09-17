from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

# 1. LA NUEVA BASE DE DATOS INMORTAL (PostgreSQL)
SQLALCHEMY_DATABASE_URL = "postgresql://bd_consultorio_user:KnDYO5xF81u9dT9tY4hiS1VXb2TUQTB6@dpg-dam58nu7bikc738ccdpg-a.oregon-postgres.render.com/bd_consultorio"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# MODELOS DE BASE DE DATOS (FASE 1, 2 y 3)
# ==========================================
class Paciente(Base):
    __tablename__ = "pacientes"
    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String, index=True)
    telefono = Column(String)

class Turno(Base):
    __tablename__ = "turnos"
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer)
    fecha_hora = Column(String)
    estado = Column(String)
    tratamiento = Column(String)

class Servicio(Base):
    __tablename__ = "servicios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    precio_sugerido = Column(Integer)
    costo_real = Column(Integer, default=0) # NUEVO FASE 3: Para calcular la Ganancia Neta

class Pago(Base):
    __tablename__ = "pagos"
    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer)
    monto = Column(Integer)
    metodo_pago = Column(String)

class Inventario(Base): # NUEVA TABLA FASE 3: Control de Materiales
    __tablename__ = "inventario"
    id = Column(Integer, primary_key=True, index=True)
    nombre_material = Column(String)
    cantidad = Column(Integer)
    costo_unitario = Column(Integer)

# Crear las tablas automáticamente
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# SCHEMAS (Validadores de datos)
# ==========================================
class PacienteCreate(BaseModel):
    nombre_completo: str
    telefono: str

class TurnoCreate(BaseModel):
    paciente_id: int
    fecha_hora: str
    estado: str
    tratamiento: str

class ServicioCreate(BaseModel):
    nombre: str
    precio_sugerido: int
    costo_real: Optional[int] = 0

class PagoCreate(BaseModel):
    turno_id: int
    monto: int
    metodo_pago: str

class InventarioCreate(BaseModel):
    nombre_material: str
    cantidad: int
    costo_unitario: int

# ==========================================
# RUTAS DE LA API (Endpoints)
# ==========================================
@app.get("/")
def read_root():
    return {"mensaje": "API Consultorio ERP funcionando en la nube Inmortal"}

# --- PACIENTES ---
@app.post("/pacientes/")
def crear_paciente(paciente: PacienteCreate, db: Session = Depends(get_db)):
    db_pac = Paciente(**paciente.dict())
    db.add(db_pac)
    db.commit()
    db.refresh(db_pac)
    return db_pac

@app.get("/pacientes/")
def leer_pacientes(db: Session = Depends(get_db)):
    return db.query(Paciente).all()

# --- TURNOS ---
@app.post("/turnos/")
def crear_turno(turno: TurnoCreate, db: Session = Depends(get_db)):
    db_turno = Turno(**turno.dict())
    db.add(db_turno)
    db.commit()
    db.refresh(db_turno)
    return db_turno

@app.get("/turnos/")
def leer_turnos(db: Session = Depends(get_db)):
    return db.query(Turno).all()

# --- SERVICIOS ---
@app.post("/servicios/")
def crear_servicio(servicio: ServicioCreate, db: Session = Depends(get_db)):
    db_serv = Servicio(**servicio.dict())
    db.add(db_serv)
    db.commit()
    db.refresh(db_serv)
    return db_serv

@app.get("/servicios/")
def leer_servicios(db: Session = Depends(get_db)):
    return db.query(Servicio).all()

# --- PAGOS ---
@app.post("/pagos/")
def crear_pago(pago: PagoCreate, db: Session = Depends(get_db)):
    db_pago = Pago(**pago.dict())
    db.add(db_pago)
    db.commit()
    db.refresh(db_pago)
    return db_pago

@app.get("/pagos/")
def leer_pagos(db: Session = Depends(get_db)):
    return db.query(Pago).all()

# --- INVENTARIO (FASE 3) ---
@app.post("/inventario/")
def crear_material(item: InventarioCreate, db: Session = Depends(get_db)):
    db_item = Inventario(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/inventario/")
def leer_inventario(db: Session = Depends(get_db)):
    return db.query(Inventario).all()