import reflex as rx

"""Wrappers de gráficos para Reflex con integración opcional a Buridan UI.

Esta capa permite cambiar el proveedor de gráficos sin tocar las páginas.
Si Buridan UI está disponible, se puede renderizar con sus componentes; si no,
se muestra un placeholder amigable.
"""

try:  # Detección opcional de Buridan UI (ajusta el import según la doc oficial)
    # Ejemplos posibles (uno de ellos podría ser válido según la lib):
    # from buridan_ui import charts as bu
    # from buridan_ui.charts import LineChart as BuLine, AreaChart as BuArea
    bu = None  # placeholder hasta definir API exacta
    HAS_BURIDAN = False
except Exception:
    bu = None
    HAS_BURIDAN = False


def placeholder_chart(title: str, note: str | None = None) -> rx.Component:
    return rx.box(
        rx.heading(title, size="4"),
        rx.box(
            (note or "Chart placeholder"),
            border="1px dashed #444",
            padding="24px",
            border_radius="8px",
        ),
        width="100%",
    )


def line_series_chart(*, title: str, categories: list[str], series: list[tuple[str, list[float]]]) -> rx.Component:
    """Grafica una o más series (línea) sobre categorías (x).

    Si Buridan UI estuviera disponible, aquí se mapearían los datos a su API.
    Por ahora, muestra un placeholder con una breve nota.
    """
    note = "Buridan UI no instalado. Instálalo y conectamos aquí."
    return placeholder_chart(title, note=note)


def area_series_chart(*, title: str, categories: list[str], series: list[tuple[str, list[float]]]) -> rx.Component:
    """Equivalente de área; placeholder si Buridan no está disponible."""
    note = "Buridan UI no instalado. Área chart placeholder."
    return placeholder_chart(title, note=note)
