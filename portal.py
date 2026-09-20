import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF

# --- CONEXIÓN A LA NUBE ---
API_URL = "https://api-consultorio-mvp.onrender.com"

st.set_page_config(page_title="Portal Odontológico ERP", page_icon="🦷", layout="wide")

# Inicializar memoria
if "vista" not in st.session_state:
    st.session_state.vista = "Inicio"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "rol" not in st.session_state:
    st.session_state.rol = ""
if "turno_exito" not in st.session_state:
    st.session_state.turno_exito = False
if "ultimo_recibo" not in st.session_state:
    st.session_state.ultimo_recibo = None

# --- FUNCIONES AUXILIARES ---
def get_horarios_libres(fecha_str, turnos):
    horarios_posibles = [f"{h:02d}:{m:02d}" for h in range(8, 19) for m in (0, 30)]
    if isinstance(turnos, list):
        ocupados = [t["fecha_hora"].split("T")[1][:5] for t in turnos if t.get("fecha_hora", "").startswith(fecha_str)]
    else:
        ocupados = []
    return [h for h in horarios_posibles if h not in ocupados]

def generar_pdf_recibo(paciente, monto, tratamientos, metodo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "CLINICA ODONTOLOGICA - RECIBO DE PAGO", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"Paciente: {paciente}", ln=True)
    pdf.cell(200, 10, f"Tratamientos Realizados: {tratamientos}", ln=True)
    pdf.cell(200, 10, f"Metodo de Pago: {metodo}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    monto_str = f"Gs. {monto:,}".replace(",", ".")
    pdf.cell(200, 10, f"MONTO TOTAL ABONADO: {monto_str}", ln=True)
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, "Gracias por confiar en nosotros para el cuidado de su sonrisa.", ln=True, align="C")
    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# 0. INICIO
# ==========================================
if st.session_state.vista == "Inicio":
    if st.session_state.turno_exito:
        st.balloons()
        st.success("🎉 ¡Tu turno ha sido agendado exitosamente! Te esperamos en la clínica. 🦷")
        st.session_state.turno_exito = False 
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
        if st.button("👨‍⚕️ Personal de Clínica\n(Ingresar al ERP)", use_container_width=True):
            st.session_state.vista = "Doctor"
            st.rerun()

# ==========================================
# 1. PACIENTE
# ==========================================
elif st.session_state.vista == "Paciente":
    if st.button("⬅️ Volver al Inicio"):
        st.session_state.vista = "Inicio"
        st.rerun()
        
    st.title("🦷 Autogestión de Pacientes")
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
            st.write("### 📅 Agendar mi Turno")
            nombre = st.text_input("Tu Nombre y Apellido")
            telefono = st.text_input("Tu Teléfono WhatsApp") 
            fecha_str = str(st.date_input("¿Qué día te gustaría venir?"))
            
            try: turnos_actuales = requests.get(f"{API_URL}/turnos/").json()
            except: turnos_actuales = []
            horarios_libres = get_horarios_libres(fecha_str, turnos_actuales)
            
            if horarios_libres: hora_str = st.selectbox("¿A qué hora?", horarios_libres)
            else: st.error("❌ Día completo."); hora_str = None
            
            if st.button("¡Confirmar mi Turno!"):
                if nombre and telefono and hora_str:
                    fecha_hora = f"{fecha_str}T{hora_str}:00"
                    turnos_verificacion = requests.get(f"{API_URL}/turnos/").json()
                    if fecha_hora in [t["fecha_hora"] for t in turnos_verificacion]:
                        st.error("❌ Este horario acaba de ser ocupado.")
                    else:
                        rp = requests.post(f"{API_URL}/pacientes/", json={"nombre_completo": nombre, "telefono": telefono})
                        if rp.status_code == 200:
                            requests.post(f"{API_URL}/turnos/", json={"paciente_id": rp.json()["id"], "fecha_hora": fecha_hora, "estado": "Pendiente", "tratamiento": ", ".join(opciones)})
                            st.session_state.turno_exito = True
                            st.session_state.vista = "Inicio"
                            st.rerun()
    else: st.warning("Catálogo vacío.")

