import streamlit as st
import os
import smtplib
from io import BytesIO
from email.mime.text import MIMEText
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# =========================
# SEGURIDAD Y CONEXIÓN
# =========================
# 1. Verificar que el usuario tenga permiso para estar aquí
if "logueado" not in st.session_state or not st.session_state.logueado:
    st.warning("Debes iniciar sesión para ver esta página.")
    st.stop()

if st.session_state.usuario_rol != "Administrativo":
    st.error("Acceso denegado. Esta vista es exclusiva para el área administrativa.")
    st.stop()

# 2. Cargar variables de entorno y conectar
load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")
BUCKET_EVIDENCIAS = "evidencias"

# =========================
# FUNCIONES AUXILIARES
# =========================
def enviar_correo(destinatario, estado, observaciones=""):
    """Envía al docente el resultado de la solicitud."""
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
        st.warning(f"No se pudo enviar el correo de notificación: {e}")

def obtener_url_evidencia(ruta):
    """Crea una URL temporal de 10 minutos para una evidencia privada."""
    if not ruta:
        return None
    respuesta = supabase.storage.from_(BUCKET_EVIDENCIAS).create_signed_url(ruta, 600)
    if isinstance(respuesta, dict):
        return respuesta.get("signedURL") or respuesta.get("signedUrl") or respuesta.get("signed_url")
    return getattr(respuesta, "signed_url", None)

def crear_excel(solicitudes):
    """Genera un Excel con solicitudes y resumen por docente."""
    columnas_solicitudes = [
        "id", "created_at", "nombre", "correo", "fecha", 
        "hora_inicio", "hora_fin", "motivo", "estado", 
        "observaciones", "evidencia_url"
    ]

    df = pd.DataFrame(solicitudes)
    for columna in columnas_solicitudes:
        if columna not in df.columns:
            df[columna] = ""

    df = df[columnas_solicitudes].copy()

    if not df.empty:
        df["estado"] = df["estado"].fillna("Pendiente").replace("", "Pendiente")
        df["fecha"] = df["fecha"].astype(str)

    if df.empty:
        docentes = pd.DataFrame(columns=["nombre", "correo", "total_solicitudes", "ultima_solicitud", "aceptadas", "rechazadas", "pendientes"])
    else:
        base = df.copy()
        base["nombre"] = base["nombre"].fillna("Sin nombre")
        base["correo"] = base["correo"].fillna("")
        base["es_aceptada"] = (base["estado"] == "Aceptada").astype(int)
        base["es_rechazada"] = (base["estado"] == "Rechazada").astype(int)
        base["es_pendiente"] = (~base["estado"].isin(["Aceptada", "Rechazada"])).astype(int)

        docentes = (
            base.groupby(["nombre", "correo"], dropna=False)
            .agg(
                total_solicitudes=("id", "count"),
                ultima_solicitud=("fecha", "max"),
                aceptadas=("es_aceptada", "sum"),
                rechazadas=("es_rechazada", "sum"),
                pendientes=("es_pendiente", "sum"),
            )
            .reset_index()
            .sort_values(["ultima_solicitud", "nombre"], ascending=[False, True])
        )

    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Solicitudes", index=False)
        docentes.to_excel(writer, sheet_name="Docentes", index=False)
        # Formateo visual del Excel
        for hoja in writer.book.worksheets:
            hoja.freeze_panes = "A2"
            hoja.auto_filter.ref = hoja.dimensions
            for columna in hoja.columns:
                maximo = 0
                letra = columna[0].column_letter
                for celda in columna:
                    valor = "" if celda.value is None else str(celda.value)
                    maximo = max(maximo, min(len(valor), 60))
                hoja.column_dimensions[letra].width = max(12, maximo + 2)

    return salida.getvalue(), docentes

# =========================
# INTERFAZ DE USUARIO
# =========================
st.title("📋 Gestión de Solicitudes")
st.markdown("Revisa solicitudes, consulta evidencias y descarga el registro.")

