from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Iterable, List

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Orb & Severity Editor", page_icon="⚙️", layout="wide")
st.title("Orb & Severity Editor ⚙️")
api = APIClient()

# ------------------------------ Utility -----------------------------------


def _allowed_policy_keys(include_name: bool = True) -> Iterable[str]:
    keys: List[str] = ["description", "per_object", "per_aspect", "adaptive_rules"]
    if include_name:
        keys.insert(0, "name")
    return keys


def sanitise_policy(payload: Dict[str, Any], include_name: bool = True) -> Dict[str, Any]:
    """Return a shallow copy containing only fields accepted by the API."""

    allowed = set(_allowed_policy_keys(include_name=include_name))
    return {key: payload[key] for key in allowed if key in payload}

# ------------------------------ Helpers ------------------------------------
DEFAULT_ASPECTS = ["conjunction","opposition","square","trine","sextile","quincunx","semisquare","sesquisquare","quintile","biquintile"]
DEFAULT_WEIGHTS = {"conjunction":1.0,"opposition":0.95,"square":0.9,"trine":0.8,"sextile":0.6,"quincunx":0.5,"semisquare":0.45,"sesquisquare":0.45,"quintile":0.4,"biquintile":0.4}

# Cosine taper (same shape as backend)
def taper_by_orb(orb: float, limit: float) -> float:
    if limit <= 0: return 0.0
    x = max(0.0, min(1.0, orb/limit))
    return 0.5 * (1.0 + np.cos(np.pi * x)) if x < 1.0 else 0.0

# Severity proxy in UI (weight × taper). Backend may add modifiers later.
def sev_ui(aspect: str, orb: float, limit: float, weights: Dict[str, float]) -> float:
    w = float(weights.get(aspect, DEFAULT_WEIGHTS.get(aspect, 0.5)))
    return max(0.0, w * taper_by_orb(orb, limit))

# ------------------------------ Sidebar ------------------------------------
st.sidebar.header("Policies")

# Load list
try:
    pol_list = api.list_policies()
    items = pol_list.get("items", [])
except Exception as e:
    st.sidebar.error(f"Failed to load policies: {e}")
    items = []

id_by_name = {f"{p['name']} (#{p['id']})": p["id"] for p in items}
options = ["— New Policy —"] + list(id_by_name.keys())
choice = st.sidebar.selectbox("Select policy", options)

is_new = choice == "— New Policy —"
policy: Dict[str, Any] = {
    "name": "classic",
    "description": "Default classical orbs",
    "per_object": {"Sun": 8.0, "Moon": 6.0},
    "per_aspect": {"conjunction": 8.0, "opposition": 7.0, "square": 6.0, "trine": 6.0, "sextile": 4.0, "quincunx": 3.0},
    "adaptive_rules": {"luminaries_factor": 0.9, "outers_factor": 1.1, "minor_aspect_factor": 0.9},
}

if not is_new:
    try:
        policy = dict(api.get_policy(id_by_name[choice]))
    except Exception as e:
        st.sidebar.error(f"Failed to fetch policy: {e}")

# ------------------------------ Form ---------------------------------------
st.subheader("Edit Policy")
col1, col2 = st.columns(2)
with col1:
    policy["name"] = st.text_input("Name", value=policy.get("name", ""), help="Unique policy name")
    policy["description"] = st.text_input("Description", value=policy.get("description", ""))
with col2:
    with st.expander("Adaptive rules"):
        ar = policy.get("adaptive_rules", {}) or {}
        ar["luminaries_factor"] = st.slider("luminaries_factor", 0.5, 1.5, float(ar.get("luminaries_factor", 0.9)), 0.05)
        ar["outers_factor"] = st.slider("outers_factor", 0.5, 1.5, float(ar.get("outers_factor", 1.1)), 0.05)
        ar["minor_aspect_factor"] = st.slider("minor_aspect_factor", 0.5, 1.5, float(ar.get("minor_aspect_factor", 0.9)), 0.05)
        policy["adaptive_rules"] = ar

st.markdown("### Per‑Aspect Orbs (deg)")
existing_aspects = list(DEFAULT_ASPECTS)
for asp_name in (policy.get("per_aspect", {}) or {}).keys():
    if asp_name not in existing_aspects:
        existing_aspects.append(asp_name)

pa = policy.get("per_aspect", {}) or {}
for asp in existing_aspects:
    pa[asp] = st.number_input(
        f"{asp}",
        min_value=0.1,
        max_value=12.0,
        value=float(pa.get(asp, DEFAULT_WEIGHTS.get(asp, 0.5) * 10)),
        step=0.1,
    )
policy["per_aspect"] = pa
available_aspects = existing_aspects

