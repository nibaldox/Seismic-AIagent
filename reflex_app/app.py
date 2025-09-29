import reflex as rx


class AppState(rx.State):
    """Estado global (reactivo)."""

    theme: str = "dark"


# Registro de páginas (imports relativos dentro del paquete)
from .pages import (  # noqa: E402
    index,
    waveform,
    spectrum,
    histograms,
    ai_interpreter,
    location_1d,
)


app = rx.App(state=AppState)

# Rutas principales
app.add_page(index.index, route="/", title="Inicio")
app.add_page(waveform.page, route="/waveform", title="Waveform Viewer")
app.add_page(spectrum.page, route="/spectrum", title="Spectrum Analysis")
app.add_page(histograms.page, route="/histograms", title="Histogramas Gecko")
app.add_page(ai_interpreter.page, route="/ai_interpreter", title="AI Interpreter")
app.add_page(location_1d.page, route="/location_1d", title="Location 1D")
