import reflex as rx


class SeismicConfig(rx.Config):
    """Configuración de Reflex para la app."""
    pass


config = SeismicConfig(
    app_name="reflex_app",  # Debe coincidir con el paquete que contiene app.py
    frontend_port=3000,
    backend_port=8000,
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    # static_dir="assets",  # opcional
)
