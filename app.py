import json
from pathlib import Path

import streamlit as st

import scopeguard as sg

st.set_page_config(page_title="ScopeGuard", page_icon="🛡️", layout="wide")
ROOT = Path(__file__).parent
SAMPLES = {"Load vague brief": "vague_brief.txt", "Load clear brief": "clear_brief.txt"}
ICON = {"low": "🟢", "medium": "🟡", "high": "🔴"}


def load_sample(label):
    st.session_state["brief"] = (ROOT / "samples" / SAMPLES[label]).read_text(encoding="utf-8")


with st.sidebar:
    st.header("🛡️ ScopeGuard")
    st.caption(f"Model: **{sg.MODEL}** (local, via Ollama)")
    ok, msg = sg.check_model()
    (st.success if ok else st.error)(msg)
    st.divider()
    for label in SAMPLES:
        st.button(label, on_click=load_sample, args=(label,))
    st.caption("Your client's message never leaves this computer.")

st.title("🛡️ ScopeGuard")
st.write("**Paste a client's project message. Find scope-creep risks before you quote a price.**")

st.text_area("Client message", key="brief", height=230,
             placeholder="Paste the client's message from Upwork, Fiverr, WhatsApp or email...")

if st.button("Analyze brief", type="primary"):
    try:
        with st.spinner("Local model is reading the message (10-60 seconds)..."):
            st.session_state["result"] = sg.analyze(st.session_state.get("brief", ""))
    except sg.ScopeGuardError as e:
        st.session_state.pop("result", None)
        st.error(str(e))

res = st.session_state.get("result")
if res:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk score", f"{res['score']}/100")
    c2.metric("Risk level", res["level"])
    c3.metric("Verified flags", len(res["risk_flags"]))
    c4.metric("Removed (quote not found)", res["dropped_flags"])

    st.subheader("Risky phrases in the client message")
    st.markdown(res["highlighted"], unsafe_allow_html=True)
    st.caption("Only phrases that really exist in the message are highlighted. "
               "Flags with invented quotes are removed by code.")

    left, right = st.columns(2)
    with left:
        st.subheader("Summary")
        st.write(res["project_summary"])
        st.subheader("Deliverables requested")
        for d in res["deliverables"]:
            st.markdown(f"- {d}")
        st.subheader("Missing information")
        for m in res["missing_info"]:
            st.markdown(f"- {m}")
    with right:
        st.subheader("Risk flags")
        if not res["risk_flags"]:
            st.info("No verified risk flags found.")
        for f in res["risk_flags"]:
            with st.expander(f"{ICON[f['severity']]} {f['category']} — “{f['quote']}”"):
                st.write(f["why"])
        st.subheader("Questions to ask the client")
        for q in res["clarifying_questions"]:
            st.markdown(f"- {q}")

    st.subheader("Draft reply (edit before sending)")
    st.text_area("Reply", value=res["draft_reply"], height=200, label_visibility="collapsed")
    export = {k: v for k, v in res.items() if k not in ("highlighted",)}
    st.download_button("Download analysis (JSON)",
                       json.dumps(export, indent=2, default=list), "scopeguard_analysis.json")
