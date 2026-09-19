import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client

# =========================
# CONFIGURACIÓN PRINCIPAL
# =========================
st.set_page_config(page_title="Go HRMS", page_icon="🎓", layout="wide")

load_dotenv()
supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)

# =========================
# ESTADO DE SESIÓN SEGURO
# =========================
if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_rol" not in st.session_state:
    st.session_state.usuario_rol = None
if "usuario_email" not in st.session_state:
    st.session_state.usuario_email = None

# =========================
# PANTALLA DE LOGIN
# =========================
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🎓 GO HRMS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Sistema de Gestión Integral</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### Iniciar Sesión")
            email = st.text_input("Correo institucional")
            password = st.text_input("Contraseña", type="password")
            
            rol_simulado = st.radio("Entrar como:", ["Docente", "Administrativo"])
            
            if st.button("Ingresar", use_container_width=True, type="primary"):
                if email and password:
                    st.session_state.logueado = True
                    st.session_state.usuario_email = email
                    st.session_state.usuario_rol = rol_simulado
                    st.rerun() 
                else:
                    st.error("⚠️ Ingresa cualquier correo y contraseña para continuar.")

# =========================
# ENRUTADOR DINÁMICO
# =========================
if not st.session_state.logueado:
    mostrar_login()
else:
    # Botón global en la barra lateral
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.usuario_email}**")
        st.caption(f"Rol: {st.session_state.usuario_rol}")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.logueado = False
            st.session_state.usuario_rol = None
            st.session_state.usuario_email = None
            st.rerun()
        st.divider()
    
    # Asignación de páginas apuntando a la carpeta "vistas/"
    paginas = []
    if st.session_state.usuario_rol == "Docente":
        paginas = [
            st.Page("vistas/1_Permisos.py", title="Mis Permisos", icon="✈️"),
        ]
    elif st.session_state.usuario_rol == "Administrativo":
        paginas = [
            st.Page("vistas/2_Panel_Administrativo.py", title="Gestión de Permisos", icon="📋"),
        ]

    # Ejecutar la navegación
    if paginas:
        pg = st.navigation(paginas)
        pg.run()