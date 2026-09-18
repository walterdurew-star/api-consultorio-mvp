import streamlit as st
import requests
import urllib.parse

# --- CONEXIÓN A LA NUBE ---
API_URL = "https://api-consultorio-mvp.onrender.com"

st.set_page_config(page_title="Portal Odontológico ERP", page_icon="🦷", layout="wide")

st.sidebar.title("🦷 Menú Principal")
menu = st.sidebar.radio("Navegación:", ["Portal del Paciente", "Panel del Doctor 👨‍⚕️"])

# ==========================================
# 1. PORTAL DEL PACIENTE (PÚBLICO)
# ==========================================
if menu == "Portal del Paciente":
    st.title("🦷 Clínica Odontológica")
    st.subheader("Autogestión de Presupuestos y Turnos")

    try:
        res_serv = requests.get(f"{API_URL}/servicios/")
        catalogo = {serv["nombre"]: serv["precio_sugerido"] for serv in res_serv.json()}
    except:
        catalogo = {}

    if catalogo:
        opciones = st.multiselect("Selecciona tratamientos:", list(catalogo.keys()))

        if opciones:
            total = sum([catalogo[op] for op in opciones])
            total_formateado = f"₲ {int(total):,}".replace(",", ".")
            
            st.info(f"💰 Presupuesto estimado total: **{total_formateado}**")
            st.write("---")
            st.write("### 📅 Agendar mi Turno")
            
            nombre = st.text_input("Tu Nombre y Apellido")
            telefono = st.text_input("Tu Teléfono WhatsApp (Ej: 595981123456)") 
            
            fecha_str = str(st.date_input("¿Qué día te gustaría venir?"))
            hora = st.time_input("¿A qué hora?")
            
            if st.button("¡Confirmar mi Turno!"):
                if nombre and telefono:
                    datos_pac = {"nombre_completo": nombre, "telefono": telefono}
                    res_pac = requests.post(f"{API_URL}/pacientes/", json=datos_pac)
                    
                    if res_pac.status_code == 200:
                        paciente_id = res_pac.json()["id"]
                        fecha_hora = f"{fecha_str}T{hora.strftime('%H:%M:%S')}"
                        
                        datos_turno = {
                            "paciente_id": paciente_id, "fecha_hora": fecha_hora, 
                            "estado": "Pendiente", "tratamiento": ", ".join(opciones)
                        }
                        res_turno = requests.post(f"{API_URL}/turnos/", json=datos_turno)
                        
                        if res_turno.status_code == 200:
                            st.balloons()
                            st.success("¡Turno agendado exitosamente!")
                else:
                    st.warning("Completa nombre y teléfono.")
    else:
        st.warning("⚠️ El catálogo está vacío. El doctor debe agregar servicios.")

