import reflex as rx
from ..components.layout import app_shell
from ..components.forms import section


def page() -> rx.Component:
    return app_shell(
        rx.vstack(
            rx.heading("🌍 Location 1D"),
            section(
                "Parámetros de red",
                rx.text("(Placeholder) Configurar estaciones, Vp/Vs, grilla"),
            ),
            section(
                "Localización",
                rx.button("Localizar Evento"),
            ),
            spacing="4",
        )
    )
