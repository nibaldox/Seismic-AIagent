import reflex as rx
from ..components.layout import app_shell
from ..components.charts import placeholder_chart
from ..components.forms import section


def page() -> rx.Component:
    return app_shell(
        rx.vstack(
            rx.heading("🔍 Spectrum Analysis"),
            section(
                "Parámetros",
                rx.hstack(
                    rx.select(["Spectrogram", "FFT", "PSD"], placeholder="Tipo"),
                    rx.input(placeholder="Ventana (s)"),
                    rx.input(placeholder="Overlap (%)"),
                    rx.button("Calcular"),
                    spacing="3",
                ),
            ),
            placeholder_chart("Spectrum"),
            spacing="4",
        )
    )
