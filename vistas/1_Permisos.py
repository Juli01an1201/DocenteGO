import streamlit as st
import os
import uuid
import re
from dotenv import load_dotenv
from supabase import create_client

# 1. Seguridad
if "logueado" not in st.session_state or not st.session_state.logueado:
    st.warning("Debes iniciar sesión para ver esta página.")
    st.stop()

# 2. Conexión a BD Robusta
load_dotenv()
try:
    supabase_url = st.secrets["SUPABASE_URL"]
except Exception:
    supabase_url = os.getenv("SUPABASE_URL")

try:
    supabase_key = st.secrets["SUPABASE_KEY"]
except Exception:
    supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    st.error("🚨 Error crítico: No se encontraron las credenciales de Supabase.")
    st.stop()

supabase = create_client(supabase_url, supabase_key)
BUCKET_EVIDENCIAS = "evidencias"

def nombre_archivo_seguro(nombre):
    nombre = os.path.basename(nombre or "evidencia")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nombre)

def subir_evidencia(archivo):
    if archivo is None:
        return None
    if archivo.size > 10 * 1024 * 1024:
        raise ValueError("La evidencia supera el límite de 10 MB.")
    
    nombre_limpio = nombre_archivo_seguro(archivo.name)
    ruta = f"solicitudes/{uuid.uuid4().hex}_{nombre_limpio}"
    
    supabase.storage.from_(BUCKET_EVIDENCIAS).upload(
        path=ruta,
        file=archivo.getvalue(),
        file_options={"content-type": archivo.type or "application/octet-stream"}
    )
    return ruta

# 3. Interfaz de Usuario
st.title("Nueva solicitud de permiso")
st.write(f"Solicitando a nombre de: **{st.session_state.usuario_email}**")

st.markdown('<div class="section-title">Detalles del permiso</div>', unsafe_allow_html=True)

fecha = st.date_input("Fecha de la ausencia")

col1, col2 = st.columns(2)
with col1:
    hora_inicio = st.time_input("Hora de inicio")
with col2:
    hora_fin = st.time_input("Hora de finalización")

tipo_novedad = st.selectbox(
    "Clasificación de la solicitud (Nómina)",
    [
        "Permiso remunerado (Cita médica, diligencia)",
        "Permiso NO remunerado (Asuntos personales)",
        "Incapacidad médica (Con soporte)",
        "Calamidad doméstica",
        "Licencia (Maternidad/Paternidad/Luto)"
    ]
)

motivo = st.text_area("Descripción detallada del motivo")
evidencia = st.file_uploader("Subir evidencia (PDF, JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])

if st.button("Enviar solicitud", type="primary", use_container_width=True):
    if not motivo:
        st.warning("⚠️ Debes escribir un motivo.")
    else:
        try:
            ruta_evidencia = subir_evidencia(evidencia)
            
            datos = {
                "nombre": st.session_state.usuario_email.split("@")[0].capitalize(),
                "correo": st.session_state.usuario_email,
                "fecha": str(fecha),
                "hora_inicio": str(hora_inicio),
                "hora_fin": str(hora_fin),
                "tipo_novedad": tipo_novedad,
                "motivo": motivo.strip(),
                "estado": "Pendiente",
                "evidencia_url": ruta_evidencia,
            }
            
            supabase.table("solicitudes").insert(datos).execute()
            st.success("✅ Solicitud enviada correctamente. El coordinador ha sido notificado.")
        except Exception as e:
            st.error(f"Error al enviar la solicitud: {e}")