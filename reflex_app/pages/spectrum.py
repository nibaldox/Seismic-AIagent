import base64
from pathlib import Path
from typing import Optional, Any, Dict

import reflex as rx
from ..components.layout import app_shell
from ..components.forms import section

from src.core.data_reader import DataReader
from src.visualization.spectrum_plots import (
    create_spectrogram,
    create_fft_plot,
    create_psd_plot,
)
from src.ai_agent.seismic_interpreter import (
    load_agent_suite,
    run_spectrum_analysis,
)


class SpectrumState(rx.State):
    file_path: str = ""
    analysis_type: str = "Spectrogram"  # Spectrogram|FFT|PSD
    # Espectrograma
    nfft: str = "256"
    overlap: str = "0.5"  # 0..1
    window_type: str = "hanning"  # hanning|hamming|blackman
    colorscale: str = "Viridis"  # Viridis|Plasma|Inferno|Turbo
    # FFT
    fft_log: bool = True
    fft_lim: str = "25"
    # PSD
    psd_nperseg: str = "512"
    psd_overlap: str = "0.75"
    psd_log: bool = True
    psd_freq_max: str = "50"

    plot_b64: str = ""
    data_uri: str = ""
    summary: str = ""
    error: Optional[str] = None
    # IA
    ai_result: str = ""
    ai_error: Optional[str] = None

    # Handlers
    def set_file_path(self, v: str):
        self.file_path = v

    def set_analysis_type(self, v: str):
        self.analysis_type = v

    def set_nfft(self, v: str):
        self.nfft = v

    def set_overlap(self, v: str):
        self.overlap = v

    def set_window_type(self, v: str):
        self.window_type = v

    def set_colorscale(self, v: str):
        self.colorscale = v

    def set_fft_log(self, v: bool):
        self.fft_log = v

    def set_fft_lim(self, v: str):
        self.fft_lim = v

    def set_psd_nperseg(self, v: str):
        self.psd_nperseg = v

    def set_psd_overlap(self, v: str):
        self.psd_overlap = v

    def set_psd_log(self, v: bool):
        self.psd_log = v

    def set_psd_freq_max(self, v: str):
        self.psd_freq_max = v

    def _to_int(self, s: str, default: int) -> int:
        try:
            return int(float(s))
        except Exception:
            return default

    def _to_float(self, s: str, default: float) -> float:
        try:
            return float(s)
        except Exception:
            return default

    def generate(self):
        self.error = None
        self.plot_b64 = ""
        self.data_uri = ""
        self.summary = ""
        self.ai_error = None

        path = self.file_path.strip()
        if not path:
            self.error = "Por favor, indique la ruta del archivo."
            return

        try:
            reader = DataReader()
            loaded_list = reader.load_files([Path(path)])
            loaded = loaded_list[0]
            stream = loaded.stream
            trace = stream[0]

            if self.analysis_type == "Spectrogram":
                fig = create_spectrogram(
                    trace,
                    nfft=self._to_int(self.nfft, 256),
                    overlap=self._to_float(self.overlap, 0.5),
                    window_type=self.window_type,
                    colorscale=self.colorscale,
                )
            elif self.analysis_type == "FFT":
                fig = create_fft_plot(
                    trace,
                    log_scale=self.fft_log,
                    freq_limit=self._to_int(self.fft_lim, 25),
                    window_type=self.window_type,
                )
            else:  # PSD
                fig = create_psd_plot(
                    trace,
                    nperseg=self._to_int(self.psd_nperseg, 512),
                    overlap=self._to_float(self.psd_overlap, 0.75),
                    log_scale=self.psd_log,
                    freq_max=self._to_int(self.psd_freq_max, 50),
                )

            png = fig.to_image(format="png", scale=2)
            self.plot_b64 = base64.b64encode(png).decode("ascii")
            self.data_uri = f"data:image/png;base64,{self.plot_b64}"
            self.summary = loaded.summary
        except Exception as exc:
            self.error = f"No se pudo calcular el espectro: {exc}"

    # Upload handler
    def save_upload(self, files: Any = None):
        try:
            upload_dir = rx.get_upload_dir()
            for f in (files or []):
                save_path = upload_dir / f.filename
                f.save(save_path)
                self.file_path = str(save_path)
                break
        except Exception as exc:
            self.error = f"No se pudo guardar el archivo subido: {exc}"

    # ----- IA: Interpretación del análisis espectral -----
    def _build_trace_info(self, trace: Any) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        try:
            stats = getattr(trace, "stats", None)
            if stats is not None:
                info["station"] = getattr(stats, "station", "Desconocida")
                info["channel"] = getattr(stats, "channel", "Desconocido")
                sr = float(getattr(stats, "sampling_rate", 0.0))
                npts = int(getattr(stats, "npts", 0))
                info["sampling_rate"] = f"{sr} Hz"
                info["npts"] = npts
                if hasattr(stats, "starttime"):
                    info["start_time"] = str(stats.starttime)
                if sr > 0 and npts > 0:
                    info["duration"] = f"{npts/sr:.2f} seconds"
        except Exception:
            pass
        return info

    def _format_params_for_ai(self) -> Dict[str, Any]:
        if self.analysis_type == "Spectrogram":
            overlap_pct = self._to_float(self.overlap, 0.5) * 100
            return {
                "nfft": self._to_int(self.nfft, 256),
                "overlap": f"{overlap_pct:.0f}%",
                "window": self.window_type,
                "colorscale": self.colorscale,
            }
        if self.analysis_type == "FFT":
            return {
                "log_scale": self.fft_log,
                "freq_limit_hz": self._to_int(self.fft_lim, 25),
                "window": self.window_type,
            }
        # PSD
        overlap_pct = self._to_float(self.psd_overlap, 0.75) * 100
        return {
            "nperseg": self._to_int(self.psd_nperseg, 512),
            "overlap": f"{overlap_pct:.0f}%",
            "log_scale": self.psd_log,
            "freq_max_hz": self._to_int(self.psd_freq_max, 50),
        }

    def _analysis_type_label(self) -> str:
        return {
            "Spectrogram": "Espectrograma",
            "FFT": "FFT",
            "PSD": "Densidad Espectral (PSD)",
        }.get(self.analysis_type, self.analysis_type)

    def analyze_ai(self):
        """Ejecuta la interpretación IA del análisis espectral actual."""
        self.ai_error = None
        self.ai_result = ""

        path = self.file_path.strip()
        if not path:
            self.ai_error = "Primero seleccione o suba un archivo."
            return

        try:
            reader = DataReader()
            loaded_list = reader.load_files([Path(path)])
            trace = loaded_list[0].stream[0]
        except Exception as exc:
            self.ai_error = f"No se pudo abrir la traza para IA: {exc}"
            return

        try:
            agents = load_agent_suite()
        except Exception as exc:
            self.ai_error = f"No se pudo inicializar el intérprete IA: {exc}"
            return

        try:
            trace_info = self._build_trace_info(trace)
            params = self._format_params_for_ai()
            analysis = run_spectrum_analysis(
                agents,
                trace_info=trace_info,
                analysis_type=self._analysis_type_label(),
                analysis_params=params,
            )
            if analysis:
                self.ai_result = str(analysis)
            else:
                self.ai_error = "El agente no devolvió resultados. Verifique 'spectrum_analysis' en agents_config.yaml."
        except Exception as exc:
            self.ai_error = f"Fallo la interpretación IA: {exc}"


