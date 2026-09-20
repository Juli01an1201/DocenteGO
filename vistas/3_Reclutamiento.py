import streamlit as st
import pandas as pd
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
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("🤝 Reclutamiento y Selección")

# Crear dos pestañas principales
tab_vacantes, tab_candidatos = st.tabs(["📢 Gestión de Vacantes", "📄 Candidatos Postulados"])

# ==========================================
# PESTAÑA 1: GESTIÓN DE VACANTES
# ==========================================
with tab_vacantes:
    st.subheader("Crear Nueva Vacante")
    
    with st.container(border=True):
        with st.form("form_crear_vacante", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                titulo_vacante = st.text_input("Título del cargo (Ej: Docente de Matemáticas)")
                departamento = st.selectbox("Departamento", ["Académico", "Administrativo", "Mantenimiento", "Directivo", "Otro"])
            
            with col2:
                descripcion = st.text_area("Descripción y Requisitos del perfil", height=110)
                
            st.markdown("<br>", unsafe_allow_html=True)
            btn_crear_vacante = st.form_submit_button("📢 Publicar Vacante", type="primary", use_container_width=True)
            
            if btn_crear_vacante:
                if titulo_vacante and descripcion:
                    try:
                        # Insertar en la tabla vacantes
                        supabase.table("vacantes").insert({
                            "titulo": titulo_vacante,
                            "departamento": departamento,
                            "descripcion": descripcion,
                            "estado": "Abierta"
                        }).execute()
                        st.success(f"La vacante '{titulo_vacante}' ha sido publicada exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear vacante: {e}")
                else:
                    st.warning("Por favor completa el título y la descripción.")

    st.divider()
    st.subheader("📋 Vacantes Actuales")
    
    try:
        # Traer todas las vacantes ordenadas por las más recientes
        res_vacantes = supabase.table("vacantes").select("*").order("created_at", desc=True).execute()
        
        if res_vacantes.data:
            for vacante in res_vacantes.data:
                # Uso de .get() por seguridad
                id_vac = vacante.get("id")
                titulo = vacante.get("titulo", "Sin título")
                depto = vacante.get("departamento", "N/A")
                estado = vacante.get("estado", "Desconocido")
                desc = vacante.get("descripcion", "Sin descripción")
                
                # Definir color visual según el estado
                color_estado = "green" if estado == "Abierta" else "red"
                
                with st.expander(f"{titulo} ({depto}) - Estado: {estado}"):
                    st.markdown(f"**Estado actual:** <span style='color:{color_estado}; font-weight:bold;'>{estado}</span>", unsafe_allow_html=True)
                    st.write(f"**Descripción:** {desc}")
                    
                    # Botones para cambiar el estado de la vacante (Abrir/Cerrar)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if estado == "Cerrada":
                            if st.button("🔓 Reabrir Vacante", key=f"abrir_{id_vac}"):
                                supabase.table("vacantes").update({"estado": "Abierta"}).eq("id", id_vac).execute()
                                st.rerun()
                    with col_b:
                        if estado == "Abierta":
                            if st.button("🔒 Cerrar Vacante", key=f"cerrar_{id_vac}", type="primary"):
                                supabase.table("vacantes").update({"estado": "Cerrada"}).eq("id", id_vac).execute()
                                st.rerun()
        else:
            st.info("No hay vacantes creadas aún.")
    except Exception as e:
        st.error(f"Error al cargar vacantes: {e}")

# ==========================================
# PESTAÑA 2: CANDIDATOS POSTULADOS
# ==========================================
with tab_candidatos:
    st.subheader("Hojas de Vida Recibidas")
    st.markdown("Aquí aparecerán los candidatos que apliquen a través del portal externo.")
    
    try:
        # Hacemos JOIN con la tabla vacantes para mostrar a qué cargo aplicaron
        res_postulaciones = supabase.table("postulaciones").select("*, vacantes(titulo)").order("created_at", desc=True).execute()
        
        if res_postulaciones.data:
            datos_candidatos = []
            for post in res_postulaciones.data:
                cargo = post.get("vacantes", {}).get("titulo", "Vacante eliminada") if post.get("vacantes") else "Desconocido"
                
                datos_candidatos.append({
                    "Fecha": str(post.get("created_at"))[:10],
                    "Candidato": post.get("nombre_candidato", "N/A"),
                    "Cargo al que aplica": cargo,
                    "Estado": post.get("estado_proceso", "Recibida")
                })
            
            # Tabla resumen superior
            df_candidatos = pd.DataFrame(datos_candidatos)
            st.dataframe(df_candidatos, use_container_width=True, hide_index=True)
            
            st.markdown("### 🔍 Detalle y Gestión del Embudo")
            
            # Tarjetas individuales para gestionar a cada candidato
            for post in res_postulaciones.data:
                nombre = post.get("nombre_candidato", "N/A")
                cargo = post.get("vacantes", {}).get("titulo", "Vacante eliminada") if post.get("vacantes") else "Desconocido"
                cv_link = post.get("cv_url", "")
                id_post = post.get("id")
                estado_actual = post.get("estado_proceso", "Recibida")
                
                with st.expander(f"👤 {nombre} ➡️ Aplicó a: {cargo} ({estado_actual})"):
                    st.write(f"**Correo:** {post.get('correo_candidato', 'N/A')}")
                    st.write(f"**Teléfono:** {post.get('telefono', 'N/A')}")
                    
                    # Botón/Enlace para descargar el PDF
                    if cv_link:
                        st.markdown(f"**Hoja de vida:** [🔗 Clic para Ver/Descargar PDF]({cv_link})")
                    else:
                        st.write("**Hoja de vida:** No adjuntada")
                    
                    st.divider()
                    
                    # Selector para mover al candidato por el embudo de contratación
                    nuevo_estado = st.selectbox(
                        "Actualizar estado del proceso", 
                        ["Recibida", "En Revisión", "Entrevista Programada", "Prueba Técnica", "Contratado", "Rechazado"],
                        index=["Recibida", "En Revisión", "Entrevista Programada", "Prueba Técnica", "Contratado", "Rechazado"].index(estado_actual) if estado_actual in ["Recibida", "En Revisión", "Entrevista Programada", "Prueba Técnica", "Contratado", "Rechazado"] else 0,
                        key=f"estado_{id_post}"
                    )
                    
                    if st.button("💾 Guardar Cambio de Estado", key=f"btn_estado_{id_post}", type="primary"):
                        supabase.table("postulaciones").update({"estado_proceso": nuevo_estado}).eq("id", id_post).execute()
                        st.success("Estado del candidato actualizado.")
                        st.rerun()
                        
        else:
            st.info("Aún no hay postulaciones recibidas. Publica una vacante y comparte el enlace del portal público.")
            
    except Exception as e:
        st.error(f"Error al cargar candidatos: {e}")