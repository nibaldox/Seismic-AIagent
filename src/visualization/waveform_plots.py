from __future__ import annotations

from typing import Literal
FilterType = Literal['bandpass', 'highpass', 'lowpass', 'none']

"""Plotly helpers for waveform visualization."""

from typing import Any, cast, Iterable, List, Tuple

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import numpy as np

from src.core.signal_processing import apply_filter, compute_global_range, normalize_trace


def _classify_axis(channel: str) -> str:
    channel_upper = channel.upper()
    if "SUM" in channel_upper or channel_upper.endswith("VS") or channel_upper.endswith("S"):
        return "sum"
    if channel_upper.endswith(("E", "X", "1")):
        return "x"
    if channel_upper.endswith(("N", "Y", "2")):
        return "y"
    if channel_upper.endswith(("Z", "3")):
        return "z"
    return "other"


def _trace_label(trace: Any, fallback_index: int) -> str:
    if hasattr(trace, "id") and trace.id:
        return str(trace.id)
    if hasattr(trace, "stats") and getattr(trace.stats, "channel", None):
        return str(trace.stats.channel)
    return f"Trace {fallback_index + 1}"


def _subplot_title(trace: Any, fallback_index: int) -> str:
    if isinstance(trace, dict):
        return trace["label"]

    stats = getattr(trace, "stats", None)
    channel = getattr(stats, "channel", "") if stats else ""
    axis = _classify_axis(channel)
    axis_pretty = {"x": "X", "y": "Y", "z": "Z", "sum": "SUM"}.get(axis)
    base = channel or _trace_label(trace, fallback_index)
    return f"{axis_pretty} · {base}" if axis_pretty else base


def _trace_color(trace: Any, fallback_index: int) -> str:
    palette = {
        "x": "#74b9ff",
        "y": "#55efc4",
        "z": "#ffeaa7",
        "sum": "#ff7675",
        "other": "#dfe6e9",
    }
    if isinstance(trace, dict):
        label = trace.get("label", "")
        axis = "sum" if "sum" in label.lower() else "other"
        return palette.get(axis, palette["other"])

    stats = getattr(trace, "stats", None)
    channel = getattr(stats, "channel", "") if stats else ""
    axis = _classify_axis(channel)
    return palette.get(axis, palette["other"])


def _convert_cmps2(data: np.ndarray, unit: str) -> tuple[np.ndarray, str]:
    """Convert from assumed cm/s² raw units to desired unit.

    Returns converted data and a short unit label for axis.
    Supported unit values: "Raw" (cm/s²), "m/s²", "g".
    """
    if unit == "m/s²":
        return data / 100.0, "m/s²"
    if unit == "g":
        return data / 980.665, "g"
    return data, "cm/s²"


def _format_micro_g(value_in_g: float) -> str:
    """Format amplitude scale in micro-g or milli-g for readability."""
    micro_g = value_in_g * 1_000_000.0
    if micro_g >= 1000:  # show in milli-g
        return f"{value_in_g*1000:.3f} mg"
    return f"{micro_g:.1f} µg"


def adaptive_downsample(data: np.ndarray, times: np.ndarray, target_points: int = 1200) -> tuple[np.ndarray, np.ndarray]:
    """Reduce la cantidad de puntos preservando min/max por bucket (ideal para visualización)."""
    n = len(data)
    if n <= target_points or target_points < 10:
        return times, data
    bucket_size = n // target_points
    # Si bucket_size < 2, no hace falta downsampling
    if bucket_size < 2:
        return times, data
    # Para cada bucket, tomar min y max
    down_times = []
    down_data = []
    for i in range(0, n, bucket_size):
        chunk = data[i:i+bucket_size]
        t_chunk = times[i:i+bucket_size]
        if len(chunk) == 0:
            continue
        min_idx = np.argmin(chunk)
        max_idx = np.argmax(chunk)
        down_data.extend([chunk[min_idx], chunk[max_idx]])
        down_times.extend([t_chunk[min_idx], t_chunk[max_idx]])
    return np.array(down_times), np.array(down_data)