with st.expander("Per‑Object Orbs (deg)", expanded=False):
    po = policy.get("per_object", {}) or {}
    # Simple add/edit rows
    new_key = st.text_input("Add/Update object name", value="")
    new_val = st.number_input("Orb (deg)", min_value=0.1, max_value=12.0, value=6.0, step=0.1)
    if st.button("Add/Update Object Orb") and new_key.strip():
        po[new_key.strip()] = float(new_val)

    if po:
        removal_options = ["—"] + sorted(po)
        selected_remove = st.selectbox("Remove object", removal_options, index=0)
        if selected_remove != "—" and st.button("Remove Selected Object"):
            po.pop(selected_remove, None)

    # Render current mapping
    if po:
        df_po = pd.DataFrame({"object": list(po.keys()), "orb": list(po.values())})
        st.dataframe(df_po, use_container_width=True, hide_index=True)
    policy["per_object"] = po

# ------------------------------ Actions ------------------------------------
colA, colB, colC, colD = st.columns(4)
with colA:
    if st.button("Save", type="primary"):
        try:
            if is_new:
                res = api.create_policy(sanitise_policy(policy, include_name=True))
                st.success(f"Created policy #{res['id']}")
            else:
                res = api.update_policy(id_by_name[choice], sanitise_policy(policy, include_name=False))
                st.success("Updated policy")
        except Exception as e:
            st.error(f"Save failed: {e}")
with colB:
    if not is_new and st.button("Delete", type="secondary"):
        try:
            api.delete_policy(id_by_name[choice])
            st.success("Deleted policy. Reload the page to refresh list.")
        except Exception as e:
            st.error(f"Delete failed: {e}")
with colC:
    if not is_new and st.button("Duplicate"):
        try:
            clone = sanitise_policy(policy, include_name=True)
            clone["name"] = f"{clone['name']}_copy"
            res = api.create_policy(clone)
            st.success(f"Duplicated as #{res['id']}")
        except Exception as e:
            st.error(f"Duplicate failed: {e}")
with colD:
    # Import/Export JSON
    exp = json.dumps(sanitise_policy(policy, include_name=True), indent=2).encode("utf-8")
    st.download_button("Export JSON", exp, file_name=f"orb_policy_{policy.get('name','unnamed')}.json", mime="application/json")
    up = st.file_uploader("Import JSON", type=["json"], label_visibility="collapsed")
    if up:
        try:
            policy.update(json.load(up))
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

# ------------------------------ Preview: Severity Curve ---------------------
st.subheader("Preview — Severity vs Orb")
col1, col2, col3 = st.columns(3)
default_aspect = "sextile" if "sextile" in available_aspects else available_aspects[0]
asp = col1.selectbox("Aspect", available_aspects, index=available_aspects.index(default_aspect))
limit = float(policy.get("per_aspect", {}).get(asp, 3.0))
weights = DEFAULT_WEIGHTS  # placeholder; you can wire SeverityProfile later

orbs = np.linspace(0.0, max(0.1, limit), 100)
sevs = [sev_ui(asp, o, limit, weights) for o in orbs]
fig = px.line(x=orbs, y=sevs, labels={"x":"orb (deg)", "y":"severity"}, title=f"{asp} — severity taper (limit={limit:.2f}°)")
st.plotly_chart(fig, use_container_width=True, theme="streamlit")

# ------------------------------ Preview: Sample Search ----------------------
st.subheader("Preview — Sample Aspect Search (optional)")
with st.expander("Run a quick 14‑day sample to see effect on hit counts/avg severity", expanded=False):
    objs = st.multiselect("Objects", ["Sun","Moon","Mercury","Venus","Mars"], default=["Sun","Moon","Venus","Mars"])  # small set
    step_minutes = st.slider("Step (minutes)", 5, 120, 60, 5)
    if st.button("Run Sample Search"):
        now = datetime.now(timezone.utc)
        payload = {
            "objects": objs,
            "aspects": [asp],
            "harmonics": [],
            "window": {"start": (now).isoformat(), "end": (now + timedelta(days=14)).isoformat()},
            "step_minutes": step_minutes,
            "limit": 500,
            "offset": 0,
            "order_by": "time",
            "orb_policy_inline": {
                "per_object": policy.get("per_object", {}),
                "per_aspect": policy.get("per_aspect", {}),
                "adaptive_rules": policy.get("adaptive_rules", {}),
            },
        }
        try:
            data = api.aspects_search(payload)
            hits = data.get("hits", [])
            df = pd.DataFrame(hits)
            if df.empty:
                st.info("No hits in the sample window.")
            else:
                st.write(f"Found {len(df)} hits.")
                st.dataframe(df[["exact_time","a","b","aspect","orb","severity"]], use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Sample search failed: {e}")
