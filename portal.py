import streamlit as st
import requests

# --- CONEXIÓN A LA NUBE ---
API_URL = "https://api-consultorio-mvp.onrender.com"

st.set_page_config(page_title="Portal Odontológico ERP", page_icon="🦷", layout="wide")

# Inicializar la memoria de sesión
if "vista" not in st.session_state:
    st.session_state.vista = "Inicio"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "turno_exito" not in st.session_state:
    st.session_state.turno_exito = False

# --- FUNCIÓN INTELIGENTE DE HORARIOS ---
def get_horarios_libres(fecha_str, turnos):
    horarios_posibles = [f"{h:02d}:{m:02d}" for h in range(8, 19) for m in (0, 30)]
    if isinstance(turnos, list):
        ocupados = [t["fecha_hora"].split("T")[1][:5] for t in turnos if t.get("fecha_hora", "").startswith(fecha_str)]
    else:
        ocupados = []
    return [h for h in horarios_posibles if h not in ocupados]


# ==========================================
# 0. PANTALLA DE INICIO (HOME)
# ==========================================
if st.session_state.vista == "Inicio":
    # Si viene de agendar un turno con éxito, mostramos los globos aquí
    if st.session_state.turno_exito:
        st.balloons()
        st.success("🎉 ¡Tu turno ha sido agendado exitosamente! Te esperamos en la clínica. 🦷")
        st.session_state.turno_exito = False # Apagamos el mensaje para que no salga siempre
        st.write("---")

    st.markdown("<h1 style='text-align: center;'>🦷 Bienvenido a la Clínica Odontológica</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: gray;'>¿Cómo deseas ingresar?</h3>", unsafe_allow_html=True)
    
    st.write("---")
    st.write("")
    
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    
    with col2:
        if st.button("👤 Soy Paciente\n(Agendar Turno)", use_container_width=True):
            st.session_state.vista = "Paciente"
            st.rerun()
            
    with col3:
        if st.button("👨‍⚕️ Soy Doctor\n(Ingresar al ERP)", use_container_width=True):
            st.session_state.vista = "Doctor"
            st.rerun()
            
    st.write("")
    st.markdown("<p style='text-align: center; font-size: small;'>Software Odontológico ERP - Desarrollado por Walter</p>", unsafe_allow_html=True)


# ==========================================
# 1. PORTAL DEL PACIENTE (PÚBLICO)
# ==========================================
elif st.session_state.vista == "Paciente":
    if st.button("⬅️ Volver al Inicio"):
        st.session_state.vista = "Inicio"
        st.rerun()
        
    st.title("🦷 Autogestión de Pacientes")
    st.subheader("Calcula tu presupuesto y agenda tu turno")

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
            
            try:
                turnos_actuales = requests.get(f"{API_URL}/turnos/").json()
            except:
                turnos_actuales = []
                
            horarios_libres = get_horarios_libres(fecha_str, turnos_actuales)
            
            if horarios_libres:
                hora_str = st.selectbox("¿A qué hora?", horarios_libres)
            else:
                st.error("❌ No hay horarios disponibles para este día. Por favor elige otra fecha.")
                hora_str = None
            
            if st.button("¡Confirmar mi Turno!"):
                if nombre and telefono and hora_str:
                    fecha_hora = f"{fecha_str}T{hora_str}:00"
                    
                    datos_pac = {"nombre_completo": nombre, "telefono": telefono}
                    res_pac = requests.post(f"{API_URL}/pacientes/", json=datos_pac)
                    
                    if res_pac.status_code == 200:
                        paciente_id = res_pac.json()["id"]
                        
                        datos_turno = {
                            "paciente_id": paciente_id, "fecha_hora": fecha_hora, 
                            "estado": "Pendiente", "tratamiento": ", ".join(opciones)
                        }
                        res_turno = requests.post(f"{API_URL}/turnos/", json=datos_turno)
                        
                        if res_turno.status_code == 200:
                            # AQUÍ ESTÁ LA MAGIA: Le avisamos que fue un éxito y lo mandamos al inicio
                            st.session_state.turno_exito = True
                            st.session_state.vista = "Inicio"
                            st.rerun()
                else:
                    st.warning("Completa nombre, teléfono y selecciona un horario válido.")
    else:
        st.warning("⚠️ El catálogo está vacío. El doctor debe agregar servicios.")