def controls() -> rx.Component:
    return section(
        "Archivo y parámetros",
        rx.hstack(
            rx.upload(
                id="sp_upload",
                multiple=False,
                accept={"application/octet-stream": [".mseed", ".sac", ".seg2", ".sg2"]},
                max_files=1,
            ),
            rx.button(
                "Subir archivo",
                on_click=SpectrumState.save_upload(rx.upload_files("sp_upload")),  # pyright: ignore[reportArgumentType]
            ),
            spacing="3",
        ),
        rx.input(
            value=SpectrumState.file_path,
            on_change=SpectrumState.set_file_path,  # pyright: ignore[reportArgumentType]
            placeholder="Ruta del archivo",
            width="100%",
        ),
        rx.hstack(
            rx.select(["Spectrogram", "FFT", "PSD"], value=SpectrumState.analysis_type, on_change=SpectrumState.set_analysis_type),  # pyright: ignore[reportArgumentType]
            rx.select(["hanning", "hamming", "blackman"], value=SpectrumState.window_type, on_change=SpectrumState.set_window_type),  # pyright: ignore[reportArgumentType]
            spacing="3",
        ),
        rx.cond(
            SpectrumState.analysis_type == "Spectrogram",
            rx.hstack(
                rx.input(placeholder="NFFT", value=SpectrumState.nfft, on_change=SpectrumState.set_nfft, width="120px"),  # pyright: ignore[reportArgumentType]
                rx.input(placeholder="Overlap (0-1)", value=SpectrumState.overlap, on_change=SpectrumState.set_overlap, width="160px"),  # pyright: ignore[reportArgumentType]
                rx.select(["Viridis", "Plasma", "Inferno", "Turbo"], value=SpectrumState.colorscale, on_change=SpectrumState.set_colorscale),  # pyright: ignore[reportArgumentType]
                rx.button("Calcular", on_click=SpectrumState.generate),  # pyright: ignore[reportArgumentType]
                spacing="3",
            ),
            rx.cond(
                SpectrumState.analysis_type == "FFT",
                rx.hstack(
                    rx.input(placeholder="Freq max (Hz)", value=SpectrumState.fft_lim, on_change=SpectrumState.set_fft_lim, width="160px"),  # pyright: ignore[reportArgumentType]
                    rx.switch(checked=SpectrumState.fft_log, on_change=SpectrumState.set_fft_log, label="Log(dB)"),  # pyright: ignore[reportArgumentType]
                    rx.button("Calcular", on_click=SpectrumState.generate),  # pyright: ignore[reportArgumentType]
                    spacing="3",
                ),
                rx.hstack(
                    rx.input(placeholder="nperseg", value=SpectrumState.psd_nperseg, on_change=SpectrumState.set_psd_nperseg, width="160px"),  # pyright: ignore[reportArgumentType]
                    rx.input(placeholder="overlap (0-1)", value=SpectrumState.psd_overlap, on_change=SpectrumState.set_psd_overlap, width="160px"),  # pyright: ignore[reportArgumentType]
                    rx.input(placeholder="freq max (Hz)", value=SpectrumState.psd_freq_max, on_change=SpectrumState.set_psd_freq_max, width="160px"),  # pyright: ignore[reportArgumentType]
                    rx.switch(checked=SpectrumState.psd_log, on_change=SpectrumState.set_psd_log, label="Log(dB)"),  # pyright: ignore[reportArgumentType]
                    rx.button("Calcular", on_click=SpectrumState.generate),  # pyright: ignore[reportArgumentType]
                    spacing="3",
                ),
            ),
        ),
    )


