import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(
    page_title="DocenteGO",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

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
        placeholder="admin@colegio.com"
    )

    password_admin = st.text_input(
        "Contraseña",
        type="password"
    )

    if st.button("Iniciar sesión", use_container_width=True):
        try:
            respuesta = supabase.auth.sign_in_with_password({
                "email": email_admin,
                "password": password_admin
            })

            if respuesta.user:
                st.session_state.admin_logueado = True
                st.session_state.admin_email = email_admin
                st.success("Inicio de sesión correcto")
                st.rerun()

        except Exception:
            st.error("Correo o contraseña incorrectos")

def cerrar_sesion_admin():
    supabase.auth.sign_out()
    st.session_state.admin_logueado = False
    st.session_state.admin_email = None
    st.rerun()

# =========================
# ESTILO MODERNO
# =========================
st.markdown("""
<style>

/* Fondo general */
.stApp {
    background:
        radial-gradient(circle at 90% 5%, rgba(16,185,129,.10), transparent 22%),
        #f7f9fc;
}

/* Ocultar elementos de Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent;}

/* Contenedor principal */
.block-container {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,.96);
    border-right: 1px solid #e8edf3;
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

/* Títulos */
h1, h2, h3 {
    color: #0f172a;
    font-family: Inter, Arial, sans-serif;
}

h1 {
    font-weight: 800 !important;
    letter-spacing: -1px;
}

/* Inputs */
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

/* Botones */
.stButton > button,
.stFormSubmitButton > button {
    width: 100%;
    border-radius: 12px;
    border: none;
    min-height: 48px;
    font-weight: 700;
    font-size: 16px;
    background: linear-gradient(90deg, #0ea47a, #12b7aa);
    color: white;
    box-shadow: 0 8px 20px rgba(16,163,127,.18);
    transition: .2s ease;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 12px 25px rgba(16,163,127,.25);
    color: white;
}

/* Tarjetas */
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

</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("""
        <div class="logo-title">🎓 Docente<span>GO</span></div>
        <div class="muted">Gestión de permisos</div>
        <br>
    """, unsafe_allow_html=True)

    tipo_acceso = st.selectbox(
        "Tipo de acceso",
        ["Docente", "Administrativo"]
    )

    st.markdown("---")

    if tipo_acceso == "Docente":
        st.markdown("### ✈️ Nueva solicitud")
        st.caption("Envía una solicitud de permiso.")
    else:
        st.markdown("### 📋 Panel administrativo")
        st.caption("Gestiona las solicitudes recibidas.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("DocenteGO © 2026")

# =========================
# DOCENTE
# =========================
if tipo_acceso == "Docente":

    st.markdown("""
        <div class="hero-card">
            <span class="badge">● Nueva solicitud</span>
            <h1 style="margin-bottom:5px;">Hola 👋</h1>
            <p class="muted" style="font-size:16px;">
                Completa los datos para enviar tu solicitud de permiso.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">👤 1. Datos del docente</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Información de quien realiza la solicitud</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input(
            "Nombre completo",
            placeholder="Ej. Julián Cortés"
        )

    with col2:
        correo = st.text_input(
            "Correo electrónico",
            placeholder="correo@ejemplo.com"
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">📅 2. Detalles del permiso</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Selecciona la fecha, horario y motivo</div>',
                unsafe_allow_html=True)

    fecha = st.date_input("Fecha de la ausencia")

    col3, col4 = st.columns(2)

    with col3:
        hora_inicio = st.time_input("Hora de inicio")

    with col4:
        hora_fin = st.time_input("Hora de finalización")

    motivo = st.text_area(
        "Motivo de la ausencia",
        placeholder="Explica brevemente el motivo de la solicitud...",
        height=120
    )

    enviar = st.button("✈️ Enviar solicitud", use_container_width=True)

    if enviar:
        if not nombre or not correo or not motivo:
            st.warning("⚠️ Completa todos los campos antes de enviar.")
        else:
            try:
                datos = {
                    "nombre": nombre,
                    "correo": correo,
                    "fecha": str(fecha),
                    "hora_inicio": str(hora_inicio),
                    "hora_fin": str(hora_fin),
                    "motivo": motivo,
                    "estado": "Pendiente"
                }

                supabase.table("solicitudes").insert(datos).execute()

                st.markdown("""
                    <div class="success-box">
                        ✅ Solicitud enviada correctamente<br>
                        <span style="font-weight:400;">
                        Tu solicitud ha sido registrada exitosamente.
                        </span>
                    </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error al enviar la solicitud: {e}")

# =========================
# ADMINISTRATIVO
# =========================
else:
    if not st.session_state.admin_logueado:
        login_admin()
        st.stop()

    if st.button("Cerrar sesión"):
        cerrar_sesion_admin()
    st.markdown("""
        <div class="hero-card">
            <span class="badge">Panel administrativo</span>
            <h1 style="margin-bottom:5px;">Gestión de solicitudes</h1>
            <p class="muted" style="font-size:16px;">
                Revisa, acepta o rechaza los permisos enviados.
            </p>
        </div>
    """, unsafe_allow_html=True)

    try:
        respuesta = (
            supabase
            .table("solicitudes")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        solicitudes = respuesta.data

        if not solicitudes:
            st.info("Todavía no hay solicitudes.")
        else:

            pendientes = [
                s for s in solicitudes
                if s.get("estado") in [None, "", "Pendiente"]
            ]

            st.markdown(
                f"### 📥 Solicitudes pendientes: {len(pendientes)}"
            )

            opciones = {
                f"#{s.get('id')} · {s.get('nombre', 'Sin nombre')} · {s.get('fecha', '')}":
                s for s in pendientes
            }

            if opciones:
                seleccion = st.selectbox(
                    "Selecciona una solicitud",
                    list(opciones.keys())
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

                observaciones = st.text_area(
                    "Observaciones",
                    placeholder="Escribe una observación opcional..."
                )

                colAceptar, colRechazar = st.columns(2)

                with colAceptar:
                    if st.button(
                        "✅ Aceptar",
                        use_container_width=True
                    ):
                        supabase.table("solicitudes").update({
                            "estado": "Aceptada",
                            "observaciones": observaciones
                        }).eq("id", solicitud_id).execute()

                        st.success("Solicitud aceptada")
                        st.rerun()

                with colRechazar:
                    if st.button(
                        "❌ Rechazar",
                        use_container_width=True
                    ):
                        supabase.table("solicitudes").update({
                            "estado": "Rechazada",
                            "observaciones": observaciones
                        }).eq("id", solicitud_id).execute()

                        st.success("Solicitud rechazada")
                        st.rerun()

            else:
                st.success("🎉 No hay solicitudes pendientes.")

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("### 📚 Historial")

            st.dataframe(
                solicitudes,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(f"Error al cargar las solicitudes: {e}")
