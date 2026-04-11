from __future__ import annotations

"""Generate AI-assisted Markdown and HTML reports."""

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.utils.logger import setup_logger

LOGGER = setup_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from agno.agent import Agent as AgnoAgent
    import plotly.graph_objects as go
else:
    AgnoAgent = Any  # type: ignore


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def _md_to_html(text: str) -> str:
    """Convert markdown text to HTML, with fallback to pre-escaped text."""
    try:
        import markdown  # type: ignore
        return markdown.markdown(text, extensions=["tables", "fenced_code"])
    except ImportError:
        import html as _html
        escaped = _html.escape(text)
        # Minimal: convert newlines to <br> inside a <pre>
        return f"<pre style='white-space:pre-wrap;font-family:inherit'>{escaped}</pre>"


def _fig_to_html(fig: Any, include_js: bool = False) -> str:
    """Serialize a Plotly figure to an HTML div string."""
    try:
        import plotly.io as pio  # type: ignore
        return pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs="cdn" if include_js else False,
            config={"responsive": True, "displayModeBar": True},
        )
    except Exception as exc:
        LOGGER.warning("Could not serialize figure: %s", exc)
        return "<p><em>Gráfico no disponible.</em></p>"


def _picks_table_html(picks: List[Dict[str, Any]]) -> str:
    """Render a picks list as an HTML table."""
    if not picks:
        return "<p><em>Sin picks registrados.</em></p>"
    rows = "\n".join(
        f"<tr><td>{p.get('phase','?')}</td><td>{p.get('station','?')}</td>"
        f"<td>{p.get('channel','?')}</td><td>{p.get('time_rel','?'):.3f}</td>"
        f"<td>{p.get('method','?')}</td></tr>"
        for p in picks
    )
    return f"""
<table>
  <thead>
    <tr><th>Fase</th><th>Estación</th><th>Canal</th><th>t_rel (s)</th><th>Método</th></tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>"""


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Informe Sísmico — {dataset_name}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bg: #0e1117; --surface: #1a1d24; --border: #2d3139;
      --text: #e0e0e0; --muted: #9ca3af; --accent: #4f8ef7;
      --green: #34d399; --yellow: #fbbf24; --red: #f87171;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', Arial, sans-serif;
           font-size: 14px; line-height: 1.6; padding: 32px 48px; max-width: 1200px; margin: auto; }}
    h1 {{ font-size: 1.8rem; color: var(--accent); margin-bottom: 4px; }}
    h2 {{ font-size: 1.2rem; color: var(--accent); margin: 32px 0 12px;
          border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
    h3 {{ font-size: 1rem; color: var(--muted); margin: 20px 0 8px; }}
    p, pre {{ margin-bottom: 12px; }}
    pre {{ background: var(--surface); padding: 12px; border-radius: 6px;
           border: 1px solid var(--border); overflow-x: auto; font-size: 13px; }}
    code {{ background: var(--surface); padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th {{ background: var(--surface); color: var(--accent); padding: 8px 12px;
          text-align: left; border: 1px solid var(--border); font-size: 13px; }}
    td {{ padding: 7px 12px; border: 1px solid var(--border); font-size: 13px; }}
    tr:nth-child(even) td {{ background: var(--surface); }}
    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
              font-size: 12px; font-weight: 600; }}
    .badge-info {{ background: #1e3a5f; color: var(--accent); }}
    .meta-row {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 12px 0 24px;
                 font-size: 13px; color: var(--muted); }}
    .figure-wrap {{ margin: 20px 0; border: 1px solid var(--border);
                    border-radius: 8px; overflow: hidden; }}
    .section {{ margin-bottom: 32px; }}
    hr {{ border: none; border-top: 1px solid var(--border); margin: 28px 0; }}
    footer {{ margin-top: 40px; font-size: 12px; color: var(--muted);
              border-top: 1px solid var(--border); padding-top: 16px; text-align: center; }}
    ul, ol {{ padding-left: 20px; margin-bottom: 12px; }}
    li {{ margin-bottom: 4px; }}
    strong {{ color: #e9ecef; }}
    blockquote {{ border-left: 3px solid var(--accent); padding-left: 12px;
                  color: var(--muted); margin: 12px 0; }}
  </style>
</head>
<body>

  <h1>🌍 Informe Sísmico</h1>
  <div class="meta-row">
    <span><strong>Dataset:</strong> {dataset_name}</span>
    <span><strong>Fecha:</strong> {report_date}</span>
    <span><strong>Generado por:</strong> SeismoAnalyzer — Agentes IA</span>
  </div>
  <hr/>

  <!-- RESUMEN DEL STREAM -->
  <div class="section">
    <h2>📡 Resumen del Stream</h2>
    {stream_summary_html}
  </div>

  <!-- WAVEFORM -->
  {waveform_section}

  <!-- ESPECTRO -->
  {spectrum_section}

  <!-- PICKS P/S -->
  <div class="section">
    <h2>📍 Picks P/S</h2>
    {picks_html}
  </div>

  <!-- ANÁLISIS IA -->
  <div class="section">
    <h2>🤖 Análisis IA</h2>
    {ai_analysis_html}
  </div>

  <!-- CONTEXTO SÍSMICO -->
  {earthquake_section}

  <footer>
    Reporte generado automáticamente · SeismoAnalyzer Pro · {report_date}
  </footer>

</body>
</html>
"""


def generate_html_report(
    *,
    dataset_name: str = "Dataset Sísmico",
    stream_summary: Optional[str] = None,
    ai_analysis: Optional[str] = None,
    earthquake_context: Optional[str] = None,
    picks: Optional[List[Dict[str, Any]]] = None,
    waveform_fig: Optional[Any] = None,
    spectrum_figs: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a self-contained HTML report with embedded Plotly figures.

    Parameters
    ----------
    dataset_name:       Name of the dataset (used in title).
    stream_summary:     Text summary of the seismic stream metadata.
    ai_analysis:        Markdown text from the AI agent analysis.
    earthquake_context: Markdown summary of nearby earthquake catalog results.
    picks:              List of P/S pick dicts (phase, station, channel, time_rel, method).
    waveform_fig:       Plotly Figure of the waveform.
    spectrum_figs:      Dict of Plotly Figures keyed by label
                        e.g. {"Espectrograma": fig1, "FFT": fig2, "PSD": fig3}.

    Returns
    -------
    str: Full self-contained HTML document.
    """
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- Stream summary ---
    stream_summary_html = _md_to_html(stream_summary) if stream_summary else "<p><em>Sin resumen disponible.</em></p>"

    # --- Waveform figure ---
    if waveform_fig is not None:
        waveform_div = _fig_to_html(waveform_fig, include_js=False)
        waveform_section = f"""
  <div class="section">
    <h2>📈 Forma de Onda</h2>
    <div class="figure-wrap">{waveform_div}</div>
  </div>"""
    else:
        waveform_section = ""

    # --- Spectrum figures ---
    if spectrum_figs:
        spec_parts = []
        for label, fig in spectrum_figs.items():
            div = _fig_to_html(fig, include_js=False)
            spec_parts.append(
                f"<h3>{label}</h3><div class='figure-wrap'>{div}</div>"
            )
        spectrum_section = f"""
  <div class="section">
    <h2>🔍 Análisis Espectral</h2>
    {''.join(spec_parts)}
  </div>"""
    else:
        spectrum_section = ""

    # --- Picks table ---
    picks_html = _picks_table_html(picks or [])

    # --- AI analysis ---
    ai_analysis_html = _md_to_html(ai_analysis) if ai_analysis else "<p><em>Sin análisis IA disponible.</em></p>"

    # --- Earthquake context ---
    if earthquake_context:
        eq_html = _md_to_html(earthquake_context)
        earthquake_section = f"""
  <div class="section">
    <h2>🌐 Contexto de Sismicidad Cercana</h2>
    {eq_html}
  </div>"""
    else:
        earthquake_section = ""

    return _HTML_TEMPLATE.format(
        dataset_name=dataset_name,
        report_date=report_date,
        stream_summary_html=stream_summary_html,
        waveform_section=waveform_section,
        spectrum_section=spectrum_section,
        picks_html=picks_html,
        ai_analysis_html=ai_analysis_html,
        earthquake_section=earthquake_section,
    )


# ---------------------------------------------------------------------------
# Legacy Markdown helpers (kept for backward compatibility)
# ---------------------------------------------------------------------------

def build_report_md(
    waveform_summary: str,
    ai_analysis: str,
    earthquake_context: str = "",
    author: str = "Equipo IA SeismoAnalyzer",
) -> str:
    """Build a simple institutional Markdown report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"# Informe Sísmico Institucional\n\n**Fecha:** {now}\n**Autor:** {author}\n\n---\n"
    sections = [
        "## Resumen de Waveform\n" + (waveform_summary or "(sin datos)"),
        "## Análisis IA\n" + (ai_analysis or "(sin análisis)"),
    ]
    if earthquake_context:
        sections.append("## Contexto de Sismicidad Cercana\n" + earthquake_context)
    footer = "\n---\n_Reporte generado automáticamente por SeismoAnalyzer Pro_"
    return header + "\n\n".join(sections) + footer


from src.ai_agent.seismic_interpreter import AgentSpec, create_agent  # noqa: E402


def build_report_agent(default_provider: str, default_model: str) -> "AgnoAgent":
    spec = AgentSpec(
        provider=default_provider,
        model_id=default_model,
        role="Generador de Reportes Tecnicos",
        instructions=(
            "Eres un redactor tecnico especializado en informes de analisis sismico.\n"
            "Tu tarea es crear informes profesionales en espanol neutro, manteniendo un tono claro y conciso.\n\n"
            "INSTRUCCIONES ESPECIFICAS:\n"
            "1. Estructura el informe con secciones claras y encabezados apropiados\n"
            "2. Incluye estimaciones de confianza cuando sea posible\n"
            "3. Evita fragmentos en otros idiomas que no sean espanol\n"
            "4. Manten consistencia tecnica y profesionalismo\n\n"
            "FORMATO DE SALIDA:\n"
            "## Resumen Ejecutivo\n"
            "## Analisis Tecnico\n"
            "## Conclusiones\n"
            "## Referencias\n\n"
            "Finaliza con una linea que indique el nivel de confianza global (Alta/Media/Baja)."
        ),
    )
    return create_agent(spec, show_tool_calls=False)


def generate_markdown_report(
    agent: "AgnoAgent",
    *,
    waveform_summary: str,
    ai_analysis: Optional[str],
    earthquake_context: Optional[str],
) -> str:
    """Generate a Markdown report by prompting the supplied agent."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    prompt = (
        "Genera un informe completo en formato Markdown escrito completamente en espanol neutro.\n"
        f"El reporte debe llevar fecha {timestamp} y usar la informacion entregada mas abajo.\n"
        "Manten parrafos cortos y preferentemente usa listas cuando mejoren la claridad.\n\n"
        f"## Datos de Analisis\n\n"
        f"### Resumen del Flujo de Forma de Onda\n{waveform_summary}\n\n"
        f"### Analisis del Agente IA\n{ai_analysis or 'No disponible.'}\n\n"
        f"### Contexto de Sismicidad Externa\n{earthquake_context or 'Sin eventos externos relevantes.'}\n\n"
        "## Estructura del Informe\n\n"
        "El informe debe incluir exactamente estos encabezados en este orden:\n"
        "- ## Resumen Ejecutivo\n"
        "- ## Analisis Tecnico\n"
        "- ## Conclusiones\n"
        "- ## Referencias\n\n"
        "Cada seccion debe ser concisa pero completa. Incluye niveles de confianza donde sea apropiado.\n"
        "Finaliza con una linea que indique el nivel de confianza global (Alta/Media/Baja)."
    )
    LOGGER.info("Generating Markdown report via agent %s", getattr(agent, "name", "unknown"))
    response = agent.run(prompt)
    return getattr(response, "content", "# Report\nReport content unavailable.")
