"""Dedicated upload page with validation."""

from __future__ import annotations

from io import BytesIO
import zipfile
from typing import Iterable, List
from datetime import datetime

import streamlit as st

from src.core.data_reader import DataReader, LoadedStream
from src.streamlit_utils.appearance import handle_error
from src.core.kelunji_metadata import load_kelunji_metadata
from src.streamlit_utils.session_state import (
    get_current_stream_name,
    get_session,
    get_stream_summary,
    list_dataset_names,
    register_stream,
    set_current_stream,
)

ACCEPTED_MSEED = {"ms": "MiniSEED", "mseed": "MiniSEED"}
ACCEPTED_METADATA = {"ss": "Kelunji metadata"}
ACCEPTED_OTHER_WAVEFORMS = {
    "sac": "SAC",
    "seg2": "SEG-2",
    "sg2": "SEG-2",
    "suds": "PC-SUDS",
}
ACCEPTED_GEOCKO = {"bin": "Gecko histogram"}


def main() -> None:
    st.header("📁 Seismic File Uploader")
    session = get_session()
    reader = DataReader()

    # Dataset activo y resumen (primero en la página)
    dataset_names = list_dataset_names(session=session)
    current_dataset = get_current_stream_name(session=session)

    if dataset_names:
        st.subheader("Dataset activo")
        selected_dataset = st.selectbox(
            "Active dataset",
            options=dataset_names,
            index=dataset_names.index(current_dataset) if current_dataset in dataset_names else 0,
            key="uploader_active_dataset",
        )
        if selected_dataset and selected_dataset != current_dataset:
            set_current_stream(selected_dataset, session=session)
            current_dataset = selected_dataset

    summary = get_stream_summary(current_dataset, session=session) if current_dataset else None
    if summary:
        st.subheader(f"Resumen del stream — {current_dataset}")
        with st.expander("Ver/ocultar resumen del stream", expanded=False):
            st.code(summary, language="text")

    st.divider()

    st.subheader("Carga de Waveforms MiniSEED (.ms/.mseed)")
    do_merge = st.checkbox(
        "Fusionar MiniSEED compatibles en un solo dataset",
        value=False,
        help="Si cargas varios archivos MiniSEED se intentará combinarlos en un Stream unificado.",
        key="merge_mseed",
    )
    mseed_files: Iterable[BytesIO] = st.file_uploader(
        "Sube uno o más archivos MiniSEED",
        accept_multiple_files=True,
        type=list(ACCEPTED_MSEED.keys()),
        help="Extensiones soportadas: .ms, .mseed",
        key="uploader_mseed",
    )

    loaded_mseed: List[tuple[str, LoadedStream]] = []
    mseed_loaded_names: List[str] = []
    if mseed_files:
        for uploaded in mseed_files:
            ext = uploaded.name.split(".")[-1].lower()
            friendly = ACCEPTED_MSEED.get(ext, ext.upper())
            with st.spinner(f"Cargando {friendly}: {uploaded.name}..."):
                try:
                    loaded = reader.load_bytes(buffer=uploaded)
                except Exception as exc:  # pragma: no cover
                    handle_error(exc, context=f"No se pudo cargar {uploaded.name}")
                    continue
            register_stream(stream=loaded.stream, name=uploaded.name, summary=loaded.summary)
            loaded_mseed.append((uploaded.name, loaded))
            mseed_loaded_names.append(f"{uploaded.name} ({friendly})")

        if mseed_loaded_names:
            st.success(f"Cargados {len(mseed_loaded_names)} archivos MiniSEED")
            with st.expander("Ver archivos MiniSEED cargados", expanded=False):
                st.markdown("\n".join(f"- {name}" for name in mseed_loaded_names))

        # Merge solo para MiniSEED
        if do_merge and loaded_mseed:
            try:
                from obspy import Stream  # type: ignore
            except Exception as exc:
                st.warning(f"No se pudo importar ObsPy para merge: {exc}")
            else:
                if len(loaded_mseed) >= 2:
                    st_all = Stream()
                    for _, ls in loaded_mseed:
                        st_all += ls.stream
                    try:
                        st_all.sort()
                    except Exception:
                        pass
                    try:
                        st_all.merge(method=1, fill_value=0.0)
                    except Exception as exc:
                        st.warning(f"No se pudo completar el merge automático: {exc}")
                    else:
                        merged_name = f"MERGED_MS_{len(loaded_mseed)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        header = f"Merged | {len(st_all)} traces (from {len(loaded_mseed)} MiniSEED files)"
                        summary_lines = [header, *(tr.stats.__str__() for tr in st_all)]
                        merged_summary = "\n".join(summary_lines)
                        register_stream(stream=st_all, name=merged_name, summary=merged_summary)
                        set_current_stream(merged_name, session=session)
                        st.success(f"Creado dataset fusionado: {merged_name}")
                else:
                    st.info("Se requiere al menos 2 archivos MiniSEED para fusionar.")

    st.divider()
    st.subheader("Carga de Metadatos Kelunji (.ss)")
    ss_files: Iterable[BytesIO] = st.file_uploader(
        "Sube archivos .ss (Kelunji metadata)",
        accept_multiple_files=True,
        type=list(ACCEPTED_METADATA.keys()),
        help="Se almacenarán en sesión para autofill en búsquedas y localización.",
        key="uploader_ss",
    )

    if ss_files:
        for uploaded in ss_files:
            metadata = load_kelunji_metadata(uploaded)
            session.metadata.setdefault("kelunji_metadata", {})[uploaded.name] = metadata.raw
            session.metadata["kelunji_last"] = metadata.raw
            session.metadata.pop("earthquake_search_lat", None)
            session.metadata.pop("earthquake_search_lon", None)
            session.metadata.pop("earthquake_search_radius_km", None)

            lat = metadata.raw.get("lat") or "—"
            lon = metadata.raw.get("long") or "—"
            alt = metadata.raw.get("alt") or "—"

            st.success(f"Importado metadato Kelunji: {uploaded.name}")
            cols = st.columns(3)
            cols[0].metric("Latitud", lat)
            cols[1].metric("Longitud", lon)
            cols[2].metric("Altitud (m)", alt)

    st.divider()
    st.subheader("Carga de otros waveforms (SAC/SEG-2/SUDS) y Gecko (.bin)")
    other_files: Iterable[BytesIO] = st.file_uploader(
        "Sube archivos adicionales",
        accept_multiple_files=True,
        type=list({**ACCEPTED_OTHER_WAVEFORMS, **ACCEPTED_GEOCKO}.keys()),
        help="Soporta SAC/SEG-2/SUDS y histogramas Gecko (.bin). No aplica merge automático.",
        key="uploader_other",
    )

    other_loaded_names: List[str] = []
    if other_files:
        for uploaded in other_files:
            ext = uploaded.name.split(".")[-1].lower()
            friendly = (ACCEPTED_OTHER_WAVEFORMS | ACCEPTED_GEOCKO).get(ext, ext.upper())
            with st.spinner(f"Cargando {friendly}: {uploaded.name}..."):
                try:
                    loaded = reader.load_bytes(buffer=uploaded)
                except Exception as exc:  # pragma: no cover
                    st.error(f"No se pudo cargar {uploaded.name}: {exc}")
                    continue
            register_stream(stream=loaded.stream, name=uploaded.name, summary=loaded.summary)
            other_loaded_names.append(f"{uploaded.name} ({friendly})")

        if other_loaded_names:
            st.success(f"Cargados {len(other_loaded_names)} archivos adicionales")
            with st.expander("Ver detalle de archivos cargados", expanded=False):
                st.markdown("\n".join(f"- {name}" for name in other_loaded_names))

    st.divider()
    st.subheader("Importar carpetas o ZIP")
    import_mode = st.radio(
        "Tipo de importación",
        options=["ZIP", "Carpetas locales"],
        index=0,
        horizontal=True,
        key="import_mode_zip_or_local",
    )

    if import_mode == "ZIP":
        do_zip_merge = st.checkbox(
            "Fusionar MiniSEED del ZIP si hay más de uno",
            value=False,
            help="Si el ZIP contiene múltiples .ms/.mseed, se creará un dataset fusionado.",
            key="merge_zip_mseed",
        )
        zip_file: BytesIO | None = st.file_uploader(
            "Sube un .zip con la carpeta de archivos",
            accept_multiple_files=False,
            type=["zip"],
            help="Incluye en el ZIP archivos soportados (.ms/.mseed, .sac, .seg2/.sg2, .suds, .bin, .ss).",
            key="uploader_zip",
        )

        if zip_file is not None:
            mseed_loaded_zip: List[tuple[str, LoadedStream]] = []
            zip_loaded_names: List[str] = []
            imported = 0
            try:
                with zipfile.ZipFile(zip_file) as zf:
                    namelist = zf.namelist()
                    if not namelist:
                        st.warning("El ZIP está vacío.")
                    for member in namelist:
                        if member.endswith("/"):
                            continue  # carpeta
                        base = member.rsplit("/", 1)[-1]
                        ext = base.split(".")[-1].lower() if "." in base else ""
                        try:
                            data = zf.read(member)
                        except Exception as exc:
                            handle_error(exc, context=f"No se pudo leer {member} del ZIP")
                            continue
                        # Procesar según tipo
                        if ext in ACCEPTED_METADATA:
                            try:
                                metadata = load_kelunji_metadata(BytesIO(data))
                                session.metadata.setdefault("kelunji_metadata", {})[base] = metadata.raw
                                session.metadata["kelunji_last"] = metadata.raw
                                session.metadata.pop("earthquake_search_lat", None)
                                session.metadata.pop("earthquake_search_lon", None)
                                session.metadata.pop("earthquake_search_radius_km", None)
                                zip_loaded_names.append(f"Metadato Kelunji: {base}")
                                imported += 1
                            except Exception as exc:
                                handle_error(exc, context=f"No se pudo procesar metadato {base}")
                            continue

                        if ext in (ACCEPTED_MSEED | ACCEPTED_OTHER_WAVEFORMS | ACCEPTED_GEOCKO):
                            friendly = (ACCEPTED_MSEED | ACCEPTED_OTHER_WAVEFORMS | ACCEPTED_GEOCKO).get(ext, ext.upper())
                            try:
                                loaded = reader.load_bytes(buffer=BytesIO(data))
                            except Exception as exc:
                                handle_error(exc, context=f"No se pudo cargar {base} ({friendly}) desde ZIP")
                                continue
                            register_stream(stream=loaded.stream, name=base, summary=loaded.summary)
                            zip_loaded_names.append(f"{base} ({friendly}) desde ZIP")
                            imported += 1
                            if ext in ACCEPTED_MSEED:
                                mseed_loaded_zip.append((base, loaded))
                        else:
                            # Ignorar extensiones no soportadas
                            continue

                # Merge opcional para MiniSEED dentro del ZIP
                if do_zip_merge and mseed_loaded_zip:
                    try:
                        from obspy import Stream  # type: ignore
                    except Exception as exc:
                        st.warning(f"No se pudo importar ObsPy para merge del ZIP: {exc}")
                    else:
                        if len(mseed_loaded_zip) >= 2:
                            st_all = Stream()
                            for _, ls in mseed_loaded_zip:
                                st_all += ls.stream
                            try:
                                st_all.sort()
                            except Exception:
                                pass
                            try:
                                st_all.merge(method=1, fill_value=0.0)
                            except Exception as exc:
                                st.warning(f"No se pudo completar el merge automático desde ZIP: {exc}")
                            else:
                                merged_name = f"MERGED_MS_ZIP_{len(mseed_loaded_zip)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                header = f"Merged | {len(st_all)} traces (from {len(mseed_loaded_zip)} MiniSEED files in ZIP)"
                                summary_lines = [header, *(tr.stats.__str__() for tr in st_all)]
                                merged_summary = "\n".join(summary_lines)
                                register_stream(stream=st_all, name=merged_name, summary=merged_summary)
                                set_current_stream(merged_name, session=session)
                                st.success(f"Creado dataset fusionado desde ZIP: {merged_name}")
                        else:
                            st.info("Se requiere al menos 2 MiniSEED dentro del ZIP para fusionar.")

                if imported == 0:
                    st.info("No se encontraron archivos soportados dentro del ZIP.")
                else:
                    st.success(f"Importados {imported} archivos desde ZIP")
                    with st.expander("Ver detalle de archivos importados del ZIP", expanded=False):
                        st.markdown("\n".join(f"- {name}" for name in zip_loaded_names))
            except zipfile.BadZipFile as exc:
                handle_error(exc, context="Archivo ZIP inválido o corrupto")
    else:
        st.caption("Ingresa una o varias rutas (una por línea), p. ej.: C:/datos/s1\nC:/datos/s2. Se explorarán recursivamente.")
        cols_lp = st.columns([3, 1])
        with cols_lp[0]:
            local_paths_text = st.text_area("Rutas de carpetas", value="", key="uploader_local_paths", height=80)
        with cols_lp[1]:
            do_local_merge = st.checkbox("Fusionar MiniSEED", value=False, key="merge_local_mseed")
            do_scan = st.button("Importar carpetas", type="primary")

        if do_scan and local_paths_text.strip():
            from pathlib import Path
            reader = DataReader()
            supported_exts = set(
                list(ACCEPTED_MSEED.keys())
                + list(ACCEPTED_OTHER_WAVEFORMS.keys())
                + list(ACCEPTED_GEOCKO.keys())
                + list(ACCEPTED_METADATA.keys())
            )
            paths = [line.strip().strip('"') for line in local_paths_text.splitlines() if line.strip()]
            all_files = []
            invalid = []
            for ptxt in paths:
                p = Path(ptxt)
                if not p.exists() or not p.is_dir():
                    invalid.append(ptxt)
                    continue
                for path in p.rglob("*"):
                    if path.is_file():
                        ext = path.suffix.lower().lstrip(".")
                        if ext in supported_exts:
                            all_files.append(path)
            if invalid:
                st.warning("Rutas inválidas/ no carpetas: " + ", ".join(invalid))
            if not all_files:
                st.info("No se encontraron archivos soportados en las carpetas indicadas.")
            else:
                mseed_loaded_local: List[tuple[str, LoadedStream]] = []
                local_loaded_names: List[str] = []
                imported = 0
                for path in all_files:
                    ext = path.suffix.lower().lstrip(".")
                    if ext in ACCEPTED_METADATA:
                        try:
                            with path.open("rb") as fh:
                                metadata = load_kelunji_metadata(fh)
                            session.metadata.setdefault("kelunji_metadata", {})[path.name] = metadata.raw
                            session.metadata["kelunji_last"] = metadata.raw
                            session.metadata.pop("earthquake_search_lat", None)
                            session.metadata.pop("earthquake_search_lon", None)
                            session.metadata.pop("earthquake_search_radius_km", None)
                            local_loaded_names.append(f"Metadato Kelunji: {path.name}")
                            imported += 1
                        except Exception as exc:
                            handle_error(exc, context=f"No se pudo procesar metadato {path.name}")
                        continue
                    # Waveforms/Gecko
                    try:
                        loaded = reader.load_files([path])[0]
                    except Exception as exc:
                        handle_error(exc, context=f"No se pudo cargar {path.name}")
                        continue
                    register_stream(stream=loaded.stream, name=path.name, summary=loaded.summary)
                    local_loaded_names.append(f"{path.name}")
                    imported += 1
                    if ext in ACCEPTED_MSEED:
                        mseed_loaded_local.append((path.name, loaded))

                if do_local_merge and mseed_loaded_local:
                    try:
                        from obspy import Stream  # type: ignore
                    except Exception as exc:
                        st.warning(f"No se pudo importar ObsPy para merge local: {exc}")
                    else:
                        if len(mseed_loaded_local) >= 2:
                            st_all = Stream()
                            for _, ls in mseed_loaded_local:
                                st_all += ls.stream
                            try:
                                st_all.sort()
                            except Exception:
                                pass
                            try:
                                st_all.merge(method=1, fill_value=0.0)
                            except Exception as exc:
                                st.warning(f"No se pudo completar el merge local: {exc}")
                            else:
                                merged_name = f"MERGED_MS_LOCAL_{len(mseed_loaded_local)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                header = f"Merged | {len(st_all)} traces (from {len(mseed_loaded_local)} MiniSEED files in folders)"
                                summary_lines = [header, *(tr.stats.__str__() for tr in st_all)]
                                merged_summary = "\n".join(summary_lines)
                                register_stream(stream=st_all, name=merged_name, summary=merged_summary)
                                set_current_stream(merged_name, session=session)
                                st.success(f"Creado dataset fusionado desde carpetas: {merged_name}")
                        else:
                            st.info("Se requieren al menos 2 MiniSEED en total para fusionar.")

                if imported == 0:
                    st.info("No se cargaron archivos desde las carpetas indicadas.")
                else:
                    st.success(f"Importados {imported} archivos desde carpetas")
                    with st.expander("Ver detalle de archivos importados (carpetas)", expanded=False):
                        st.markdown("\n".join(f"- {name}" for name in local_loaded_names))



if __name__ == "__main__":  # pragma: no cover
    main()