# ==========================================
# 2. PANEL DEL DOCTOR (PRIVADO - ERP)
# ==========================================
elif st.session_state.vista == "Doctor":
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("⬅️ Volver al Inicio"):
            st.session_state.vista = "Inicio"
            st.session_state.logged_in = False
            st.rerun()
    with col_btn2:
        if st.session_state.logged_in:
            if st.button("🔒 Cerrar Sesión"):
                st.session_state.logged_in = False
                st.rerun()

    st.title("👨‍⚕️ Panel de Administración ERP")
    
    if not st.session_state.logged_in:
        password = st.text_input("Ingresa la clave de acceso:", type="password")
        if password == "admin123":
            st.session_state.logged_in = True
            st.rerun()
        elif password != "":
            st.error("Contraseña incorrecta")

    if st.session_state.logged_in:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Agenda", "⚙️ Servicios y Costos", "💰 Finanzas", "📦 Inventario", "🩺 Historial Clínico"])
        
        # --- PESTAÑA 1: AGENDA ---
        with tab1:
            with st.expander("➕ Agendar Turno Manual (Teléfono / Presencial)", expanded=False):
                try:
                    res_serv_manual = requests.get(f"{API_URL}/servicios/").json()
                    catalogo_manual = [s["nombre"] for s in res_serv_manual] if res_serv_manual else []
                    pacientes_manual = requests.get(f"{API_URL}/pacientes/").json()
                    turnos_actuales_doc = requests.get(f"{API_URL}/turnos/").json()
                except:
                    catalogo_manual = []
                    pacientes_manual = []
                    turnos_actuales_doc = []

                if catalogo_manual:
                    tab_nuevo, tab_exist = st.tabs(["👤 Nuevo Paciente", "👥 Paciente Existente"])
                    
                    with tab_nuevo:
                        with st.form("form_manual_nuevo", clear_on_submit=False):
                            col_n1, col_n2 = st.columns(2)
                            with col_n1:
                                nom_m = st.text_input("Nombre y Apellido")
                            with col_n2:
                                tel_m = st.text_input("Teléfono")
                            
                            fec_m = st.date_input("Fecha del turno", key="fec_m")
                            horarios_libres_doc = get_horarios_libres(str(fec_m), turnos_actuales_doc)
                            
                            if horarios_libres_doc:
                                hora_m_str = st.selectbox("Hora", horarios_libres_doc, key="hora_m_sel")
                            else:
                                st.error("Día completo.")
                                hora_m_str = None
                                
                            trat_m = st.multiselect("Tratamiento(s)", catalogo_manual, key="trat_m")
                            
                            if st.form_submit_button("Agendar Nuevo Paciente"):
                                if nom_m and tel_m and trat_m and hora_m_str:
                                    f_h = f"{fec_m}T{hora_m_str}:00"
                                    rp = requests.post(f"{API_URL}/pacientes/", json={"nombre_completo": nom_m, "telefono": tel_m})
                                    if rp.status_code == 200:
                                        p_id = rp.json()["id"]
                                        requests.post(f"{API_URL}/turnos/", json={"paciente_id": p_id, "fecha_hora": f_h, "estado": "Pendiente", "tratamiento": ", ".join(trat_m)})
                                        st.success("¡Turno guardado exitosamente!")
                                        st.rerun()
                                else:
                                    st.warning("Completa todos los datos y selecciona una hora.")

                    with tab_exist:
                        if pacientes_manual:
                            with st.form("form_manual_exist", clear_on_submit=False):
                                dic_pac_exist = {f"{p['nombre_completo']} - {p['telefono']}": p["id"] for p in pacientes_manual}
                                pac_sel_exist = st.selectbox("Buscar Paciente", ["Seleccionar..."] + list(dic_pac_exist.keys()))
                                
                                fec_me = st.date_input("Fecha del turno", key="fec_me")
                                horarios_libres_doce = get_horarios_libres(str(fec_me), turnos_actuales_doc)
                                
                                if horarios_libres_doce:
                                    hora_me_str = st.selectbox("Hora", horarios_libres_doce, key="hora_me_sel")
                                else:
                                    st.error("Día completo.")
                                    hora_me_str = None
                                    
                                trat_me = st.multiselect("Tratamiento(s)", catalogo_manual, key="trat_me")
                                
                                if st.form_submit_button("Agendar a Paciente Existente"):
                                    if pac_sel_exist != "Seleccionar..." and trat_me and hora_me_str:
                                        f_h = f"{fec_me}T{hora_me_str}:00"
                                        p_id = dic_pac_exist[pac_sel_exist]
                                        requests.post(f"{API_URL}/turnos/", json={"paciente_id": p_id, "fecha_hora": f_h, "estado": "Pendiente", "tratamiento": ", ".join(trat_me)})
                                        st.success("¡Turno guardado exitosamente!")
                                        st.rerun()
                                    else:
                                        st.warning("Selecciona paciente, tratamientos y hora.")
                        else:
                            st.info("Aún no hay pacientes registrados.")
                else:
                    st.warning("Para agendar manualmente, primero debes cargar Servicios en la pestaña correspondiente.")

            st.write("---")
            st.subheader("📋 Turnos Pendientes de Atención")
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
                        
                        fecha_hora_raw = turno['fecha_hora']
                        if "T" in fecha_hora_raw:
                            fecha_t, hora_t = fecha_hora_raw.split("T")
                            hora_limpia = hora_t[:5] 
                            titulo_expander = f"🦷 {paciente.get('nombre_completo', 'N/A')} | 📅 {fecha_t} | ⏰ {hora_limpia} hs"
                        else:
                            titulo_expander = f"🦷 {paciente.get('nombre_completo', 'N/A')} - {fecha_hora_raw}"
                        
                        with st.expander(titulo_expander):
                            st.write(f"**Tratamiento:** {turno['tratamiento']}")
                            st.write(f"**Estado del Turno:** {turno['estado']}")
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if paciente.get("telefono"):
                                    st.link_button("📲 Enviar WhatsApp", f"https://wa.me/{paciente['telefono']}?text=Hola, recordatorio de tu turno...")
                            with col_b:
                                if st.button("🗑️ Cancelar Turno", key=f"del_turno_{turno['id']}"):
                                    requests.delete(f"{API_URL}/turnos/{turno['id']}")
                                    st.rerun()
                else:
                    st.info("¡Excelente! No hay turnos pendientes.")
            except:
                st.error("Esperando conexión...")

        # --- PESTAÑA 2: SERVICIOS ---
        with tab2:
            st.subheader("Agregar Servicio Nuevo")
            with st.form("form_servicios", clear_on_submit=True):
                nuevo_nombre = st.text_input("Nombre del Servicio (Ej: Profilaxis)")
                col1, col2 = st.columns(2)
                with col1:
                    precio_texto = st.text_input("Precio a cobrar (₲)", placeholder="Ej: 150.000")
                with col2:
                    costo_texto = st.text_input("Costo de materiales (₲)", placeholder="Ej: 30.000")
                
                if st.form_submit_button("Guardar Servicio Nuevo"):
                    p_limpio = ''.join(filter(str.isdigit, precio_texto))
                    c_limpio = ''.join(filter(str.isdigit, costo_texto))
                    nuevo_precio = int(p_limpio) if p_limpio else 0
                    nuevo_costo = int(c_limpio) if c_limpio else 0
                    
                    if nuevo_nombre and nuevo_precio > 0:
                        requests.post(f"{API_URL}/servicios/", json={"nombre": nuevo_nombre, "precio_sugerido": nuevo_precio, "costo_real": nuevo_costo})
                        st.success("Servicio guardado exitosamente.")
                        st.rerun()

            st.write("---")
            st.subheader("Catálogo y Edición")
            try:
                res_serv_admin = requests.get(f"{API_URL}/servicios/").json()
                if res_serv_admin:
                    with st.expander("👀 Ver Lista Completa de Servicios", expanded=False):
                        for s in res_serv_admin:
                            st.write(f"**{s['nombre']}** | Precio: ₲ {s['precio_sugerido']:,}".replace(",", ".") + f" | Costo: ₲ {s['costo_real']:,}".replace(",", "."))
                    
                    opciones_serv = {s["nombre"]: s for s in res_serv_admin}
                    serv_sel = st.selectbox("Selecciona un servicio para modificar:", list(opciones_serv.keys()))
                    
                    if serv_sel:
                        datos_s = opciones_serv[serv_sel]
                        col_e1, col_e2, col_e3 = st.columns(3)
                        with col_e1:
                            edit_nombre = st.text_input("Nombre", value=datos_s["nombre"], key=f"en_{datos_s['id']}")
                        with col_e2:
                            edit_precio = st.text_input("Precio (₲)", value=f"{datos_s['precio_sugerido']:,}".replace(",","."), key=f"ep_{datos_s['id']}")
                        with col_e3:
                            edit_costo = st.text_input("Costo (₲)", value=f"{datos_s['costo_real']:,}".replace(",","."), key=f"ec_{datos_s['id']}")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("💾 Guardar Cambios de Servicio", type="primary"):
                                p_limpio = int(''.join(filter(str.isdigit, edit_precio)) or 0)
                                c_limpio = int(''.join(filter(str.isdigit, edit_costo)) or 0)
                                requests.put(f"{API_URL}/servicios/{datos_s['id']}", json={"nombre": edit_nombre, "precio_sugerido": p_limpio, "costo_real": c_limpio})
                                st.rerun()
                        with col_btn2:
                            if st.button("🚨 Borrar Servicio"):
                                requests.delete(f"{API_URL}/servicios/{datos_s['id']}")
                                st.rerun()
            except:
                pass

        # --- PESTAÑA 3: FINANZAS ---
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
                    
                    metodo = st.selectbox("Método de Pago:", ["Efectivo", "Transferencia", "Tarjeta"])
                    
                    if st.button("Registrar Cobro"):
                        requests.post(f"{API_URL}/pagos/", json={"turno_id": turno_datos['id'], "monto": monto_cobrar, "metodo_pago": metodo})
                        st.success("¡Cobro registrado! Verás la actualización en el Dashboard.")
                        st.rerun() 
                else:
                    st.success("No hay turnos pendientes de cobro.")
            except:
                pass

        # --- PESTAÑA 4: INVENTARIO ---
        with tab4:
            st.subheader("📦 Agregar Material Nuevo")
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
                        requests.post(f"{API_URL}/inventario/", json={"nombre_material": nombre_material, "cantidad": cantidad, "costo_unitario": costo_final})
                        st.success("¡Material agregado al inventario!")
                        st.rerun()

            st.write("---")
            st.subheader("Stock Actual y Edición")
            try:
                inventario = requests.get(f"{API_URL}/inventario/").json()
                if inventario:
                    with st.expander("📦 Ver Todo el Stock Actual", expanded=True):
                        for item in inventario:
                            st.info(f"**{item['nombre_material']}** | Cantidad: {item['cantidad']} | Costo Un.: ₲ {item['costo_unitario']:,}".replace(",", "."))

                    opciones_inv = {i["nombre_material"]: i for i in inventario}
                    inv_sel = st.selectbox("Selecciona un material para modificar:", list(opciones_inv.keys()))
                    
                    if inv_sel:
                        datos_i = opciones_inv[inv_sel]
                        col_i1, col_i2, col_i3 = st.columns(3)
                        with col_i1:
                            edit_mat = st.text_input("Material", value=datos_i["nombre_material"], key=f"im_{datos_i['id']}")
                        with col_i2:
                            edit_cant = st.number_input("Cantidad", value=datos_i["cantidad"], step=1, key=f"ic_{datos_i['id']}")
                        with col_i3:
                            edit_cost_i = st.text_input("Costo Un. (₲)", value=f"{datos_i['costo_unitario']:,}".replace(",","."), key=f"icu_{datos_i['id']}")
                        
                        col_btni1, col_btni2 = st.columns(2)
                        with col_btni1:
                            if st.button("💾 Actualizar Stock", type="primary"):
                                c_limpio = int(''.join(filter(str.isdigit, edit_cost_i)) or 0)
                                requests.put(f"{API_URL}/inventario/{datos_i['id']}", json={"nombre_material": edit_mat, "cantidad": edit_cant, "costo_unitario": c_limpio})
                                st.rerun()
                        with col_btni2:
                            if st.button("🚨 Borrar Material"):
                                requests.delete(f"{API_URL}/inventario/{datos_i['id']}")
                                st.rerun()
            except:
                pass

        # --- PESTAÑA 5: HISTORIAL CLÍNICO ---
        with tab5:
            st.subheader("🩺 Historial Clínico de Pacientes")
            
            try:
                pacientes_hist = requests.get(f"{API_URL}/pacientes/").json()
                
                if pacientes_hist:
                    dic_pacientes_hist = {f"{p['nombre_completo']} ({p['telefono']})": p["id"] for p in pacientes_hist}
                    opciones_pacientes = ["Seleccionar paciente..."] + list(dic_pacientes_hist.keys())
                    paciente_seleccionado = st.selectbox("👤 Buscar Paciente:", opciones_pacientes)
                    
                    if paciente_seleccionado != "Seleccionar paciente...":
                        pac_id = dic_pacientes_hist[paciente_seleccionado]
                        nombre_limpio = paciente_seleccionado.split(' (')[0]
                        
                        st.write("---")
                        st.write(f"### 📂 Carpeta Médica: {nombre_limpio}")
                        
                        todos_historiales = requests.get(f"{API_URL}/historial/").json()
                        historial_paciente = [h for h in todos_historiales if h["paciente_id"] == pac_id]
                        
                        if historial_paciente:
                            for ficha in reversed(historial_paciente):
                                with st.expander(f"🗓️ Fecha: {ficha['fecha']} | Pieza: {ficha['pieza_dental']} | {ficha['tratamiento']}"):
                                    st.write(f"**Tratamiento:** {ficha['tratamiento']}")
                                    st.write(f"**Observaciones:** {ficha['observaciones']}")
                                    if st.button("🗑️ Borrar este registro", key=f"del_h_{ficha['id']}"):
                                        requests.delete(f"{API_URL}/historial/{ficha['id']}")
                                        st.rerun()
                        else:
                            st.info("Este paciente es nuevo y aún no tiene registros en su historial.")
                        
                        st.write("---")
                        st.subheader("➕ Agregar Nuevo Registro Médico")
                        
                        with st.form("form_historial", clear_on_submit=True):
                            col_h1, col_h2 = st.columns(2)
                            with col_h1:
                                fecha_h = st.date_input("Fecha de atención")
                            with col_h2:
                                pieza_h = st.text_input("Pieza Dental (Ej: 36, 47 o 'General')")
                            
                            tratamiento_h = st.text_input("Tratamiento realizado")
                            observaciones_h = st.text_area("Observaciones (Alergias, dolor, materiales usados...)")
                            
                            if st.form_submit_button("💾 Guardar en Historial"):
                                if pieza_h and tratamiento_h:
                                    datos_ficha = {
                                        "paciente_id": pac_id,
                                        "fecha": str(fecha_h),
                                        "pieza_dental": pieza_h,
                                        "tratamiento": tratamiento_h,
                                        "observaciones": observaciones_h
                                    }
                                    requests.post(f"{API_URL}/historial/", json=datos_ficha)
                                    st.success("¡Registro guardado exitosamente!")
                                    st.rerun()
                                else:
                                    st.warning("Por favor completa la pieza dental y el tratamiento.")
                else:
                    st.warning("Todavía no hay pacientes registrados en el sistema.")
            except:
                st.error("Error conectando con la base de datos de historiales.")