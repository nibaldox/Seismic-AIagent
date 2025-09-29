import reflex as rx
from ..components.layout import app_shell
from ..components.charts import placeholder_chart
from ..components.forms import section


def page() -> rx.Component:
    return app_shell(
        rx.vstack(
            rx.heading("📊 Waveform Viewer"),
            section(
                "Archivo y filtros",
                rx.hstack(
                    rx.input(placeholder="Selecciona archivo..."),
                    rx.select(["Band-pass", "High-pass", "Low-pass"], placeholder="Filtro"),
                    rx.button("Aplicar"),
                    spacing="3",
                ),
            ),
            placeholder_chart("Waveform"),
            spacing="4",
        )
    )
