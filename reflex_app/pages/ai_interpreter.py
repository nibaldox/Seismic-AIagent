import reflex as rx
from reflex_app.components.layout import app_shell
from reflex_app.components.forms import section
from reflex_app.components.charts import placeholder_chart


def page() -> rx.Component:
    return app_shell(
        rx.vstack(
            rx.heading("🤖 AI Interpreter"),
            section(
                "Modo",
                rx.radio(items=["Análisis Primario", "Análisis Espectral", "Telemetría", "Equipo (coordinado)"]),
            ),
            section(
                "Contexto",
                rx.textarea(placeholder="Notas y contexto para los agentes...", width="100%"),
                rx.button("Ejecutar Análisis IA"),
            ),
            placeholder_chart("Resultados IA"),
            spacing="4",
        )
    )