def create_waveform_plot(
    streams: Iterable[Any],
    time_window: Tuple[int, int],
    *,
    title: str = "Waveforms",
    unit: str = "Raw",
    picks: List[dict] | None = None,
    filter_type: str | None = None,
    freqmin: float | None = None,
    freqmax: float | None = None,
    amplitude_scale: str = "Auto",
) -> go.Figure:
    """Generate a stacked waveform plot for the provided ObsPy streams."""

    traces: List[Any] = list(streams)
    if not traces:
        return go.Figure()

    indexed_traces = list(enumerate(traces))

    def sort_key(item):
        idx, trace = item
        channel = getattr(getattr(trace, "stats", None), "channel", "") or ""
        axis = _classify_axis(channel)
        axis_priority = {"x": 0, "y": 1, "z": 2, "sum": 3}.get(axis, 4)
        return (axis_priority, channel.upper(), idx)

    ordered = [trace for _, trace in sorted(indexed_traces, key=sort_key)]

    axis_map = {}
    for trace in ordered:
        channel = getattr(getattr(trace, "stats", None), "channel", "") or ""
        axis = _classify_axis(channel)
        axis_map.setdefault(axis, trace)

    has_sum_channel = axis_map.get("sum") is not None

    computed_sum = None
    if not has_sum_channel and all(axis in axis_map for axis in ("x", "y", "z")):
        x_trace = axis_map["x"]
        y_trace = axis_map["y"]
        z_trace = axis_map["z"]
        min_len = min(len(x_trace.data), len(y_trace.data), len(z_trace.data))
        times = np.asarray(x_trace.times("relative"))[:min_len]
        x_data = np.nan_to_num(np.asarray(x_trace.data)[:min_len], nan=0.0)
        y_data = np.nan_to_num(np.asarray(y_trace.data)[:min_len], nan=0.0)
        z_data = np.nan_to_num(np.asarray(z_trace.data)[:min_len], nan=0.0)
        # Calculate vector sum magnitude, ensuring non-negative values
        squared_sum = np.square(x_data) + np.square(y_data) + np.square(z_data)
        sum_data = np.sqrt(np.maximum(squared_sum, 0.0))
        computed_sum = {"times": times, "data": sum_data, "label": "Vector Sum"}

    plot_traces = ordered.copy()
    if computed_sum is not None:
        plot_traces.append(computed_sum)

    fig = make_subplots(
        rows=len(plot_traces),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=[_subplot_title(trace, idx) for idx, trace in enumerate(plot_traces)],
    )

    window_start, window_end = time_window

    annotations = []
    processed_arrays: List[np.ndarray] = []
    for idx, trace in enumerate(plot_traces, start=1):
        if isinstance(trace, dict):
            times = np.asarray(trace["times"])
            data = np.asarray(trace["data"])
            name = trace["label"]
        else:
            times = np.asarray(trace.times("relative"))
            data = np.asarray(trace.data)
            name = _trace_label(trace, idx - 1)

        if times.size == 0 or data.size == 0:
            continue

        mask = (times >= window_start) & (times <= window_end)
        if not np.any(mask):
            masked_times = times
            masked_data = data
        else:
            masked_times = times[mask]
            masked_data = data[mask]

        # Filtering (does not mutate original trace)
        stats = getattr(trace, "stats", None)
        sr = float(getattr(stats, "sampling_rate", 0) or 0)
        if filter_type and filter_type != "none" and sr > 0 and freqmin is not None and freqmax is not None:
            try:
                masked_data = apply_filter(masked_data, sr, filter_type=cast(FilterType, filter_type), freqmin=freqmin, freqmax=freqmax)
            except Exception:  # pragma: no cover
                pass

        # Downsampling adaptativo para visualización
        target_points = 1200  # Valor típico para performance y detalle
        down_times, down_data = adaptive_downsample(masked_data, masked_times, target_points=target_points)

        # Convert chosen display unit
        down_data, axis_unit = _convert_cmps2(down_data, unit)
        processed_arrays.append(down_data)

        fig.add_trace(
            go.Scatter(
                x=down_times,
                y=down_data,
                name=name,
                mode="lines",
                line=dict(color=_trace_color(trace, idx - 1), width=2.0),
            ),
            row=idx,
            col=1,
        )

        # Axis placeholder; real scaling applied after loop depending on amplitude_scale
        fig.update_yaxes(title_text="", row=idx, col=1, automargin=True, zeroline=False, showline=False)

        # Build left-side annotation similar to provided screenshot
        # Compute peak amplitude in g for a consistent representation
        # First derive data in g regardless of display unit
        data_in_g = masked_data if axis_unit == "g" else (_convert_cmps2(masked_data * (100.0 if axis_unit == "m/s²" else 1.0), "g")[0] if axis_unit != "g" else masked_data)
        peak_g = float(np.max(np.abs(data_in_g))) if data_in_g.size else 0.0
        amp_label = _format_micro_g(peak_g)

        channel_label = name
        annotation_text = f"{amp_label}<br>{channel_label}"
        # Determine a y position near the top of current data range (before any global/normalized rescale)
        local_y_max = float(np.max(masked_data)) if masked_data.size else 0.0
        # If flat line, nudge a bit so text is visible after later scaling adjustments
        if masked_data.size and np.allclose(local_y_max, np.min(masked_data)):
            local_y_max += 1.0 if local_y_max == 0 else abs(local_y_max) * 0.05
        annotations.append(
            dict(
                xref=f"x{idx}" if idx > 1 else "x",
                yref=f"y{idx}" if idx > 1 else "y",
                x=masked_times[0] if masked_times.size else 0,
                y=local_y_max,
                xanchor="left",
                yanchor="top",
                text=annotation_text,
                showarrow=False,
                font=dict(size=11, color="#ff4d4d"),
                align="left",
            )
        )

    # Overlay picks (vertical lines). We assign them to matching channel trace rows.
    pick_shapes = []
    if picks:
        channel_row_map = {}
        for idx, trace in enumerate(plot_traces, start=1):
            if isinstance(trace, dict):
                label = trace.get("label", f"Trace {idx}")
            else:
                stats = getattr(trace, "stats", None)
                channel = getattr(stats, "channel", None)
                station = getattr(stats, "station", None)
                label = f"{station}.{channel}" if station and channel else channel or _trace_label(trace, idx - 1)
            channel_row_map[label] = idx
        for p in picks:
            ch_label = f"{p.get('station')}.{p.get('channel')}" if p.get('station') and p.get('channel') else p.get('channel')
            row = channel_row_map.get(ch_label)
            if not row:
                continue
            color = "#00e5ff" if p.get("phase") == "P" else ("#ffa142" if p.get("phase") == "S" else "#cccccc")
            t = float(p.get("time_rel", 0.0))
            # Only draw if inside window
            if not (time_window[0] <= t <= time_window[1]):
                continue
            pick_shapes.append(
                dict(
                    type="line",
                    xref=f"x{row}" if row > 1 else "x",
                    # Use domain so y0=0..y1=1 spans the full height of the subplot row
                    yref=f"y{row} domain" if row > 1 else "y domain",
                    x0=t,
                    x1=t,
                    y0=0,
                    y1=1,
                    line=dict(color=color, width=2, dash="dash"),
                    layer="above",
                )
            )
    # Apply amplitude scaling
    if processed_arrays:
        if amplitude_scale.lower() == "global":
            gmin, gmax = compute_global_range(processed_arrays)
            if gmin == gmax:
                delta = 1.0 if gmin == 0 else abs(gmin) * 0.05
                gmin -= delta
                gmax += delta
            for i in range(1, len(processed_arrays) + 1):
                fig.update_yaxes(range=[gmin, gmax], row=i, col=1)
        elif amplitude_scale.lower() == "normalized":
            for i, arr in enumerate(processed_arrays, start=1):
                norm_arr = normalize_trace(arr)
                # Replace trace data (inefficient but simple for now)
                fig.data[i - 1].y = norm_arr
                fig.update_yaxes(range=[-1.05, 1.05], row=i, col=1)
        else:  # Auto / Individual default
            for i, arr in enumerate(processed_arrays, start=1):
                y_min = float(np.min(arr)) if arr.size else 0.0
                y_max = float(np.max(arr)) if arr.size else 0.0
                if y_min == y_max:
                    delta = 1.0 if y_min == 0 else abs(y_min) * 0.05
                    y_min -= delta
                    y_max += delta
                fig.update_yaxes(range=[y_min, y_max], row=i, col=1)

    fig.update_xaxes(title_text="Time (s)", row=len(plot_traces), col=1)
    # Calculate automatic X-axis range based on all processed data
    if processed_arrays:
        all_times = []
        for idx, trace in enumerate(plot_traces, start=1):
            if isinstance(trace, dict):
                times = np.asarray(trace["times"])
            else:
                times = np.asarray(trace.times("relative"))

            if times.size > 0:
                # Apply the same time window masking as used for plotting
                mask = (times >= window_start) & (times <= window_end)
                if np.any(mask):
                    masked_times = times[mask]
                else:
                    masked_times = times
                all_times.extend(masked_times)

        if all_times:
            x_min = float(np.min(all_times))
            x_max = float(np.max(all_times))
            if x_min == x_max:
                x_max = x_min + 1.0
            # Apply automatic X-axis range to all subplots
            for i in range(1, len(plot_traces) + 1):
                fig.update_xaxes(range=[x_min, x_max], row=i, col=1)
    # Ensure shapes/annotations are standard python lists (Plotly accepts lists/tuples)
    existing_ann = list(fig.layout.annotations) if getattr(fig.layout, "annotations", None) else []
    existing_shapes = list(fig.layout.shapes) if getattr(fig.layout, "shapes", None) else []
    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=260 * len(plot_traces),
        showlegend=False,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, r=30, b=40, l=80),
        annotations=(existing_ann + list(annotations)),
        shapes=(existing_shapes + list(pick_shapes)),
    )
    return fig
