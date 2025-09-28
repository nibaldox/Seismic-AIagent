"""
Benchmark de renderizado de waveforms (FPS/tiempos)
"""
import time
import numpy as np
from src.visualization.waveform_plots import create_waveform_plot

# Simular datos: 3 canales, 10,000 puntos cada uno
N = 10000
channels = [
    {
        "data": np.random.normal(0, 1, N),
        "times": np.linspace(0, 100, N),
        "label": f"CH{i+1}"
    }
    for i in range(3)
]
time_window = (0, 100)

# Medir tiempo de render
start = time.time()
fig = create_waveform_plot(channels, time_window)
end = time.time()

total_time = end - start
print(f"Tiempo de renderizado: {total_time:.3f} s para {N} puntos x 3 canales")

# KPI objetivo: < 0.5 s para 10k puntos x 3 canales
if total_time < 0.5:
    print("✅ Cumple KPI de performance")
else:
    print("⚠️ No cumple KPI de performance")

# Documentar KPIs actuales vs objetivo
with open("tests/perf_waveform_kpi.txt", "w") as f:
    f.write(f"Render time: {total_time:.3f} s\n")
    f.write("KPI objetivo: < 0.5 s para 10k puntos x 3 canales\n")
    f.write("Status: " + ("OK" if total_time < 0.5 else "SLOW") + "\n")
