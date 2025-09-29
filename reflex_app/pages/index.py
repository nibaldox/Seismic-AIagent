import reflex as rx
from reflex_app.components.layout import app_shell


def index() -> rx.Component:
    return app_shell(
        rx.vstack(
            rx.heading("Inicio"),
            rx.text("Bienvenido a la migración Reflex de Seismic AIagent"),
            rx.link("Ir a Waveform", href="/waveform"),
            spacing="3",
        )
    )
