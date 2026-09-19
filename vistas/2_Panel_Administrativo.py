import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

# ==========================================
# 1. SEGURIDAD: VERIFICAR QUE SEA ADMINISTRATIVO
# ==========================================
if "logueado" not in st.session_state or not st.session_state.logueado:
    st.error("⚠️ Debes iniciar sesión primero.")
    st.stop()

if st.session_state.usuario_rol != "Administrativo":
    st.error("⛔ Acceso denegado. Esta página es solo para personal Administrativo.")
    st.stop()

# ==========================================
# 2. CONEXIÓN A SUPABASE
# ==========================================
@st.cache_resource
def init_connection():
    # Usa st.secrets porque la app ya está en Streamlit Cloud
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("⚙️ Panel Administrativo HRMS")

# Crear dos pestañas principales
tab_permisos, tab_novedades = st.tabs(["📋 Solicitudes de Permisos", "⚠️ Novedades de Nómina"])

# ==========================================
# PESTAÑA 1: GESTIÓN DE PERMISOS
# ==========================================
with tab_permisos:
    st.subheader("Permisos Pendientes de Aprobación")
    
    try:
        # Traer solicitudes pendientes
        res_solicitudes = supabase.table("solicitudes").select("*").eq("estado", "Pendiente").execute()
        
        if res_solicitudes.data:
            for sol in res_solicitudes.data:
                # Usamos .get() para que no colapse si la columna tiene otro nombre
                nombre = sol.get('nombre', 'Empleado')
                fecha = sol.get('fecha', 'Fecha no especificada')
                motivo = sol.get('motivo', 'Motivo no especificado')
                
                # Si en tu BD le pusiste "descripcion" en vez de "detalle", también lo intentará buscar
                detalle = sol.get('detalle', sol.get('descripcion', sol.get('observacion', 'Sin detalle adicional')))
                
                with st.expander(f"Solicitud de {nombre} - {fecha}"):
                    st.write(f"**Motivo:** {motivo}")
                    st.write(f"**Detalle:** {detalle}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Aprobar", key=f"btn_aprobar_{sol['id']}", type="primary"):
                            supabase.table("solicitudes").update({"estado": "Aprobado"}).eq("id", sol['id']).execute()
                            st.success("Permiso Aprobado.")
                            st.rerun()
                    with col2:
                        if st.button("❌ Rechazar", key=f"btn_rechazar_{sol['id']}"):
                            supabase.table("solicitudes").update({"estado": "Rechazado"}).eq("id", sol['id']).execute()
                            st.error("Permiso Rechazado.")
                            st.rerun()
        else:
            st.info("No hay solicitudes de permisos pendientes en este momento.")
            
    except Exception as e:
        st.error(f"Error al cargar solicitudes: {e}")

# ==========================================
# PESTAÑA 2: REGISTRO DE NOVEDADES DE NÓMINA
# ==========================================
with tab_novedades:
    st.subheader("Registro Manual de Novedades")
    st.markdown("Ingresa ausencias, incapacidades y otras novedades que afectan la nómina.")
    
    try:
        # Traer solo los perfiles de Docentes
        res_perfiles = supabase.table("perfiles").select("id, nombre").eq("rol", "docente").execute()
        if res_perfiles.data:
            diccionario_docentes = {d["nombre"]: d["id"] for d in res_perfiles.data}
            nombres_docentes = list(diccionario_docentes.keys())
        else:
            diccionario_docentes = {}
            nombres_docentes = ["No hay docentes registrados"]
    except Exception as e:
        st.error(f"Error al cargar docentes: {e}")
        diccionario_docentes = {}
        nombres_docentes = []

    # Opciones extraídas de la tabla de convenciones del colegio
    opciones_novedad = [
        "H: Hospitalizada", 
        "INC: Incapacidad", 
        "P: Permiso Remunerado",
        "PN: Permiso No remunerado", 
        "R: Retiro", 
        "AI: Ausencia Injustificada",
        "NRH: No registra huella / firma", 
        "O: Otros", 
        "PH: Permiso por horas",
        "V: Vacaciones", 
        "IN: Ingreso", 
        "LM: Lic. Maternidad"
    ]

    with st.container(border=True):
        with st.form("form_registro_novedad", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                docente_seleccionado = st.selectbox("Seleccionar Empleado", options=nombres_docentes)
                fecha_novedad = st.date_input("Fecha de la Novedad", value=date.today())
                
            with col2:
                tipo_novedad = st.selectbox("Código de Convención", options=opciones_novedad)
                observacion = st.text_input("Observación / Detalle (Opcional)")
                
            st.markdown("<br>", unsafe_allow_html=True)
            btn_guardar = st.form_submit_button("💾 Registrar Novedad en Base de Datos", type="primary", use_container_width=True)
            
            if btn_guardar:
                if docente_seleccionado and diccionario_docentes:
                    docente_id = diccionario_docentes[docente_seleccionado]
                    try:
                        # Insertar en la tabla de Supabase
                        supabase.table("novedades_nomina").insert({
                            "docente_id": docente_id,
                            "fecha": str(fecha_novedad),
                            "codigo_novedad": tipo_novedad,
                            "observacion": observacion
                        }).execute()
                        st.success(f"Novedad '{tipo_novedad}' registrada exitosamente para {docente_seleccionado}.")
                    except Exception as e:
                        st.error(f"Error al guardar la novedad: {e}")
                else:
                    st.warning("Por favor seleccione un empleado válido.")

    st.divider()
    st.subheader("📊 Historial de Novedades")
    
    try:
        # Hacemos JOIN con perfiles para mostrar el nombre del docente
        res_novedades = supabase.table("novedades_nomina").select("fecha, codigo_novedad, observacion, perfiles(nombre)").order("fecha", desc=True).limit(20).execute()
        
        if res_novedades.data:
            datos_tabla = []
            for nov in res_novedades.data:
                nombre_docente = nov.get("perfiles", {}).get("nombre", "Desconocido") if nov.get("perfiles") else "Desconocido"
                datos_tabla.append({
                    "Fecha": nov.get("fecha"),
                    "Empleado": nombre_docente,
                    "Novedad": nov.get("codigo_novedad"),
                    "Observación": nov.get("observacion")
                })
            
            df_novedades = pd.DataFrame(datos_tabla)
            st.dataframe(df_novedades, use_container_width=True, hide_index=True)
        else:
            st.info("No hay novedades registradas recientemente.")
    except Exception as e:
        st.error(f"No se pudo cargar el historial: {e}")