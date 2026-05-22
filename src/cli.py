"""CLI headless entry point — SeismoAnalyzer Pro batch processing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.core.data_reader import DataReader, DataReadError
from src.core.intensity_measures import compute_all_ims
from src.core.picking import suggest_picks_sta_lta
from src.utils.logger import setup_logger

LOGGER = setup_logger("cli")


def process_file(file_path: Path, output_format: str = "json") -> dict:
    """Process a single seismic file and return analysis results."""
    reader = DataReader()
    try:
        loaded = reader.load_files([file_path])
    except (DataReadError, FileNotFoundError) as exc:
        return {"error": str(exc), "file": str(file_path)}

    if not loaded or not loaded[0].stream:
        return {"error": "No data loaded", "file": str(file_path)}

    stream = loaded[0].stream
    results = {"file": str(file_path), "format": loaded[0].format_description, "traces": []}

    for tr in stream:
        trace_result = {
            "station": tr.stats.station,
            "channel": tr.stats.channel,
            "network": tr.stats.network,
            "sampling_rate": tr.stats.sampling_rate,
            "n_samples": tr.stats.npts,
            "start_time": str(tr.stats.starttime),
            "duration_s": tr.stats.npts / tr.stats.sampling_rate if tr.stats.sampling_rate > 0 else 0,
        }

        sr = tr.stats.sampling_rate

        if sr > 0:
            ims = compute_all_ims(tr)
            if ims:
                trace_result["ims"] = {
                    "pga_cms2": ims.pga_cms2,
                    "pga_g": ims.pga_g,
                    "pgv_cms": ims.pgv_cms,
                    "pgd_cm": ims.pgd_cm,
                    "arias_ms": ims.arias_ms,
                    "cav_cms": ims.cav_cms,
                    "dominant_period_s": ims.dominant_period_s,
                }

            picks = suggest_picks_sta_lta(tr)
            trace_result["picks"] = [
                {"time_rel": p.get("time_rel"), "phase": p.get("phase"),
                 "score": p.get("score"), "snr_db": p.get("snr_db")}
                for p in picks
            ]

        results["traces"].append(trace_result)

    return results


def process_directory(dir_path: Path, pattern: str = "*.ms", output_format: str = "json") -> list[dict]:
    """Process all matching files in a directory."""
    all_paths = sorted(dir_path.glob(pattern))
    files = [p for p in all_paths if p.is_file()]
    if not files:
        LOGGER.warning("No files matching '%s' found in %s", pattern, dir_path)
        return []

    results = []
    for fpath in files:
        LOGGER.info("Processing %s", fpath)
        result = process_file(fpath, output_format)
        results.append(result)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="SeismoAnalyzer Pro — CLI batch processing")
    parser.add_argument("input", type=str, help="File path or directory to process")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output file path (default: stdout)")
    parser.add_argument("-f", "--format", choices=["json", "human"], default="json", help="Output format")
    parser.add_argument("-p", "--pattern", type=str, default="*.ms", help="Glob pattern when input is a directory")
    parser.add_argument("-r", "--recursive", action="store_true", help="Search directories recursively")

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        LOGGER.error("Input path does not exist: %s", input_path)
        return 1

    if input_path.is_dir():
        pattern = f"**/{args.pattern}" if args.recursive else args.pattern
        results = process_directory(input_path, pattern=pattern, output_format=args.format)
    else:
        results = [process_file(input_path, args.format)]

    output = json.dumps(results, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(output)
        LOGGER.info("Results written to %s", args.output)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
