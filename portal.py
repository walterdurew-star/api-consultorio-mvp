import streamlit as st
import requests
import urllib.parse
import time  # <-- NUEVA HERRAMIENTA PARA EL AUTO-REFRESCO

# --- CONEXIÓN A LA NUBE ---
API_URL = "https://api-consultorio-mvp.onrender.com"

st.set_page_config(page_title="Portal Odontológico", page_icon="🦷", layout="wide")

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
            
            nombre = st.text_input("Tu Nombre y Apellido (🎤 Puedes usar el dictado de tu teclado)")
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
# 2. PANEL DEL DOCTOR (PRIVADO)
# ==========================================
elif menu == "Panel del Doctor 👨‍⚕️":
    st.title("👨‍⚕️ Panel de Administración")
    
    password = st.text_input("Ingresa la clave de acceso:", type="password")
    
    if password == "admin123":
        st.success("¡Bienvenido al sistema, Doctor!")
        
        tab1, tab2, tab3 = st.tabs(["📅 Agenda", "⚙️ Gestor Precios", "💰 Finanzas (Cobros)"])
        
        # --- PESTAÑA 1: AGENDA ---
        with tab1:
            st.subheader("Turnos Registrados")
            try:
                turnos = requests.get(f"{API_URL}/turnos/").json()
                pacientes = requests.get(f"{API_URL}/pacientes/").json()
                dic_pacientes = {p["id"]: p for p in pacientes}
                
                if turnos:
                    for turno in turnos:
                        paciente = dic_pacientes.get(turno["paciente_id"], {})
                        with st.expander(f"🦷 {paciente.get('nombre_completo', 'N/A')} - {turno['fecha_hora'][:10]}"):
                            st.write(f"**Tratamiento:** {turno['tratamiento']}")
                            st.write(f"**Estado del Turno:** {turno['estado']}")
                            if paciente.get("telefono"):
                                st.link_button("📲 Enviar Recordatorio WhatsApp", f"https://wa.me/{paciente['telefono']}?text=Hola, recordatorio de tu turno...")
                else:
                    st.info("No hay turnos.")
            except:
                st.error("Error cargando agenda.")

        # --- PESTAÑA 2: CARGAR PRECIOS ---
        with tab2:
            st.subheader("Agregar Servicio al Catálogo")
            with st.form("form_servicios"):
                nuevo_nombre = st.text_input("Nombre del Servicio")
                precio_texto = st.text_input("Precio (₲) - Ej: 150.000", value="")
                
                if st.form_submit_button("Guardar"):
                    precio_limpio = ''.join(filter(str.isdigit, precio_texto))
                    nuevo_precio = int(precio_limpio) if precio_limpio else 0
                    
                    if nuevo_nombre and nuevo_precio > 0:
                        requests.post(f"{API_URL}/servicios/", json={"nombre": nuevo_nombre, "precio_sugerido": nuevo_precio})
                        st.success("Servicio agregado exitosamente.")
                        time.sleep(1) # Pausa de 1 segundo
                        st.rerun() # Auto-recarga para actualizar catálogo
                    else:
                        st.warning("Por favor ingresa un nombre y un precio válido.")

        # --- PESTAÑA 3: FINANZAS Y COBROS ---
        with tab3:
            st.subheader("Registrar un Cobro")
            try:
                turnos_finanzas = requests.get(f"{API_URL}/turnos/").json()
                pagos_hechos = requests.get(f"{API_URL}/pagos/").json()
                pacientes_finanzas = requests.get(f"{API_URL}/pacientes/").json()
                
                # Diccionario para encontrar rápido el nombre del paciente
                dic_pacientes_fin = {p["id"]: p["nombre_completo"] for p in pacientes_finanzas}
                
                res_serv_admin = requests.get(f"{API_URL}/servicios/").json()
                catalogo_precios = {s["nombre"]: s["precio_sugerido"] for s in res_serv_admin}
                
                total_recaudado = sum(p["monto"] for p in pagos_hechos)
                total_str = f"₲ {int(total_recaudado):,}".replace(",", ".")
                st.metric(label="Ingresos Totales Registrados", value=total_str)
                st.write("---")
                
                if turnos_finanzas:
                    # AQUÍ ESTÁ LA MEJORA DEL NOMBRE DEL PACIENTE
                    opciones_turno = {}
                    for t in turnos_finanzas:
                        nombre_paciente = dic_pacientes_fin.get(t["paciente_id"], "Paciente Desconocido")
                        # Nuevo formato: Turno #1 - Walter - profilaxis
                        texto_visible = f"Turno #{t['id']} - {nombre_paciente} - {t['tratamiento']}"
                        opciones_turno[texto_visible] = t

                    turno_seleccionado = st.selectbox("Seleccionar Turno a Cobrar:", list(opciones_turno.keys()))
                    turno_datos = opciones_turno[turno_seleccionado]
                    
                    tratamientos_del_turno = turno_datos['tratamiento'].split(", ")
                    presupuesto_original = sum([catalogo_precios.get(t, 0) for t in tratamientos_del_turno])
                    
                    presupuesto_str = f"₲ {int(presupuesto_original):,}".replace(",", ".")
                    st.write(f"📝 **Presupuesto original sugerido:** {presupuesto_str}")
                    
                    valor_por_defecto = f"{int(presupuesto_original):,}".replace(",", ".")
                    monto_texto = st.text_input(
                        "Monto final a cobrar (puedes modificarlo con puntos):", 
                        value=valor_por_defecto
                    )
                    
                    monto_limpio = ''.join(filter(str.isdigit, monto_texto))
                    monto_cobrar = int(monto_limpio) if monto_limpio else 0
                    
                    monto_formateado = f"₲ {monto_cobrar:,}".replace(",", ".")
                    st.info(f"🧾 Se registrará un cobro por: **{monto_formateado}**")
                    
                    metodo = st.selectbox("Método de Pago:", ["Efectivo", "Transferencia", "Tarjeta"])
                    
                    if st.button("Registrar Cobro"):
                        datos_pago = {
                            "turno_id": turno_datos['id'],
                            "monto": monto_cobrar,
                            "metodo_pago": metodo
                        }
                        res_pago = requests.post(f"{API_URL}/pagos/", json=datos_pago)
                        if res_pago.status_code == 200:
                            st.success("¡Cobro registrado! Actualizando ingresos...")
                            time.sleep(1.5) # Espera 1.5 segundos para que leas el cartel verde
                            st.rerun() # ¡MAGIA! Recarga la página y actualiza el contador al instante
            except:
                st.error("Error al cargar datos financieros.")