def plot_view() -> rx.Component:
    return rx.cond(
        SpectrumState.data_uri == "",
        rx.box("Genera el análisis espectral para visualizar el resultado."),
        rx.vstack(
            rx.image(src=SpectrumState.data_uri, width="100%"),
            rx.hstack(
                rx.link("Abrir/Descargar PNG", href=SpectrumState.data_uri, is_external=True),
                spacing="3",
            ),
            spacing="3",
            width="100%",
        ),
    )


def page() -> rx.Component:
    return app_shell(
        rx.vstack(
            rx.heading("🔍 Análisis Espectral"),
            controls(),
            rx.cond(SpectrumState.error != None, rx.callout(SpectrumState.error, color="red"), rx.box()),
            rx.cond(SpectrumState.summary != "", rx.code(SpectrumState.summary), rx.box()),
            plot_view(),
            rx.divider(),
            section(
                "Intérprete IA Espectral",
                rx.text("Genera una interpretación operativa en español del análisis espectral."),
                rx.hstack(
                    rx.button("Ejecutar interpretación IA", on_click=SpectrumState.analyze_ai),  # pyright: ignore[reportArgumentType]
                    spacing="3",
                ),
                rx.cond(SpectrumState.ai_error != None, rx.callout(SpectrumState.ai_error, color="red"), rx.box()),
                rx.cond(SpectrumState.ai_result != "", rx.markdown(SpectrumState.ai_result), rx.text("Aún no hay resultados de IA.")),
            ),
            spacing="4",
        )
    )
