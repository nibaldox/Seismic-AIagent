import base64
from pathlib import Path
from typing import Optional, Any

import reflex as rx
from ..components.layout import app_shell
from ..components.forms import section

from src.core.data_reader import DataReader
from src.visualization.waveform_plots import create_waveform_plot


class WaveformState(rx.State):
    """Estado y acciones para la vista de Waveform."""

    file_path: str = ""
    filter_type: str = "none"  # none|bandpass|highpass|lowpass
    freqmin: str = "1.0"
    freqmax: str = "10.0"
    unit: str = "Raw"  # Raw|m/s²|g
    amplitude_scale: str = "Auto"  # Auto|Global|Normalized
    window_start: str = "0"
    window_end: str = "0"

    plot_png_b64: str = ""
    data_uri: str = ""
    summary: str = ""
    error: Optional[str] = None

    def _to_float(self, s: str, default: float) -> float:
        try:
            return float(s)
        except Exception:
            return default

    # Handlers para on_change (evita depender de setters dinámicos)
    def set_file_path(self, v: str):
        self.file_path = v

    def set_filter_type(self, v: str):
        self.filter_type = v

    def set_freqmin(self, v: str):
        self.freqmin = v

    def set_freqmax(self, v: str):
        self.freqmax = v

    def set_unit(self, v: str):
        self.unit = v

    def set_amplitude_scale(self, v: str):
        self.amplitude_scale = v

    def set_window_start(self, v: str):
        self.window_start = v

    def set_window_end(self, v: str):
        self.window_end = v

    def generate(self):
        """Genera la figura a partir del archivo y parámetros actuales."""
        self.error = None
        self.plot_png_b64 = ""
        self.summary = ""
        self.data_uri = ""

        path = self.file_path.strip()
        if not path:
            self.error = "Por favor, indique la ruta del archivo (MiniSEED/SAC/SEG2)."
            return

        try:
            reader = DataReader()
            loaded_list = reader.load_files([Path(path)])
            loaded = loaded_list[0]
            stream = loaded.stream
            # Calcular ventana por defecto si end==0
            try:
                first_trace = stream[0]
                t_end = float(first_trace.times("relative")[-1]) if first_trace.stats.npts > 0 else 0.0
            except Exception:
                t_end = 0.0

            w_start = self._to_float(self.window_start, 0.0)
            w_end = self._to_float(self.window_end, t_end)
            if w_end <= w_start:
                w_end = max(w_start + 1.0, t_end or 1.0)

            fmin = self._to_float(self.freqmin, 1.0)
            fmax = self._to_float(self.freqmax, 10.0)

            fig = create_waveform_plot(
                streams=stream,
                time_window=(int(w_start), int(w_end)),
                unit=self.unit,
                filter_type=self.filter_type,
                freqmin=fmin,
                freqmax=fmax,
                amplitude_scale=self.amplitude_scale,
                title=f"Waveforms · {Path(path).name}",
            )

            # Exportar a PNG (requiere kaleido)
            png_bytes = fig.to_image(format="png", scale=2)
            self.plot_png_b64 = base64.b64encode(png_bytes).decode("ascii")
            self.data_uri = f"data:image/png;base64,{self.plot_png_b64}"
            self.summary = loaded.summary
        except Exception as exc:
            self.error = f"No se pudo generar la figura: {exc}"

    # Upload handler (Reflex): guarda archivo y setea la ruta
    def save_upload(self, files: Any = None):
        try:
            upload_dir = rx.get_upload_dir()
            for f in (files or []):
                save_path = upload_dir / f.filename
                f.save(save_path)
                # Usa el primero subido
                self.file_path = str(save_path)
                break
        except Exception as exc:
            self.error = f"No se pudo guardar el archivo subido: {exc}"


def controls() -> rx.Component:
    return section(
        "Archivo y filtros",
        rx.hstack(
            rx.upload(
                id="wf_upload",
                multiple=False,
                accept={"application/octet-stream": [".mseed", ".sac", ".seg2", ".sg2"]},
                max_files=1,
            ),
            rx.button(
                "Subir archivo",
                on_click=WaveformState.save_upload(rx.upload_files("wf_upload")),  # pyright: ignore[reportArgumentType]
            ),
            spacing="3",
        ),
        rx.input(
            value=WaveformState.file_path,
            on_change=WaveformState.set_file_path,  # pyright: ignore[reportArgumentType]
            placeholder="Ruta del archivo (ej: data/AC-1-SUR/Data/02-05-25/00/sample.mseed)",
            width="100%",
        ),
        rx.hstack(
            rx.select(
                ["none", "bandpass", "highpass", "lowpass"],
                value=WaveformState.filter_type,
                on_change=WaveformState.set_filter_type,  # pyright: ignore[reportArgumentType]
            ),
            rx.input(placeholder="freqmin", value=WaveformState.freqmin, on_change=WaveformState.set_freqmin, width="120px"),  # pyright: ignore[reportArgumentType]
            rx.input(placeholder="freqmax", value=WaveformState.freqmax, on_change=WaveformState.set_freqmax, width="120px"),  # pyright: ignore[reportArgumentType]
            rx.select(["Raw", "m/s²", "g"], value=WaveformState.unit, on_change=WaveformState.set_unit),  # pyright: ignore[reportArgumentType]
            rx.select(["Auto", "Global", "Normalized"], value=WaveformState.amplitude_scale, on_change=WaveformState.set_amplitude_scale),  # pyright: ignore[reportArgumentType]
            spacing="3",
        ),
        rx.hstack(
            rx.input(placeholder="t0 (s)", value=WaveformState.window_start, on_change=WaveformState.set_window_start, width="120px"),  # pyright: ignore[reportArgumentType]
            rx.input(placeholder="t1 (s)", value=WaveformState.window_end, on_change=WaveformState.set_window_end, width="120px"),  # pyright: ignore[reportArgumentType]
            rx.button("Generar", on_click=WaveformState.generate),  # pyright: ignore[reportArgumentType]
            spacing="3",
        ),
    )


def plot_view() -> rx.Component:
    return rx.cond(
        WaveformState.data_uri == "",
        rx.box("Genera el gráfico para visualizar la señal."),
        rx.image(src=WaveformState.data_uri, width="100%"),
    )


def page() -> rx.Component:
    return app_shell(
        rx.vstack(
            rx.heading("📊 Waveform Viewer"),
            controls(),
            rx.cond(WaveformState.error != None, rx.callout(WaveformState.error, color="red"), rx.box()),
            rx.cond(WaveformState.summary != "", rx.code(WaveformState.summary), rx.box()),
            plot_view(),
            spacing="4",
        )
    )
