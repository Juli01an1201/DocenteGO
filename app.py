import streamlit as st
import os
import smtplib
import re
import uuid
from io import BytesIO
from email.mime.text import MIMEText

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(
    page_title="DocenteGO",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")

if not supabase_url or not supabase_key:
    st.error("Faltan las variables SUPABASE_URL o SUPABASE_KEY.")
    st.stop()

supabase = create_client(supabase_url, supabase_key)
BUCKET_EVIDENCIAS = "evidencias"


def enviar_correo(destinatario, estado, observaciones=""):
    """Envía al docente el resultado de la solicitud."""
    if not destinatario or not email_user or not email_password:
        return

    asunto = f"DocenteGO - Solicitud {estado}"
    cuerpo = f"""
Hola,

Tu solicitud ha sido {estado}.

Observaciones: {observaciones if observaciones else "Sin observaciones."}

DocenteGO
"""

    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = asunto
    mensaje["From"] = email_user
    mensaje["To"] = destinatario

    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()
        servidor.login(email_user, email_password)
        servidor.send_message(mensaje)


def nombre_archivo_seguro(nombre):
    """Limpia el nombre del archivo antes de subirlo a Storage."""
    nombre = os.path.basename(nombre or "evidencia")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nombre)


def subir_evidencia(archivo):
    """Sube una evidencia al bucket privado y devuelve su ruta."""
    if archivo is None:
        return None

    if archivo.size > 10 * 1024 * 1024:
        raise ValueError("La evidencia supera el límite de 10 MB.")

    nombre_limpio = nombre_archivo_seguro(archivo.name)
    ruta = f"solicitudes/{uuid.uuid4().hex}_{nombre_limpio}"

    supabase.storage.from_(BUCKET_EVIDENCIAS).upload(
        path=ruta,
        file=archivo.getvalue(),
        file_options={
            "content-type": archivo.type or "application/octet-stream",
            "upsert": "false",
        },
    )
    return ruta


def obtener_url_evidencia(ruta):
    """Crea una URL temporal de 10 minutos para una evidencia privada."""
    if not ruta:
        return None

    respuesta = (
        supabase.storage
        .from_(BUCKET_EVIDENCIAS)
        .create_signed_url(ruta, 600)
    )

    if isinstance(respuesta, dict):
        return (
            respuesta.get("signedURL")
            or respuesta.get("signedUrl")
            or respuesta.get("signed_url")
        )

    return getattr(respuesta, "signed_url", None)


