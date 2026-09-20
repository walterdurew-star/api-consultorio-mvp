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
            # (Igual a tu código anterior: agendado manual y vista de pendientes)
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
                    
                    if pagos_h:
                        # Calculamos ganancias totales
                        total_rec = sum(p["monto"] for p in pagos_h)
                        col1, col2 = st.columns(2)
                        col1.metric("Ingresos Totales", f"₲ {int(total_rec):,}".replace(",", "."))
                        
                        # GRAFICOS
                        st.write("---")
                        st.write("#### Ingresos por Método de Pago")
                        df_pagos = pd.DataFrame(pagos_h)
                        grafico_metodos = df_pagos.groupby("metodo_pago")["monto"].sum()
                        st.bar_chart(grafico_metodos)
                    else:
                        st.info("Aún no hay cobros registrados para mostrar gráficos.")
                    
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
                        st.success(f"Cobro de {st.session_state.ultimo_recibo['paciente']} procesado con éxito.")
                        pdf_bytes = generar_pdf_recibo(
                            st.session_state.ultimo_recibo["paciente"], 
                            st.session_state.ultimo_recibo["monto"], 
                            st.session_state.ultimo_recibo["tratamientos"], 
                            st.session_state.ultimo_recibo["metodo"]
                        )
                        st.download_button(
                            label="📄 DESCARGAR RECIBO EN PDF",
                            data=pdf_bytes,
                            file_name=f"Recibo_{st.session_state.ultimo_recibo['paciente']}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                except Exception as e:
                    pass

            with tab_servicios:
                st.info("Aquí administras precios de servicios. (Activo para Doctor)")
            with tab_inventario:
                st.info("Aquí administras resinas, anestesias. (Activo para Doctor)")