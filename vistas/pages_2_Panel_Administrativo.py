import streamlit as st
import os
import smtplib
from io import BytesIO
from email.mime.text import MIMEText
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# 1. Seguridad
if "logueado" not in st.session_state or not st.session_state.logueado:
    st.warning("Debes iniciar sesión para ver esta página.")
    st.stop()
if st.session_state.usuario_rol != "Administrativo":
    st.error("Acceso denegado. Esta vista es exclusiva para el área administrativa.")
    st.stop()

# 2. Conexión
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

email_user = os.getenv("EMAIL_USER") or st.secrets.get("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD") or st.secrets.get("EMAIL_PASSWORD")
BUCKET_EVIDENCIAS = "evidencias"

# 3. Funciones
def enviar_correo(destinatario, estado, observaciones=""):
    if not destinatario or not email_user or not email_password:
        return
    asunto = f"DocenteGO - Solicitud {estado}"
    cuerpo = f"Hola,\n\nTu solicitud ha sido {estado}.\n\nObservaciones: {observaciones if observaciones else 'Sin observaciones.'}\n\nDocenteGO"
    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = asunto
    mensaje["From"] = email_user
    mensaje["To"] = destinatario
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
            servidor.starttls()
            servidor.login(email_user, email_password)
            servidor.send_message(mensaje)
    except Exception as e:
        st.warning(f"Error al enviar correo: {e}")

def obtener_url_evidencia(ruta):
    if not ruta: return None
    res = supabase.storage.from_(BUCKET_EVIDENCIAS).create_signed_url(ruta, 600)
    if isinstance(res, dict): return res.get("signedURL") or res.get("signed_url")
    return getattr(res, "signed_url", None)

def crear_excel(solicitudes):
    columnas = [
        "id", "created_at", "nombre", "correo", "fecha", 
        "hora_inicio", "hora_fin", "tipo_novedad", "motivo", 
        "estado", "observaciones", "evidencia_url"
    ]
    df = pd.DataFrame(solicitudes)
    for col in columnas:
        if col not in df.columns: df[col] = ""
    df = df[columnas].copy()
    
    if not df.empty:
        df["estado"] = df["estado"].fillna("Pendiente").replace("", "Pendiente")
        df["fecha"] = df["fecha"].astype(str)
        base = df.copy()
        base["es_aceptada"] = (base["estado"] == "Aceptada").astype(int)
        base["es_rechazada"] = (base["estado"] == "Rechazada").astype(int)
        
        docentes = (
            base.groupby(["nombre", "correo", "tipo_novedad"], dropna=False)
            .agg(total_solicitudes=("id", "count"), aceptadas=("es_aceptada", "sum"))
            .reset_index()
        )
    else:
        docentes = pd.DataFrame(columns=["nombre", "correo", "tipo_novedad", "total_solicitudes", "aceptadas"])

    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Solicitudes", index=False)
        docentes.to_excel(writer, sheet_name="Resumen_Nomina", index=False)
    return salida.getvalue(), docentes

# 4. Interfaz UI
st.title("📋 Gestión de Solicitudes y Nómina")

try:
    res = supabase.table("solicitudes").select("*").order("id", desc=True).execute()
    solicitudes = res.data or []

    pendientes = [s for s in solicitudes if s.get("estado") in [None, "", "Pendiente"]]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Solicitudes", len(solicitudes))
    m2.metric("Pendientes", len(pendientes))
    m3.metric("Procesadas", len(solicitudes) - len(pendientes))

    st.markdown("---")
    st.subheader(f"📥 Solicitudes pendientes: {len(pendientes)}")

    opciones = {f"#{s.get('id')} · {s.get('correo', '')} · {s.get('fecha', '')}": s for s in pendientes}

    if opciones:
        seleccion = st.selectbox("Selecciona una solicitud para gestionar", list(opciones.keys()))
        solicitud = opciones[seleccion]
        sol_id = solicitud.get("id")

        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Usuario:** {solicitud.get('correo', '')}")
                st.write(f"**Novedad:** {solicitud.get('tipo_novedad', 'No especificado')}")
                st.write(f"**Fecha:** {solicitud.get('fecha', '')}")
            with col2:
                st.write(f"**Horario:** {solicitud.get('hora_inicio', '')} - {solicitud.get('hora_fin', '')}")
                st.write(f"**Motivo:** {solicitud.get('motivo', '')}")
                
                ruta = solicitud.get("evidencia_url")
                if ruta:
                    url = obtener_url_evidencia(ruta)
                    if url: st.link_button("📎 Ver evidencia", url)
                else: st.caption("Sin evidencia.")

            obs = st.text_area("Observaciones de coordinación")

            cA, cR = st.columns(2)
            if cA.button("✅ Aprobar Permiso", use_container_width=True, type="primary"):
                supabase.table("solicitudes").update({"estado": "Aceptada", "observaciones": obs}).eq("id", sol_id).execute()
                enviar_correo(solicitud.get("correo", ""), "aceptada", obs)
                st.success("Aprobado.")
                st.rerun()
            if cR.button("❌ Rechazar Permiso", use_container_width=True):
                supabase.table("solicitudes").update({"estado": "Rechazada", "observaciones": obs}).eq("id", sol_id).execute()
                enviar_correo(solicitud.get("correo", ""), "rechazada", obs)
                st.success("Rechazado.")
                st.rerun()
    else:
        st.success("No hay solicitudes pendientes.")

    st.markdown("---")
    st.subheader("📚 Base de Datos y Exportación")
    
    excel_bytes, docentes_df = crear_excel(solicitudes)
    
    tab1, tab2 = st.tabs(["Historial Completo", "Resumen para Nómina"])
    with tab1: st.dataframe(pd.DataFrame(solicitudes), hide_index=True)
    with tab2: st.dataframe(docentes_df, hide_index=True)

    st.download_button(
        "⬇️ Descargar Reporte Excel",
        data=excel_bytes,
        file_name="reporte_go_hrms.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
except Exception as e:
    st.error(f"Error de base de datos: {e}")