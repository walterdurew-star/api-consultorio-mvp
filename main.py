from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

# CONEXIÓN A POSTGRESQL (Tu Base de Datos Inmortal)
SQLALCHEMY_DATABASE_URL = "postgresql://bd_consultorio_user:KnDYO5xF81u9dT9tY4hiS1VXb2TUQTB6@dpg-dam58nu7bikc738ccdpg-a.oregon-postgres.render.com/bd_consultorio"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# MODELOS DE BASE DE DATOS
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
    costo_real = Column(Integer, default=0)

class Pago(Base):
    __tablename__ = "pagos"
    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer)
    monto = Column(Integer)
    metodo_pago = Column(String)

class Inventario(Base):
    __tablename__ = "inventario"
    id = Column(Integer, primary_key=True, index=True)
    nombre_material = Column(String)
    cantidad = Column(Integer)
    costo_unitario = Column(Integer)

# --- NUEVO FASE 5: HISTORIAL CLÍNICO ---
class HistorialClinico(Base):
    __tablename__ = "historial_clinico"
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, index=True)
    fecha = Column(String)
    pieza_dental = Column(String)
    tratamiento = Column(String)
    observaciones = Column(Text)

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
# SCHEMAS (Validadores)
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

class InventarioCreate(BaseModel):
    nombre_material: str
    cantidad: int
    costo_unitario: int

class PagoCreate(BaseModel):
    turno_id: int
    monto: int
    metodo_pago: str

class ServicioUpdate(BaseModel):
    nombre: Optional[str] = None
    precio_sugerido: Optional[int] = None
    costo_real: Optional[int] = None

class InventarioUpdate(BaseModel):
    nombre_material: Optional[str] = None
    cantidad: Optional[int] = None
    costo_unitario: Optional[int] = None

# --- NUEVO FASE 5: Schema Historial ---
class HistorialCreate(BaseModel):
    paciente_id: int
    fecha: str
    pieza_dental: str
    tratamiento: str
    observaciones: str

# ==========================================
# RUTAS DE LA API (Endpoints)
# ==========================================
@app.get("/")
def read_root():
    return {"mensaje": "API Consultorio ERP (Fase 5: Historial Clínico)"}

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

@app.put("/servicios/{servicio_id}")
def editar_servicio(servicio_id: int, serv_data: ServicioUpdate, db: Session = Depends(get_db)):
    db_serv = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if serv_data.nombre is not None: db_serv.nombre = serv_data.nombre
    if serv_data.precio_sugerido is not None: db_serv.precio_sugerido = serv_data.precio_sugerido
    if serv_data.costo_real is not None: db_serv.costo_real = serv_data.costo_real
    db.commit()
    db.refresh(db_serv)
    return db_serv

@app.delete("/servicios/{servicio_id}")
def borrar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    db_serv = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if db_serv:
        db.delete(db_serv)
        db.commit()
    return {"mensaje": "Eliminado"}

# --- INVENTARIO ---
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

@app.put("/inventario/{item_id}")
def editar_inventario(item_id: int, item_data: InventarioUpdate, db: Session = Depends(get_db)):
    db_item = db.query(Inventario).filter(Inventario.id == item_id).first()
    if item_data.nombre_material is not None: db_item.nombre_material = item_data.nombre_material
    if item_data.cantidad is not None: db_item.cantidad = item_data.cantidad
    if item_data.costo_unitario is not None: db_item.costo_unitario = item_data.costo_unitario
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/inventario/{item_id}")
def borrar_inventario(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Inventario).filter(Inventario.id == item_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
    return {"mensaje": "Eliminado"}

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

@app.delete("/turnos/{turno_id}")
def borrar_turno(turno_id: int, db: Session = Depends(get_db)):
    db_turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if db_turno:
        db.delete(db_turno)
        db.commit()
    return {"mensaje": "Turno cancelado"}

# --- PACIENTES Y PAGOS ---
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

# --- NUEVO FASE 5: RUTAS HISTORIAL CLÍNICO ---
@app.post("/historial/")
def crear_historial(ficha: HistorialCreate, db: Session = Depends(get_db)):
    db_ficha = HistorialClinico(**ficha.dict())
    db.add(db_ficha)
    db.commit()
    db.refresh(db_ficha)
    return db_ficha

@app.get("/historial/")
def leer_historiales(db: Session = Depends(get_db)):
    return db.query(HistorialClinico).all()

@app.delete("/historial/{ficha_id}")
def borrar_historial(ficha_id: int, db: Session = Depends(get_db)):
    db_ficha = db.query(HistorialClinico).filter(HistorialClinico.id == ficha_id).first()
    if db_ficha:
        db.delete(db_ficha)
        db.commit()
    return {"mensaje": "Eliminado"}