# ==========================================
# 2. PANEL ERP (DOCTOR / SECRETARIA)
# ==========================================
elif st.session_state.vista == "Doctor":
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("⬅️ Volver al Inicio"):
            st.session_state.vista = "Inicio"; st.session_state.logged_in = False; st.rerun()
    with col_btn2:
        if st.session_state.logged_in:
            if st.button("🔒 Cerrar Sesión"):
                st.session_state.logged_in = False; st.session_state.rol = ""; st.rerun()

    st.title("👨‍⚕️ Panel de Administración ERP")
    
    # --- SISTEMA DE ROLES (LOGIN) ---
    if not st.session_state.logged_in:
        usuario_sel = st.selectbox("Usuario:", ["Doctor", "Secretaria"])
        password = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            if usuario_sel == "Doctor" and password == "doc123":
                st.session_state.logged_in = True; st.session_state.rol = "Doctor"; st.rerun()
            elif usuario_sel == "Secretaria" and password == "secre123":
                st.session_state.logged_in = True; st.session_state.rol = "Secretaria"; st.rerun()
            else:
                st.error("Contraseña incorrecta")

    if st.session_state.logged_in:
        st.caption(f"👤 Ingresaste como: **{st.session_state.rol}**")
        
        # --- BLOQUEO POR ROLES ---
        if st.session_state.rol == "Doctor":
            tabs = st.tabs(["📅 Agenda", "🩺 Historial Clínico", "💰 Finanzas (PDF y Gráficos)", "⚙️ Servicios", "📦 Inventario"])
            tab_agenda, tab_historial, tab_finanzas, tab_servicios, tab_inventario = tabs
        elif st.session_state.rol == "Secretaria":
            tabs = st.tabs(["📅 Agenda", "🩺 Historial Clínico"])
            tab_agenda, tab_historial = tabs
            tab_finanzas, tab_servicios, tab_inventario = None, None, None

        # --- PESTAÑA AGENDA (Ambos roles) ---
        with tab_agenda:
            with st.expander("➕ Agendar Turno Manual (Teléfono / Presencial)", expanded=False):
                try:
                    res_serv_manual = requests.get(f"{API_URL}/servicios/").json()
                    catalogo_manual = [s["nombre"] for s in res_serv_manual] if res_serv_manual else []
                    pacientes_manual = requests.get(f"{API_URL}/pacientes/").json()
                    turnos_actuales_doc = requests.get(f"{API_URL}/turnos/").json()
                except:
                    catalogo_manual = []; pacientes_manual = []; turnos_actuales_doc = []

                if catalogo_manual:
                    tab_nuevo, tab_exist = st.tabs(["👤 Nuevo Paciente", "👥 Paciente Existente"])
                    with tab_nuevo:
                        with st.form("form_manual_nuevo", clear_on_submit=False):
                            col_n1, col_n2 = st.columns(2)
                            with col_n1: nom_m = st.text_input("Nombre y Apellido")
                            with col_n2: tel_m = st.text_input("Teléfono")
                            
                            fec_m = st.date_input("Fecha del turno", key="fec_m")
                            horarios_libres_doc = get_horarios_libres(str(fec_m), turnos_actuales_doc)
                            if horarios_libres_doc: hora_m_str = st.selectbox("Hora", horarios_libres_doc, key="hora_m_sel")
                            else: st.error("Día completo."); hora_m_str = None
                                
                            trat_m = st.multiselect("Tratamiento(s)", catalogo_manual, key="trat_m")
                            
                            if st.form_submit_button("Agendar Nuevo Paciente"):
                                if nom_m and tel_m and trat_m and hora_m_str:
                                    f_h = f"{fec_m}T{hora_m_str}:00"
                                    if f_h in [t["fecha_hora"] for t in turnos_actuales_doc]:
                                        st.error("❌ Horario ocupado.")
                                    else:
                                        rp = requests.post(f"{API_URL}/pacientes/", json={"nombre_completo": nom_m, "telefono": tel_m})
                                        if rp.status_code == 200:
                                            requests.post(f"{API_URL}/turnos/", json={"paciente_id": rp.json()["id"], "fecha_hora": f_h, "estado": "Pendiente", "tratamiento": ", ".join(trat_m)})
                                            st.success("¡Turno guardado!"); st.rerun()
                                else: st.warning("Completa todos los datos.")

                    with tab_exist:
                        if pacientes_manual:
                            with st.form("form_manual_exist", clear_on_submit=False):
                                dic_pac_exist = {f"{p['nombre_completo']} - {p['telefono']}": p["id"] for p in pacientes_manual}
                                pac_sel_exist = st.selectbox("Buscar Paciente", ["Seleccionar..."] + list(dic_pac_exist.keys()))
                                fec_me = st.date_input("Fecha del turno", key="fec_me")
                                horarios_libres_doce = get_horarios_libres(str(fec_me), turnos_actuales_doc)
                                if horarios_libres_doce: hora_me_str = st.selectbox("Hora", horarios_libres_doce, key="hora_me_sel")
                                else: st.error("Día completo."); hora_me_str = None
                                trat_me = st.multiselect("Tratamiento(s)", catalogo_manual, key="trat_me")
                                
                                if st.form_submit_button("Agendar Existente"):
                                    if pac_sel_exist != "Seleccionar..." and trat_me and hora_me_str:
                                        f_h = f"{fec_me}T{hora_me_str}:00"
                                        if f_h in [t["fecha_hora"] for t in turnos_actuales_doc]:
                                            st.error("❌ Horario ocupado.")
                                        else:
                                            requests.post(f"{API_URL}/turnos/", json={"paciente_id": dic_pac_exist[pac_sel_exist], "fecha_hora": f_h, "estado": "Pendiente", "tratamiento": ", ".join(trat_me)})
                                            st.success("¡Turno guardado!"); st.rerun()
                                    else: st.warning("Completa todos los datos.")
                        else: st.info("Sin pacientes registrados.")
                else: st.warning("Faltan servicios en el catálogo.")

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
                        f_raw = turno['fecha_hora']
                        titulo = f"🦷 {paciente.get('nombre_completo', 'N/A')} | 📅 {f_raw[:10]} | ⏰ {f_raw[11:16]} hs" if "T" in f_raw else f_raw
                        
                        with st.expander(titulo):
                            st.write(f"**Tratamiento:** {turno['tratamiento']}")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if paciente.get("telefono"): st.link_button("📲 Enviar WhatsApp", f"https://wa.me/{paciente['telefono']}")
                            with col_b:
                                if st.button("🗑️ Cancelar Turno", key=f"del_{turno['id']}"):
                                    requests.delete(f"{API_URL}/turnos/{turno['id']}")
                                    st.rerun()
                else: st.info("No hay turnos pendientes.")
            except: st.error("Conectando...")

        # --- PESTAÑA HISTORIAL CLINICO (Ambos roles) ---
        with tab_historial:
            st.subheader("🩺 Fichas Clínicas")
            try:
                pac_hist = requests.get(f"{API_URL}/pacientes/").json()
                if pac_hist:
                    dic_p_h = {f"{p['nombre_completo']}": p["id"] for p in pac_hist}
                    p_sel = st.selectbox("Buscar Paciente:", ["Seleccionar..."] + list(dic_p_h.keys()))
                    if p_sel != "Seleccionar...":
                        pac_id = dic_p_h[p_sel]
                        historias = [h for h in requests.get(f"{API_URL}/historial/").json() if h["paciente_id"] == pac_id]
                        if historias:
                            for ficha in reversed(historias):
                                with st.expander(f"🗓️ {ficha['fecha']} | Pieza: {ficha['pieza_dental']}"):
                                    st.write(f"**Tratamiento:** {ficha['tratamiento']}")
                                    st.write(f"**Observaciones:** {ficha['observaciones']}")
                        else: st.info("Sin registros.")
                        
                        st.write("---"); st.write("➕ Nuevo Registro")
                        with st.form("form_h", clear_on_submit=True):
                            f_h = st.date_input("Fecha"); p_h = st.text_input("Pieza")
                            t_h = st.text_input("Tratamiento"); o_h = st.text_area("Notas")
                            if st.form_submit_button("Guardar"):
                                requests.post(f"{API_URL}/historial/", json={"paciente_id": pac_id, "fecha": str(f_h), "pieza_dental": p_h, "tratamiento": t_h, "observaciones": o_h})
                                st.rerun()
            except: pass

        # --- PESTAÑAS PRIVADAS (Solo Doctor) ---
        if st.session_state.rol == "Doctor":
            
            with tab_finanzas:
                st.subheader("📊 Gráficos y Dashboard Financiero")
                try:
                    pagos_h = requests.get(f"{API_URL}/pagos/").json()
                    serv_h = requests.get(f"{API_URL}/servicios/").json()
                    turn_h = requests.get(f"{API_URL}/turnos/").json()
                    
                    dic_costos = {s["nombre"]: s.get("costo_real", 0) for s in serv_h}
                    dic_turnos_trat = {t["id"]: t["tratamiento"] for t in turn_h}
                    
                    total_rec = sum(p["monto"] for p in pagos_h)
                    total_cos = 0
                    for p in pagos_h:
                        trat_str = dic_turnos_trat.get(p["turno_id"], "")
                        for tr in trat_str.split(", "):
                            total_cos += dic_costos.get(tr, 0)
                            
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Ingresos", f"₲ {int(total_rec):,}".replace(",", "."))
                    col2.metric("Costos", f"₲ {int(total_cos):,}".replace(",", "."))
                    col3.metric("Ganancia Neta", f"₲ {int(total_rec - total_cos):,}".replace(",", "."))
                    
                    if pagos_h:
                        st.write("---")
                        st.write("#### Ingresos por Método de Pago")
                        df_pagos = pd.DataFrame(pagos_h)
                        grafico_metodos = df_pagos.groupby("metodo_pago")["monto"].sum()
                        st.bar_chart(grafico_metodos)
                    
                    st.write("---")
                    st.subheader("💰 Registrar Cobro y Generar Recibo PDF")
                    pacientes_fin = requests.get(f"{API_URL}/pacientes/").json()
                    dic_pac_fin = {p["id"]: p["nombre_completo"] for p in pacientes_fin}
                    cat_precios = {s["nombre"]: s["precio_sugerido"] for s in serv_h}
                    t_pagados = {p["turno_id"] for p in pagos_h}
                    t_pendientes = [t for t in turn_h if t["id"] not in t_pagados]
                    
                    if t_pendientes:
                        op_t = {f"Turno #{t['id']} - {dic_pac_fin.get(t['paciente_id'])} - {t['tratamiento']}": t for t in t_pendientes}
                        t_sel = st.selectbox("Seleccionar Turno a Cobrar:", list(op_t.keys()))
                        t_datos = op_t[t_sel]
                        nom_pac_recibo = dic_pac_fin.get(t_datos['paciente_id'])
                        
                        presu = sum([cat_precios.get(tr, 0) for tr in t_datos['tratamiento'].split(", ")])
                        st.write(f"📝 **Sugerido:** ₲ {int(presu):,}".replace(",", "."))
                        
                        monto_txt = st.text_input("Monto final a cobrar:", value=f"{int(presu):,}".replace(",", "."))
                        metodo = st.selectbox("Método:", ["Efectivo", "Transferencia", "Tarjeta"])
                        
                        if st.button("Registrar Cobro"):
                            m_cobrar = int(''.join(filter(str.isdigit, monto_txt)) or 0)
                            requests.post(f"{API_URL}/pagos/", json={"turno_id": t_datos['id'], "monto": m_cobrar, "metodo_pago": metodo})
                            st.session_state.ultimo_recibo = {"paciente": nom_pac_recibo, "monto": m_cobrar, "tratamientos": t_datos['tratamiento'], "metodo": metodo}
                            st.success("¡Cobro guardado!")
                            st.rerun()
                    else:
                        st.success("No hay turnos pendientes de cobro.")

                    # --- BOTON DE DESCARGA PDF ---
                    if st.session_state.ultimo_recibo:
                        st.write("---")
                        st.success(f"Cobro de {st.session_state.ultimo_recibo['paciente']} procesado.")
                        pdf_bytes = generar_pdf_recibo(
                            st.session_state.ultimo_recibo["paciente"], 
                            st.session_state.ultimo_recibo["monto"], 
                            st.session_state.ultimo_recibo["tratamientos"], 
                            st.session_state.ultimo_recibo["metodo"]
                        )
                        st.download_button(
                            label="📄 DESCARGAR RECIBO EN PDF", data=pdf_bytes,
                            file_name=f"Recibo_{st.session_state.ultimo_recibo['paciente']}.pdf", mime="application/pdf", type="primary"
                        )
                except: pass

            with tab_servicios:
                st.subheader("Agregar Servicio Nuevo")
                with st.form("form_servicios", clear_on_submit=True):
                    nuevo_nombre = st.text_input("Nombre del Servicio (Ej: Profilaxis)")
                    col1, col2 = st.columns(2)
                    with col1: precio_texto = st.text_input("Precio a cobrar (₲)", placeholder="Ej: 150.000")
                    with col2: costo_texto = st.text_input("Costo de materiales (₲)", placeholder="Ej: 30.000")
                    if st.form_submit_button("Guardar Servicio Nuevo"):
                        p_limpio = ''.join(filter(str.isdigit, precio_texto))
                        c_limpio = ''.join(filter(str.isdigit, costo_texto))
                        nuevo_precio = int(p_limpio) if p_limpio else 0
                        nuevo_costo = int(c_limpio) if c_limpio else 0
                        if nuevo_nombre and nuevo_precio > 0:
                            requests.post(f"{API_URL}/servicios/", json={"nombre": nuevo_nombre, "precio_sugerido": nuevo_precio, "costo_real": nuevo_costo})
                            st.success("Servicio guardado exitosamente."); st.rerun()

                st.write("---")
                st.subheader("Catálogo y Edición")
                try:
                    res_serv_admin = requests.get(f"{API_URL}/servicios/").json()
                    if res_serv_admin:
                        with st.expander("👀 Ver Lista Completa", expanded=False):
                            for s in res_serv_admin:
                                st.write(f"**{s['nombre']}** | Precio: ₲ {s['precio_sugerido']:,}".replace(",", ".") + f" | Costo: ₲ {s['costo_real']:,}".replace(",", "."))
                        opciones_serv = {s["nombre"]: s for s in res_serv_admin}
                        serv_sel = st.selectbox("Modificar servicio:", list(opciones_serv.keys()))
                        if serv_sel:
                            datos_s = opciones_serv[serv_sel]
                            col_e1, col_e2, col_e3 = st.columns(3)
                            with col_e1: edit_nombre = st.text_input("Nombre", value=datos_s["nombre"], key=f"en_{datos_s['id']}")
                            with col_e2: edit_precio = st.text_input("Precio (₲)", value=f"{datos_s['precio_sugerido']:,}".replace(",","."), key=f"ep_{datos_s['id']}")
                            with col_e3: edit_costo = st.text_input("Costo (₲)", value=f"{datos_s['costo_real']:,}".replace(",","."), key=f"ec_{datos_s['id']}")
                            
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("💾 Guardar Cambios", type="primary"):
                                    p_limpio = int(''.join(filter(str.isdigit, edit_precio)) or 0)
                                    c_limpio = int(''.join(filter(str.isdigit, edit_costo)) or 0)
                                    requests.put(f"{API_URL}/servicios/{datos_s['id']}", json={"nombre": edit_nombre, "precio_sugerido": p_limpio, "costo_real": c_limpio})
                                    st.rerun()
                            with col_btn2:
                                if st.button("🚨 Borrar Servicio"):
                                    requests.delete(f"{API_URL}/servicios/{datos_s['id']}"); st.rerun()
                except: pass

            with tab_inventario:
                st.subheader("📦 Agregar Material Nuevo")
                with st.form("form_inventario", clear_on_submit=True):
                    nombre_material = st.text_input("Nombre del Material (Ej: Resina A2)")
                    col_cant, col_cost = st.columns(2)
                    with col_cant: cantidad = st.number_input("Cantidad en Stock", min_value=0, step=1)
                    with col_cost: costo_unitario_txt = st.text_input("Costo Unitario (₲)")
                    if st.form_submit_button("Agregar Material"):
                        costo_u_limpio = ''.join(filter(str.isdigit, costo_unitario_txt))
                        costo_final = int(costo_u_limpio) if costo_u_limpio else 0
                        if nombre_material and cantidad > 0:
                            requests.post(f"{API_URL}/inventario/", json={"nombre_material": nombre_material, "cantidad": cantidad, "costo_unitario": costo_final})
                            st.success("¡Material agregado!"); st.rerun()

                st.write("---")
                st.subheader("Stock Actual y Edición")
                try:
                    inventario = requests.get(f"{API_URL}/inventario/").json()
                    if inventario:
                        with st.expander("📦 Ver Todo el Stock", expanded=True):
                            for item in inventario:
                                st.info(f"**{item['nombre_material']}** | Cantidad: {item['cantidad']} | Costo Un.: ₲ {item['costo_unitario']:,}".replace(",", "."))
                        opciones_inv = {i["nombre_material"]: i for i in inventario}
                        inv_sel = st.selectbox("Modificar material:", list(opciones_inv.keys()))
                        if inv_sel:
                            datos_i = opciones_inv[inv_sel]
                            col_i1, col_i2, col_i3 = st.columns(3)
                            with col_i1: edit_mat = st.text_input("Material", value=datos_i["nombre_material"], key=f"im_{datos_i['id']}")
                            with col_i2: edit_cant = st.number_input("Cantidad", value=datos_i["cantidad"], step=1, key=f"ic_{datos_i['id']}")
                            with col_i3: edit_cost_i = st.text_input("Costo Un. (₲)", value=f"{datos_i['costo_unitario']:,}".replace(",","."), key=f"icu_{datos_i['id']}")
                            
                            col_btni1, col_btni2 = st.columns(2)
                            with col_btni1:
                                if st.button("💾 Actualizar Stock", type="primary"):
                                    c_limpio = int(''.join(filter(str.isdigit, edit_cost_i)) or 0)
                                    requests.put(f"{API_URL}/inventario/{datos_i['id']}", json={"nombre_material": edit_mat, "cantidad": edit_cant, "costo_unitario": c_limpio})
                                    st.rerun()
                            with col_btni2:
                                if st.button("🚨 Borrar Material"):
                                    requests.delete(f"{API_URL}/inventario/{datos_i['id']}"); st.rerun()
                except: pass