# ==========================================
# 2. PANEL DEL DOCTOR (PRIVADO - ERP)
# ==========================================
elif menu == "Panel del Doctor 👨‍⚕️":
    st.title("👨‍⚕️ Panel de Administración ERP")
    
    password = st.text_input("Ingresa la clave de acceso:", type="password")
    
    if password == "admin123":
        
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Agenda", "⚙️ Servicios y Costos", "💰 Finanzas", "📦 Inventario"])
        
        # --- PESTAÑA 1: AGENDA ---
        with tab1:
            st.subheader("Turnos Pendientes de Atención")
            try:
                turnos = requests.get(f"{API_URL}/turnos/").json()
                pacientes = requests.get(f"{API_URL}/pacientes/").json()
                pagos = requests.get(f"{API_URL}/pagos/").json()
                
                dic_pacientes = {p["id"]: p for p in pacientes}
                turnos_pagados_ids = {p["turno_id"] for p in pagos}
                turnos_pendientes = [t for t in turnos if t["id"] not in turnos_pagados_ids]
                
                if turnos_pendientes:
                    for turno in turnos_pendientes:
                        paciente = dic_pacientes.get(turno["paciente_id"], {})
                        with st.expander(f"🦷 {paciente.get('nombre_completo', 'N/A')} - {turno['fecha_hora'][:10]}"):
                            st.write(f"**Tratamiento:** {turno['tratamiento']}")
                            st.write(f"**Estado del Turno:** {turno['estado']}")
                            if paciente.get("telefono"):
                                st.link_button("📲 Enviar Recordatorio WhatsApp", f"https://wa.me/{paciente['telefono']}?text=Hola, recordatorio de tu turno...")
                else:
                    st.info("¡Excelente! No hay turnos pendientes.")
            except:
                st.error("Esperando conexión...")

        # --- PESTAÑA 2: CARGAR PRECIOS Y COSTOS ---
        with tab2:
            st.subheader("Agregar Servicio (Precio y Costo)")
            
            # EL SECRETO: clear_on_submit=True vacía todo al guardar
            with st.form("form_servicios", clear_on_submit=True):
                nuevo_nombre = st.text_input("Nombre del Servicio (Ej: Profilaxis)")
                
                col1, col2 = st.columns(2)
                with col1:
                    precio_texto = st.text_input("Precio a cobrar al paciente (₲)", placeholder="Ej: 150.000")
                with col2:
                    costo_texto = st.text_input("Costo interno de materiales (₲)", placeholder="Ej: 30.000")
                
                if st.form_submit_button("Guardar Servicio"):
                    p_limpio = ''.join(filter(str.isdigit, precio_texto))
                    c_limpio = ''.join(filter(str.isdigit, costo_texto))
                    
                    nuevo_precio = int(p_limpio) if p_limpio else 0
                    nuevo_costo = int(c_limpio) if c_limpio else 0
                    
                    if nuevo_nombre and nuevo_precio > 0:
                        requests.post(f"{API_URL}/servicios/", json={
                            "nombre": nuevo_nombre, 
                            "precio_sugerido": nuevo_precio,
                            "costo_real": nuevo_costo
                        })
                        st.success("Servicio guardado exitosamente.")
                        st.rerun()

            # LA MEJORA VISUAL: Ver lo que acabas de cargar con formato perfecto
            st.write("---")
            st.write("### Catálogo Actual de Servicios")
            try:
                res_serv_admin = requests.get(f"{API_URL}/servicios/").json()
                if res_serv_admin:
                    for s in reversed(res_serv_admin): # reversed para que el más nuevo salga arriba
                        precio_str = f"₲ {s['precio_sugerido']:,}".replace(",", ".")
                        costo_str = f"₲ {s['costo_real']:,}".replace(",", ".")
                        st.info(f"**{s['nombre']}** | Precio a cobrar: {precio_str} | Costo interno: {costo_str}")
                else:
                    st.write("No hay servicios cargados aún.")
            except:
                pass

        # --- PESTAÑA 3: FINANZAS E INTELIGENCIA DE NEGOCIO ---
        with tab3:
            st.subheader("Dashboard Financiero")
            try:
                pagos_hechos = requests.get(f"{API_URL}/pagos/").json()
                res_serv_admin = requests.get(f"{API_URL}/servicios/").json()
                turnos_finanzas = requests.get(f"{API_URL}/turnos/").json()
                
                dic_costos = {s["nombre"]: s.get("costo_real", 0) for s in res_serv_admin}
                dic_turnos_trat = {t["id"]: t["tratamiento"] for t in turnos_finanzas}
                
                total_recaudado = sum(p["monto"] for p in pagos_hechos)
                total_costos = 0
                for p in pagos_hechos:
                    tratamientos_str = dic_turnos_trat.get(p["turno_id"], "")
                    for trat in tratamientos_str.split(", "):
                        total_costos += dic_costos.get(trat, 0)
                
                ganancia_neta = total_recaudado - total_costos

                col1, col2, col3 = st.columns(3)
                col1.metric("Ingresos Brutos", f"₲ {int(total_recaudado):,}".replace(",", "."))
                col2.metric("Costos Operativos", f"₲ {int(total_costos):,}".replace(",", "."))
                col3.metric("Ganancia Neta Real", f"₲ {int(ganancia_neta):,}".replace(",", "."))
                
                st.write("---")
                st.subheader("Registrar un Cobro")
                
                pacientes_finanzas = requests.get(f"{API_URL}/pacientes/").json()
                dic_pacientes_fin = {p["id"]: p["nombre_completo"] for p in pacientes_finanzas}
                catalogo_precios = {s["nombre"]: s["precio_sugerido"] for s in res_serv_admin}
                
                turnos_pagados_ids = {p["turno_id"] for p in pagos_hechos}
                turnos_pendientes_fin = [t for t in turnos_finanzas if t["id"] not in turnos_pagados_ids]
                
                if turnos_pendientes_fin:
                    opciones_turno = {}
                    for t in turnos_pendientes_fin:
                        nombre_paciente = dic_pacientes_fin.get(t["paciente_id"], "Paciente Desconocido")
                        texto_visible = f"Turno #{t['id']} - {nombre_paciente} - {t['tratamiento']}"
                        opciones_turno[texto_visible] = t

                    turno_seleccionado = st.selectbox("Seleccionar Turno a Cobrar:", list(opciones_turno.keys()))
                    turno_datos = opciones_turno[turno_seleccionado]
                    
                    presupuesto_original = sum([catalogo_precios.get(t, 0) for t in turno_datos['tratamiento'].split(", ")])
                    st.write(f"📝 **Presupuesto original sugerido:** ₲ {int(presupuesto_original):,}".replace(",", "."))
                    
                    valor_defecto = f"{int(presupuesto_original):,}".replace(",", ".")
                    monto_texto = st.text_input("Monto final a cobrar (puedes poner puntos):", value=valor_defecto)
                    
                    monto_limpio = ''.join(filter(str.isdigit, monto_texto))
                    monto_cobrar = int(monto_limpio) if monto_limpio else 0
                    
                    st.info(f"🧾 Se registrará un cobro por: **₲ {monto_cobrar:,}**".replace(",", "."))
                    metodo = st.selectbox("Método de Pago:", ["Efectivo", "Transferencia", "Tarjeta"])
                    
                    if st.button("Registrar Cobro"):
                        requests.post(f"{API_URL}/pagos/", json={"turno_id": turno_datos['id'], "monto": monto_cobrar, "metodo_pago": metodo})
                        st.rerun() 
                else:
                    st.success("No hay turnos pendientes de cobro.")
            except:
                st.warning("Cargando datos financieros...")

        # --- PESTAÑA 4: INVENTARIO DE MATERIALES ---
        with tab4:
            st.subheader("📦 Gestión de Inventario")
            
            # EL SECRETO: También limpia las cajas del inventario
            with st.form("form_inventario", clear_on_submit=True):
                nombre_material = st.text_input("Nombre del Material (Ej: Resina A2)")
                col_cant, col_cost = st.columns(2)
                with col_cant:
                    cantidad = st.number_input("Cantidad en Stock", min_value=0, step=1)
                with col_cost:
                    costo_unitario_txt = st.text_input("Costo Unitario (₲) - Ej: 80.000")
                
                if st.form_submit_button("Agregar Material"):
                    costo_u_limpio = ''.join(filter(str.isdigit, costo_unitario_txt))
                    costo_final = int(costo_u_limpio) if costo_u_limpio else 0
                    
                    if nombre_material and cantidad > 0:
                        requests.post(f"{API_URL}/inventario/", json={
                            "nombre_material": nombre_material,
                            "cantidad": cantidad,
                            "costo_unitario": costo_final
                        })
                        st.success("¡Material agregado al inventario!")
                        st.rerun()

            st.write("---")
            st.write("### Stock Actual")
            try:
                inventario = requests.get(f"{API_URL}/inventario/").json()
                if inventario:
                    for item in reversed(inventario):
                        cost_str = f"₲ {item['costo_unitario']:,}".replace(",", ".")
                        st.info(f"**{item['nombre_material']}** | Stock: {item['cantidad']} unidades | Costo: {cost_str}")
                else:
                    st.write("El inventario está vacío.")
            except:
                st.write("Cargando inventario...")