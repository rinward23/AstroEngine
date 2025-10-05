"""Streamlit app for evaluating horary cases."""

from __future__ import annotations

from datetime import datetime

import streamlit as st
from fpdf import FPDF

from astroengine.engine.horary import GeoLocation, evaluate_case
from astroengine.engine.horary.profiles import list_profiles

from .components import location_picker

st.set_page_config(page_title="Horary Toolkit", layout="wide")


def _profile_names() -> list[str]:
    return [profile.name for profile in list_profiles()]


def _render_pdf(result: dict[str, object], notes: str, tags: list[str]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Horary Judgement", ln=True)

    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Question: {result['question']}", ln=True)
    pdf.cell(0, 8, f"Asked at: {result['asked_at']}", ln=True)
    pdf.cell(0, 8, f"Profile: {result['profile']}", ln=True)
    pdf.cell(0, 8, f"House system: {result['house_system']}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Radicality Checks", ln=True)
    pdf.set_font("Helvetica", size=11)
    for check in result["radicality"]:
        status = "⚠" if check["flag"] else "✔"
        pdf.multi_cell(0, 6, f"{status} {check['code']}: {check['reason']}")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Judgement", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Score: {result['judgement']['score']:.2f}", ln=True)
    pdf.cell(0, 8, f"Outcome: {result['judgement']['classification']}", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top Contributions", ln=True)
    pdf.set_font("Helvetica", size=11)
    for entry in result["judgement"]["contributions"][:10]:
        pdf.multi_cell(
            0,
            6,
            f"{entry['label']} (score {entry['score']:.2f}): {entry['rationale']}",
        )
    pdf.ln(2)

    if notes:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Notes", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 6, notes)
    if tags:
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 6, f"Tags: {', '.join(tags)}", ln=True)

    return pdf.output(dest="S").encode("latin-1")


def main() -> None:
    st.title("Horary Judgement Toolkit")
    st.write("Cast the chart for a horary question, inspect radicality checks, and review the judgement summary.")

    with st.sidebar:
        st.header("Case Metadata")
        profiles = _profile_names() or ["Lilly"]
        profile_name = st.selectbox("Tradition profile", profiles, index=0)
        house_system = st.selectbox("House system", ["placidus", "regiomontanus", "whole_sign"])
        quesited_house = st.number_input("Quesited house", min_value=1, max_value=12, value=7)
        notes = st.text_area("Notes", "")
        tags = st.multiselect("Sentiment tags", ["hopeful", "challenging", "delayed", "swift", "reconsider"])
        attachments = st.file_uploader("Attachments", accept_multiple_files=True)
        if attachments:
            st.caption(f"Loaded {len(attachments)} attachment(s) for reference.")

    location_picker(
        "Event location",
        default_query="London, United Kingdom",
        state_prefix="horary_location",
        help="Uses the atlas geocoder; DST status reflects the current date.",
    )
    lat_default = float(st.session_state.get("horary_location_lat", 51.5074))
    lon_default = float(st.session_state.get("horary_location_lon", -0.1278))

    with st.form("horary_form"):
        question = st.text_input("Question", "Will I get the job?")
        asked_at = st.datetime_input("Moment of question", datetime.utcnow())
        col1, col2, col3 = st.columns(3)
        with col1:
            latitude = st.number_input("Latitude", value=lat_default)
        with col2:
            longitude = st.number_input("Longitude", value=lon_default)
        with col3:
            altitude = st.number_input("Altitude (m)", value=0.0)
        submit = st.form_submit_button("Evaluate")

    if submit:
        st.session_state["horary_location_lat"] = float(latitude)
        st.session_state["horary_location_lon"] = float(longitude)
        with st.spinner("Casting chart and evaluating testimonies..."):
            result = evaluate_case(
                question=question,
                asked_at=asked_at,
                location=GeoLocation(latitude=latitude, longitude=longitude, altitude=altitude),
                house_system=house_system,
                quesited_house=int(quesited_house),
                profile=profile_name,
            )
        st.success("Horary chart computed.")

        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Judgement")
            st.metric("Score", f"{result['judgement']['score']:.1f}")
            st.metric("Outcome", result["judgement"]["classification"])
            st.subheader("Planetary Hour")
            hour = result["planetary_hour"]
            st.write(
                f"Hour ruler: **{hour['ruler']}** (Day ruler: {hour['day_ruler']})"
            )
            st.write(
                f"Hour span: {hour['start']} – {hour['end']}"
            )
        with col_right:
            st.subheader("Radicality")
            for check in result["radicality"]:
                icon = "⚠️" if check["flag"] else "✅"
                st.write(f"{icon} **{check['code']}** — {check['reason']}")

        st.subheader("Significators")
        sig_cols = st.columns(3)
        sig_map = {
            "Querent": result["significators"]["querent"],
            "Quesited": result["significators"]["quesited"],
            "Moon": result["significators"]["moon"],
        }
        for (label, data), col in zip(sig_map.items(), sig_cols):
            with col:
                st.markdown(f"### {label}")
                st.write(
                    f"{data['body']} @ {data['longitude']:.2f}°, House {data['house']}"
                )
                st.write(f"Dignity score: {data['dignities']['score']:.1f}")
                if data["receptions"]:
                    st.write("Receptions:")
                    for target, kinds in data["receptions"].items():
                        st.write(f"• {target}: {', '.join(kinds)}")

        with st.expander("Judgement contributions", expanded=False):
            for entry in result["judgement"]["contributions"]:
                st.write(
                    f"{entry['label']} — score {entry['score']:.2f} (weight {entry['weight']}, value {entry['value']})"
                )
                st.caption(entry["rationale"])

        if result.get("aspect"):
            st.subheader("Primary aspect")
            contact = result["aspect"]
            st.write(
                f"{contact['body_a']} and {contact['body_b']} in {contact['aspect']} (orb {contact['orb']:.2f}°)"
            )
            if contact["perfection_time"]:
                st.caption(f"Perfection at {contact['perfection_time']}")

        pdf_bytes = _render_pdf(result, notes, tags)
        st.download_button(
            "Download judgement PDF",
            data=pdf_bytes,
            file_name="horary-judgement.pdf",
            mime="application/pdf",
        )


if __name__ == "__main__":
    main()

