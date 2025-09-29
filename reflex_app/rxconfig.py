import reflex as rx

class SeismicConfig(rx.Config):
    app_name: str = "seismic_aiagent"
    frontend_port: int = 3000
    backend_port: int = 8000
    # Directorio público para assets estáticos si aplica
    # static_dir = "assets"

config = SeismicConfig()