def crear_excel(solicitudes):
    """Genera un Excel con solicitudes y resumen por docente."""
    columnas_solicitudes = [
        "id",
        "created_at",
        "nombre",
        "correo",
        "fecha",
        "hora_inicio",
        "hora_fin",
        "motivo",
        "estado",
        "observaciones",
        "evidencia_url",
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
        docentes = pd.DataFrame(
            columns=[
                "nombre",
                "correo",
                "total_solicitudes",
                "ultima_solicitud",
                "aceptadas",
                "rechazadas",
                "pendientes",
            ]
        )
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
# SESIÓN DE ADMINISTRADOR
# =========================
if "admin_logueado" not in st.session_state:
    st.session_state.admin_logueado = False

if "admin_email" not in st.session_state:
    st.session_state.admin_email = None


def login_admin():
    st.markdown("### 🔐 Acceso administrativo")

    email_admin = st.text_input(
        "Correo del administrador",
        placeholder="admin@colegio.com",
    )

    password_admin = st.text_input(
        "Contraseña",
        type="password",
    )

    if st.button("Iniciar sesión", use_container_width=True):
        try:
            respuesta = supabase.auth.sign_in_with_password({
                "email": email_admin,
                "password": password_admin,
            })

            if respuesta.user:
                st.session_state.admin_logueado = True
                st.session_state.admin_email = email_admin
                st.success("Inicio de sesión correcto")
                st.rerun()

        except Exception:
            st.error("Correo o contraseña incorrectos")


def cerrar_sesion_admin():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.admin_logueado = False
    st.session_state.admin_email = None
    st.rerun()


# =========================
# ESTILO MODERNO
# =========================
st.markdown(
    """
<style>
.stApp {
    background:
        radial-gradient(circle at 90% 5%, rgba(16,185,129,.10), transparent 22%),
        #f7f9fc;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent;}

.block-container {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

section[data-testid="stSidebar"] {
    background: rgba(255,255,255,.96);
    border-right: 1px solid #e8edf3;
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

h1, h2, h3 {
    color: #0f172a;
    font-family: Inter, Arial, sans-serif;
}

h1 {
    font-weight: 800 !important;
    letter-spacing: -1px;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
textarea {
    border-radius: 12px !important;
    border: 1px solid #dce3ec !important;
    background: white !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within {
    border-color: #10a37f !important;
    box-shadow: 0 0 0 3px rgba(16,163,127,.10) !important;
}

.stButton > button,
.stFormSubmitButton > button,
.stDownloadButton > button {
    width: 100%;
    border-radius: 12px;
    min-height: 48px;
    font-weight: 700;
    font-size: 16px;
}

.stButton > button,
.stFormSubmitButton > button {
    border: none;
    background: linear-gradient(90deg, #0ea47a, #12b7aa);
    color: white;
    box-shadow: 0 8px 20px rgba(16,163,127,.18);
}

.hero-card {
    padding: 26px 30px;
    border-radius: 22px;
    background: white;
    border: 1px solid #e7ebf0;
    box-shadow: 0 10px 35px rgba(15,23,42,.05);
    margin-bottom: 24px;
}

.section-title {
    font-size: 20px;
    font-weight: 750;
    color: #152238;
    margin-top: 10px;
    margin-bottom: 6px;
}

.section-subtitle {
    color: #718096;
    font-size: 14px;
    margin-bottom: 18px;
}

.badge {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 999px;
    background: #e8faf4;
    color: #078564;
    font-size: 13px;
    font-weight: 700;
}

.logo-title {
    font-size: 26px;
    font-weight: 850;
    color: #0f172a;
    margin-bottom: 2px;
}

.logo-title span {
    color: #0ca678;
}

.muted {
    color: #718096;
}

.success-box {
    background: linear-gradient(90deg,#ecfdf5,#f0fdfa);
    border: 1px solid #c8f3e4;
    padding: 18px 20px;
    border-radius: 16px;
    color: #08765d;
    font-weight: 650;
    margin-top: 15px;
}

hr {
    border: none;
    border-top: 1px solid #edf0f4;
    margin: 24px 0;
}

/* Mejor contraste exclusivamente en celulares */
@media (max-width: 768px) {
    .stApp,
    .stApp p,
    .stApp label,
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stWidgetLabel"] {
        color: #1f2937 !important;
    }

    .muted,
    .section-subtitle,
    [data-testid="stCaptionContainer"] {
        color: #4b5563 !important;
    }

    h1, h2, h3, h4,
    .section-title,
    .logo-title {
        color: #0f172a !important;
    }

    input,
    textarea,
    div[data-baseweb="select"] span {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    input::placeholder,
    textarea::placeholder {
        color: #6b7280 !important;
        -webkit-text-fill-color: #6b7280 !important;
        opacity: 1 !important;
    }

    .stButton > button,
    .stFormSubmitButton > button {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    .badge {
        color: #078564 !important;
    }

    .success-box {
        color: #08765d !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown(
        """
        <div class="logo-title">🎓 Docente<span>GO</span></div>
        <div class="muted">Gestión de permisos</div>
        <br>
        """,
        unsafe_allow_html=True,
    )

    tipo_acceso = st.selectbox(
        "Tipo de acceso",
        ["Docente", "Administrativo"],
    )

    st.markdown("---")

    if tipo_acceso == "Docente":
        st.markdown("### ✈️ Nueva solicitud")
        st.caption("Envía una solicitud de permiso y adjunta una evidencia.")
    else:
        st.markdown("### 📋 Panel administrativo")
        st.caption("Gestiona solicitudes, evidencias y registros.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("DocenteGO © 2026")

# =========================
# DOCENTE
# =========================
if tipo_acceso == "Docente":
    st.markdown(
        """
        <div class="hero-card">
            <span class="badge">● Nueva solicitud</span>
            <h1 style="margin-bottom:5px;">Hola 👋</h1>
            <p class="muted" style="font-size:16px;">
                Completa los datos para enviar tu solicitud de permiso.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">👤 1. Datos del docente</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">Información de quien realiza la solicitud</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input(
            "Nombre completo",
            placeholder="Ej. Julián Cortés",
        )

    with col2:
        correo = st.text_input(
            "Correo electrónico",
            placeholder="correo@ejemplo.com",
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">📅 2. Detalles del permiso</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">Selecciona la fecha, horario y motivo</div>',
        unsafe_allow_html=True,
    )

    fecha = st.date_input("Fecha de la ausencia")

    col3, col4 = st.columns(2)

    with col3:
        hora_inicio = st.time_input("Hora de inicio")

    with col4:
        hora_fin = st.time_input("Hora de finalización")

    motivo = st.text_area(
        "Motivo de la ausencia",
        placeholder="Explica brevemente el motivo de la solicitud...",
        height=120,
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">📎 3. Evidencia</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-subtitle">Puedes adjuntar un soporte. Máximo 10 MB.</div>',
        unsafe_allow_html=True,
    )

    evidencia = st.file_uploader(
        "Subir evidencia",
        type=["pdf", "png", "jpg", "jpeg", "doc", "docx"],
        help="Formatos permitidos: PDF, imagen, Word.",
    )

    enviar = st.button("✈️ Enviar solicitud", use_container_width=True)

    if enviar:
        if not nombre or not correo or not motivo:
            st.warning("⚠️ Completa todos los campos obligatorios antes de enviar.")
        elif hora_fin <= hora_inicio:
            st.warning("⚠️ La hora de finalización debe ser posterior a la hora de inicio.")
        else:
            try:
                ruta_evidencia = subir_evidencia(evidencia)

                datos = {
                    "nombre": nombre.strip(),
                    "correo": correo.strip(),
                    "fecha": str(fecha),
                    "hora_inicio": str(hora_inicio),
                    "hora_fin": str(hora_fin),
                    "motivo": motivo.strip(),
                    "estado": "Pendiente",
                    "evidencia_url": ruta_evidencia,
                }

                supabase.table("solicitudes").insert(datos).execute()

                st.markdown(
                    """
                    <div class="success-box">
                        ✅ Solicitud enviada correctamente<br>
                        <span style="font-weight:400;">
                        Tu solicitud y su evidencia han sido registradas.
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            except Exception as e:
                st.error(f"Error al enviar la solicitud: {e}")

# =========================
# ADMINISTRATIVO
# =========================
else:
    if not st.session_state.admin_logueado:
        login_admin()
        st.stop()

    col_sesion, col_usuario = st.columns([1, 3])
    with col_sesion:
        if st.button("Cerrar sesión"):
            cerrar_sesion_admin()
    with col_usuario:
        st.caption(f"Sesión: {st.session_state.admin_email}")

    st.markdown(
        """
        <div class="hero-card">
            <span class="badge">Panel administrativo</span>
            <h1 style="margin-bottom:5px;">Gestión de solicitudes</h1>
            <p class="muted" style="font-size:16px;">
                Revisa solicitudes, consulta evidencias y descarga el registro.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        respuesta = (
            supabase
            .table("solicitudes")
            .select("*")
            .order("id", desc=True)
            .execute()
        )
        solicitudes = respuesta.data or []

        total = len(solicitudes)
        aceptadas = sum(1 for s in solicitudes if s.get("estado") == "Aceptada")
        rechazadas = sum(1 for s in solicitudes if s.get("estado") == "Rechazada")
        pendientes = [
            s for s in solicitudes
            if s.get("estado") in [None, "", "Pendiente"]
        ]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", total)
        m2.metric("Pendientes", len(pendientes))
        m3.metric("Aceptadas", aceptadas)
        m4.metric("Rechazadas", rechazadas)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"### 📥 Solicitudes pendientes: {len(pendientes)}")

        opciones = {
            f"#{s.get('id')} · {s.get('nombre', 'Sin nombre')} · {s.get('fecha', '')}": s
            for s in pendientes
        }

        if opciones:
            seleccion = st.selectbox(
                "Selecciona una solicitud",
                list(opciones.keys()),
            )

            solicitud = opciones[seleccion]
            solicitud_id = solicitud.get("id")

            st.markdown("<hr>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 👤 Docente")
                st.write(solicitud.get("nombre", ""))

                st.markdown("#### ✉️ Correo")
                st.write(solicitud.get("correo", ""))

                st.markdown("#### 📅 Fecha")
                st.write(solicitud.get("fecha", ""))

            with col2:
                st.markdown("#### 🕐 Horario")
                st.write(
                    f"{solicitud.get('hora_inicio', '')} - "
                    f"{solicitud.get('hora_fin', '')}"
                )

                st.markdown("#### 📝 Motivo")
                st.write(solicitud.get("motivo", ""))

                st.markdown("#### 📎 Evidencia")
                ruta = solicitud.get("evidencia_url")
                if ruta:
                    try:
                        url = obtener_url_evidencia(ruta)
                        if url:
                            st.link_button(
                                "Abrir evidencia",
                                url,
                                use_container_width=True,
                            )
                        else:
                            st.warning("No se pudo generar el enlace temporal.")
                    except Exception as e:
                        st.warning(f"No se pudo abrir la evidencia: {e}")
                else:
                    st.caption("Sin evidencia adjunta.")

            observaciones = st.text_area(
                "Observaciones",
                placeholder="Escribe una observación opcional...",
            )

            col_aceptar, col_rechazar = st.columns(2)

            with col_aceptar:
                if st.button("✅ Aceptar", use_container_width=True):
                    supabase.table("solicitudes").update({
                        "estado": "Aceptada",
                        "observaciones": observaciones,
                    }).eq("id", solicitud_id).execute()

                    try:
                        enviar_correo(
                            solicitud.get("correo", ""),
                            "aceptada",
                            observaciones,
                        )
                    except Exception as e:
                        st.warning(f"Solicitud aceptada, pero el correo no pudo enviarse: {e}")

                    st.success("Solicitud aceptada")
                    st.rerun()

            with col_rechazar:
                if st.button("❌ Rechazar", use_container_width=True):
                    supabase.table("solicitudes").update({
                        "estado": "Rechazada",
                        "observaciones": observaciones,
                    }).eq("id", solicitud_id).execute()

                    try:
                        enviar_correo(
                            solicitud.get("correo", ""),
                            "rechazada",
                            observaciones,
                        )
                    except Exception as e:
                        st.warning(f"Solicitud rechazada, pero el correo no pudo enviarse: {e}")

                    st.success("Solicitud rechazada")
                    st.rerun()
        else:
            st.success("🎉 No hay solicitudes pendientes.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### 📚 Registro e historial")

        excel_bytes, docentes = crear_excel(solicitudes)

        tab_solicitudes, tab_docentes = st.tabs(
            ["Todas las solicitudes", "Docentes que han solicitado permiso"]
        )

        with tab_solicitudes:
            if solicitudes:
                columnas_visibles = [
                    "id",
                    "created_at",
                    "nombre",
                    "correo",
                    "fecha",
                    "hora_inicio",
                    "hora_fin",
                    "motivo",
                    "estado",
                    "observaciones",
                    "evidencia_url",
                ]
                historial = pd.DataFrame(solicitudes)
                columnas_presentes = [
                    c for c in columnas_visibles if c in historial.columns
                ]
                st.dataframe(
                    historial[columnas_presentes],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Todavía no hay solicitudes.")

        with tab_docentes:
            if docentes.empty:
                st.info("Todavía no hay docentes registrados.")
            else:
                st.dataframe(
                    docentes,
                    use_container_width=True,
                    hide_index=True,
                )

        st.download_button(
            "⬇️ Descargar registro en Excel",
            data=excel_bytes,
            file_name="registro_docentego.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"Error al cargar las solicitudes: {e}")
