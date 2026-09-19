import streamlit as st
import os
import uuid
import re
from supabase import create_client

# Nos aseguramos de que Supabase esté conectado (Streamlit recarga por página)
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# =========================
# SEGURIDAD Y CONEXIÓN
# =========================
# 1. Verificar que el usuario tenga permiso para estar aquí
if not st.session_state.get("logueado", False):
    st.warning("🔒 Debes iniciar sesión desde la página principal para ver este módulo.")
    st.stop()

# Aquí pegas tus funciones específicas de esta página (subir_evidencia, etc.)
def nombre_archivo_seguro(nombre):
    nombre = os.path.basename(nombre or "evidencia")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nombre)

# ... (pega aquí la función subir_evidencia) ...

st.title("✈️ Nueva solicitud de permiso")
st.write(f"Solicitando a nombre de: **{st.session_state.usuario_email}**") # Usamos el email de la sesión

st.markdown('<div class="section-title">📅 Detalles del permiso</div>', unsafe_allow_html=True)
fecha = st.date_input("Fecha de la ausencia")

col1, col2 = st.columns(2)
with col1:
    hora_inicio = st.time_input("Hora de inicio")
with col2:
    hora_fin = st.time_input("Hora de finalización")

motivo = st.text_area("Motivo de la ausencia")

evidencia = st.file_uploader("Subir evidencia", type=["pdf", "png", "jpg"])

if st.button("✈️ Enviar solicitud", type="primary", use_container_width=True):
    # Lógica de inserción a Supabase (igual a la que ya tenías)
    st.success("Solicitud enviada correctamente (Lógica por implementar).")