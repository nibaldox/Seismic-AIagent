import reflex as rx
from reflex_app.components.layout import app_shell
from reflex_app.components.charts import placeholder_chart
from reflex_app.components.forms import section


def page() -> rx.Component:
    return app_shell(
        rx.vstack(
            rx.heading("📈 Histogramas Gecko"),
            section(
                "Variables",
                rx.hstack(
                    rx.input(placeholder="CSV de histogramas"),
                    rx.select(["1 min", "5 min", "1 h", "1 día"], placeholder="Remuestreo"),
                    rx.select(["mean", "max", "min", "sum"], placeholder="Agregación"),
                    rx.button("Aplicar"),
                    spacing="3",
                ),
            ),
            placeholder_chart("Series temporales"),
            spacing="4",
        )
    )
