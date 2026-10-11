"""UploadBox (Appendix B): add new readings, see errors in plain words, see what changed."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from scoring.config import repo_path

SAMPLE = "data/samples/new_readings_sample.csv"
UPLOAD_KEY = "upload_file"
SAMPLE_KEY = "use_sample"


def pending_upload() -> tuple[bytes | None, str]:
    """Bytes of the uploaded file (or the sample) from session state, and a label."""
    file = st.session_state.get(UPLOAD_KEY)
    if file is not None:
        return file.getvalue(), file.name
    if st.session_state.get(SAMPLE_KEY):
        return repo_path(SAMPLE).read_bytes(), "sample file (invented values)"
    return None, ""


def _use_sample() -> None:
    st.session_state[SAMPLE_KEY] = True


def _clear() -> None:
    st.session_state[SAMPLE_KEY] = False
    st.session_state.pop(UPLOAD_KEY, None)


def upload_panel(state: dict[str, Any]) -> None:
    """Render the upload box. `state` holds label, result (UploadResult), changes, error."""
    label, result = state.get("label"), state.get("result")
    expanded = bool(label)
    with st.expander("Add new readings and re-score (same columns as the MPPCB CSV)",
                     expanded=expanded):
        st.caption("Required columns: site, year, festival, phase, parameter, value (or flag). "
                   "Uploaded rows are tagged 'user-supplied' and never overwrite a report "
                   "value. Nothing leaves this computer.")
        st.file_uploader("Drop a CSV here", type=["csv"], key=UPLOAD_KEY)
        cols = st.columns(3)
        cols[0].button("Try the sample file", on_click=_use_sample,
                       help="Durga 2026 readings with INVENTED values, for demonstration")
        cols[1].download_button("Download the sample CSV", repo_path(SAMPLE).read_bytes(),
                                "new_readings_sample.csv", mime="text/csv")
        if label:
            cols[2].button("Remove uploaded readings", on_click=_clear)
        if state.get("error"):
            st.error(state["error"])
        elif result is not None and not result.ok:
            st.error(f"Could not use **{label}**. Please fix these and upload again:\n\n"
                     + "\n".join(f"- {e}" for e in result.errors))
        elif result is not None:
            st.success(f"Re-scored with **{label}**. " + " ".join(result.notes))
            changes = pd.DataFrame(state["changes"])
            changed = changes[changes["changed"]].drop(columns="changed")
            st.markdown("**What changed** (before → after)")
            st.dataframe(changed if len(changed) else changes.drop(columns="changed"),
                         hide_index=True, width="stretch")
