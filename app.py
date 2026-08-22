import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)
st.title("Sistema de Permisos Docentes")                
tipo_acceso = st.selectbox(
    "Seleccione el tipo de acceso",
    ["Docente", "Administrativo"]
)

if tipo_acceso == "Docente":
    st.subheader("Solicitud de permiso de ausencia")
    nombre = st.text_input("Nombre del docente")
    correo = st.text_input("Correo electrónico")
    fecha = st.date_input("Fecha de la ausencia")
    hora_inicio = st.time_input("Hora de inicio")
    hora_fin = st.time_input("Hora de finalización")
    motivo = st.text_area("Motivo de la ausencia")
    enviar = st.button("Enviar solicitud")
    if enviar:
        try:
            datos = {
                "nombre": nombre,
                "correo": correo,
                "fecha": fecha.isoformat(),
                "hora_inicio": hora_inicio.isoformat(),
                "hora_fin": hora_fin.isoformat(),
                "motivo": motivo
            }

            supabase.table("solicitudes").insert(
                datos, returning="minimal"
            ).execute()

            st.success("✅ Solicitud enviada correctamente")
        except Exception as e:
            st.error(f"Error al enviar la solicitud: {e}")
elif tipo_acceso == "Administrativo":
    st.subheader("Panel Administrativo")

    try:
        respuesta = supabase.table("solicitudes").select("*").execute()
        solicitudes = respuesta.data

        if solicitudes:
            st.dataframe(solicitudes, width="stretch")

            ids = [solicitud["id"] for solicitud in solicitudes]
            solicitud_id = st.selectbox("Seleccione la solicitud", ids)

            observaciones = st.text_area("Observaciones")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Aceptar"):
                    supabase.table("solicitudes").update({
                        "estado": "Aceptada",
                        "observaciones": observaciones
                    }).eq("id", solicitud_id).execute()

                    st.success("Solicitud aceptada")
                    st.rerun()

            with col2:
                if st.button("❌ Rechazar"):
                    supabase.table("solicitudes").update({
                        "estado": "Rechazada",
                        "observaciones": observaciones
                    }).eq("id", solicitud_id).execute()

                    st.success("Solicitud rechazada")
                    st.rerun()

        else:
            st.info("No hay solicitudes registradas.")

    except Exception as e:
        st.error(f"Error al cargar las solicitudes: {e}")