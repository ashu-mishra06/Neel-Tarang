"""UploadBox (Appendix B): add new readings, see errors in plain words, see what changed."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from scoring.config import repo_path
from ui import i18n

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


def upload_panel(state: dict[str, Any], lang: str = "en") -> None:
    """Upload box (sidebar). `state` holds label, result (UploadResult), error."""
    label, result = state.get("label"), state.get("result")
    st.caption(i18n.t("up_help", lang))
    st.file_uploader(i18n.t("up_drop", lang), type=["csv"], key=UPLOAD_KEY)
    st.button(i18n.t("up_sample", lang), on_click=_use_sample, width="stretch")
    st.download_button(i18n.t("up_download", lang), repo_path(SAMPLE).read_bytes(),
                       "new_readings_sample.csv", mime="text/csv", width="stretch")
    if label:
        st.button(i18n.t("up_remove", lang), on_click=_clear, width="stretch")
    if state.get("error"):
        st.error(state["error"])
    elif result is not None and not result.ok:
        st.error(f"Could not use **{label}**. Please fix these and upload again:\n\n"
                 + "\n".join(f"- {e}" for e in result.errors))
    elif result is not None:
        st.success(f"Re-scored with **{label}**. " + " ".join(result.notes))


def changes_table(state: dict[str, Any], label: str) -> None:
    """'What changed' after a successful upload (shown above the ranking)."""
    changes = pd.DataFrame(state["changes"])
    changed = changes[changes["changed"]].drop(columns="changed")
    st.info(f"Showing scores that include uploaded readings from {label} "
            "(marked 'user-supplied' in the evidence).")
    st.markdown("**What changed** (before → after)")
    st.dataframe(changed if len(changed) else changes.drop(columns="changed"),
                 hide_index=True, width="stretch")