try:
    # Obtener datos de Supabase
    respuesta = supabase.table("solicitudes").select("*").order("id", desc=True).execute()
    solicitudes = respuesta.data or []

    total = len(solicitudes)
    aceptadas = sum(1 for s in solicitudes if s.get("estado") == "Aceptada")
    rechazadas = sum(1 for s in solicitudes if s.get("estado") == "Rechazada")
    pendientes = [s for s in solicitudes if s.get("estado") in [None, "", "Pendiente"]]

    # Métricas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Solicitudes", total)
    m2.metric("Pendientes", len(pendientes))
    m3.metric("Aceptadas", aceptadas)
    m4.metric("Rechazadas", rechazadas)

    st.markdown("---")
    st.markdown(f"### 📥 Solicitudes pendientes: {len(pendientes)}")

    opciones = {f"#{s.get('id')} · {s.get('nombre', 'Sin nombre')} · {s.get('fecha', '')}": s for s in pendientes}

    if opciones:
        seleccion = st.selectbox("Selecciona una solicitud para gestionar", list(opciones.keys()))
        solicitud = opciones[seleccion]
        solicitud_id = solicitud.get("id")

        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**👤 Docente:** {solicitud.get('nombre', '')}")
                st.markdown(f"**✉️ Correo:** {solicitud.get('correo', '')}")
                st.markdown(f"**📅 Fecha:** {solicitud.get('fecha', '')}")
            with col2:
                st.markdown(f"**🕐 Horario:** {solicitud.get('hora_inicio', '')} - {solicitud.get('hora_fin', '')}")
                st.markdown(f"**📝 Motivo:** {solicitud.get('motivo', '')}")
                
                ruta = solicitud.get("evidencia_url")
                if ruta:
                    url = obtener_url_evidencia(ruta)
                    if url:
                        st.link_button("📎 Ver evidencia adjunta", url)
                    else:
                        st.warning("No se pudo generar el enlace de la evidencia.")
                else:
                    st.caption("Sin evidencia adjunta.")

            observaciones = st.text_area("Observaciones de coordinación (opcional)", placeholder="Motivo de rechazo o anotación...")

            col_aceptar, col_rechazar = st.columns(2)
            with col_aceptar:
                if st.button("✅ Aprobar Permiso", use_container_width=True, type="primary"):
                    supabase.table("solicitudes").update({"estado": "Aceptada", "observaciones": observaciones}).eq("id", solicitud_id).execute()
                    enviar_correo(solicitud.get("correo", ""), "aceptada", observaciones)
                    st.success("Permiso aprobado.")
                    st.rerun()

            with col_rechazar:
                if st.button("❌ Rechazar Permiso", use_container_width=True):
                    supabase.table("solicitudes").update({"estado": "Rechazada", "observaciones": observaciones}).eq("id", solicitud_id).execute()
                    enviar_correo(solicitud.get("correo", ""), "rechazada", observaciones)
                    st.success("Permiso rechazado.")
                    st.rerun()
    else:
        st.success("🎉 No hay solicitudes pendientes de revisión.")

    st.markdown("---")
    st.markdown("### 📚 Base de Datos y Exportación")

    excel_bytes, docentes = crear_excel(solicitudes)

    tab_solicitudes, tab_docentes = st.tabs(["Todas las solicitudes", "Resumen por Docente"])

    with tab_solicitudes:
        if solicitudes:
            st.dataframe(pd.DataFrame(solicitudes), use_container_width=True, hide_index=True)
        else:
            st.info("Todavía no hay solicitudes en el sistema.")

    with tab_docentes:
        if not docentes.empty:
            st.dataframe(docentes, use_container_width=True, hide_index=True)
        else:
            st.info("No hay información de docentes todavía.")

    st.download_button(
        label="⬇️ Descargar Reporte en Excel (.xlsx)",
        data=excel_bytes,
        file_name="reporte_novedades_go.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary"
    )

except Exception as e:
    st.error(f"Error en la conexión con la base de datos: {e}")