# Developer Guide: Station Coordinates & Metadata

This document explains what is ALREADY implemented in the project for handling station coordinates and how to use it from other modules (e.g., Location 1D, AI tools, reporting).

## What’s implemented today

- Kelunji/Gecko station settings parser (SS files)
  - File: `src/core/kelunji_metadata.py`
  - Public API:
    - `load_kelunji_metadata(source) -> KelunjiMetadata`
    - `loads_kelunji_metadata(content: str) -> KelunjiMetadata`
    - Class `KelunjiMetadata` with:
      - `.raw: Dict[str, str]` holding key/value pairs from the file
      - `.to_sections() -> Dict[str, Dict[str, str]]` grouping keys by logical section (e.g., `Position`)
  - Keys of interest (section `Position`):
    - `lat` (latitude), `long` (longitude), `alt` (altitude), plus GPS satellites, leap seconds, etc.

- Uploader integration that stores station metadata in the shared session
  - File: `pages/00_📁_Uploader.py`
  - Behavior when a `.ss` file is uploaded:
    - Parses with `load_kelunji_metadata(uploaded)`
    - Saves into session:
      - `session.metadata.setdefault("kelunji_metadata", {})[filename] = metadata.raw`
      - `session.metadata["kelunji_last"] = metadata.raw` (handy “last imported” reference)
    - Resets any previously stored earthquake search lat/lon to favor the new metadata.
    - Displays `lat`, `long`, `alt` to the user.

- Simple accessor used by the AI Interpreter page
  - File: `pages/07_🤖_AI_Interpreter.py`
  - Function `_kelunji_coordinates(session) -> (lat, lon, alt)`
    - Reads `session.metadata["kelunji_last"]` and extracts `lat`, `long`, `alt` as floats (or `None`).
  - The page then uses these to initialize the Earthquake Search controls.

- Session state helpers
  - File: `src/streamlit_utils/session_state.py`
  - Exposes `get_session()` and standard access patterns for storing/retrieving metadata.
  - Trace accessors preserve station codes from ObsPy traces (e.g., `trace.stats.station`, `trace.stats.channel`) used throughout the app (plotting, picking, etc.).

## How to use station coordinates in new code

1. Get the shared session and read the last imported Kelunji metadata:
   - `session = get_session()`
   - `meta = session.metadata.get("kelunji_last")` (a `Dict[str, str]` or `None`)
   - Keys you’ll likely need: `meta.get("lat")`, `meta.get("long")`, `meta.get("alt")`

2. Convert to floats safely (example pattern already in `_kelunji_coordinates`):
   - `lat = float(str(meta.get("lat")).strip())` (guard with try/except)
   - `lon = float(str(meta.get("long")).strip())`
   - `alt = float(str(meta.get("alt")).strip())`

3. For algorithms needing planar coordinates (x, y in km), project from (lat, lon):
   - This project does not yet include a projection utility.
   - A common approach is to define a local tangent plane (e.g., ENU) with a reference origin and use a geodesy lib (e.g., `pyproj`) to get meters → convert to km.
   - Keep altitude optional unless required by your method.

4. Build station objects for algorithms:
   - Location 1D expects `Station(code, x_km, y_km)` objects; you can derive `code` from your active traces (`trace.stats.station`).
   - If you only have one station (Kelunji single recorder), you can still pass that station; note that multi-station is required to locate robustly.

## Where station codes come from

- ObsPy traces carry `trace.stats.station` and `trace.stats.channel`.
- We propagate these labels in plots and picks, and store picks as dictionaries including `station` and `channel`.
- When correlating station coordinates with traces, use `trace.stats.station` as the linking key.

## Example flows already using this metadata

- Uploader → Session → AI Interpreter:
  1. User uploads `*.ss` → parser extracts `lat/long/alt`.
  2. Uploader stores them in `session.metadata`.
  3. AI Interpreter uses `_kelunji_coordinates()` to prefill Earthquake Search fields.

## Not implemented (by design, to keep scope focused)

- No global coordinate projection utility (lat/lon → local x/y km) yet.
- No automatic linkage of `.ss` metadata to `Location 1D` page; that page uses synthetic station positions for demo.
  - To replace: read `lat/long` as above, choose a local origin, project to x/y, and construct `Station` objects accordingly.
- No multi-station catalog parsing (only Kelunji `.ss` single-station metadata supported today).

## Pointers for future work

- Add a small geo helper (optional dependency `pyproj`) with a single function:
  - `latlon_to_local_xy(lat, lon, lat0, lon0) -> (x_km, y_km)` using an ENU/ECEF approach.
- Extend `pages/04_🌍_Location_1D.py` to:
  - Read real station positions (if present) instead of creating synthetic ones.
  - Cache projected positions in `session.metadata["station_xy"]` for reuse.
- If multiple `.ss` files are uploaded, allow choosing which station set is active.

## Quick reference (files & functions)

- `src/core/kelunji_metadata.py`
  - `load_kelunji_metadata(source)`
  - `KelunjiMetadata.to_sections()`
- `pages/00_📁_Uploader.py`
  - Stores `kelunji_last` into `session.metadata`
- `pages/07_🤖_AI_Interpreter.py`
  - `_kelunji_coordinates(session)`
- `src/streamlit_utils/session_state.py`
  - `get_session()` and session `.metadata` storage
- `src/core/location/one_d_location.py`
  - `Station` model and `locate_event_1d(...)`
