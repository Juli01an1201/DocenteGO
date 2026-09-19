import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client

# =========================
# CONFIGURACIÓN PRINCIPAL
# =========================
st.set_page_config(page_title="Go HRMS", page_icon="🎓", layout="wide")

load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# =========================
# ESTADO DE SESIÓN
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
            
            # Para simular temporalmente los roles sin modificar aún Supabase
            rol_simulado = st.radio("Entrar como:", ["Docente", "Administrativo"])
            
            if st.button("Ingresar", use_container_width=True):
                # Aquí conectaremos supabase.auth.sign_in_with_password() más adelante
                # Por ahora, forzamos el login exitoso para probar la navegación
                if email and password:
                    st.session_state.logueado = True
                    st.session_state.usuario_email = email
                    st.session_state.usuario_rol = rol_simulado
                    st.success("Acceso concedido")
                    st.rerun() # Recarga la app para aplicar el enrutamiento
                else:
                    st.error("Ingresa correo y contraseña.")

# =========================
# ENRUTADOR DINÁMICO
# =========================
if not st.session_state.logueado:
    mostrar_login()
else:
    # Definimos las páginas disponibles según el rol
    paginas_disponibles = []
    
    # Todos los usuarios pueden ver la opción de cerrar sesión
    def cerrar_sesion():
        st.session_state.logueado = False
        st.session_state.usuario_rol = None
        st.session_state.usuario_email = None
        st.rerun()

    # Botón global en la barra lateral
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.usuario_email}**")
        st.caption(f"Rol: {st.session_state.usuario_rol}")
        if st.button("Cerrar Sesión", use_container_width=True):
            cerrar_sesion()
        st.divider()
    
    # Asignación de páginas según el rol
    if st.session_state.usuario_rol == "Docente":
        paginas_disponibles = [
            st.Page("pages/1_Permisos.py", title="Mis Permisos", icon="✈️"),
            st.Page("pages/3_Evaluacion_360.py", title="Evaluación 360", icon="📊"),
        ]
    elif st.session_state.usuario_rol == "Administrativo":
        paginas_disponibles = [
            st.Page("pages/2_Panel_Administrativo.py", title="Gestión de Permisos", icon="📋"),
            st.Page("pages/3_Evaluacion_360.py", title="Resultados 360", icon="📈"),
        ]

    # Ejecutar la navegación
    if paginas_disponibles:
        pg = st.navigation(paginas_disponibles)
        pg.run()