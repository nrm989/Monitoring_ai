"""Dashboard quotidien Streamlit.
Usage: streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).parent
CSV = BASE / "data" / "history.csv"
LATEST = BASE / "data" / "latest.json"

st.set_page_config(page_title="Monitoring MMSP / Idarati", layout="wide")
st.title("📊 Monitoring quotidien — ai.mmsp.gov.ma & chatbot.idarati.ma")
st.caption("Uptime • Performance • SSL • Headers sécurité — actualisez avec le bouton ci-dessous.")

col_btn, _ = st.columns([1, 5])
with col_btn:
    if st.button("🔄 Rafraîchir"):
        st.rerun()

# --- Statut actuel ---
if LATEST.exists():
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
else:
    st.warning("Aucune donnée. Lancez d'abord : `python monitor.py`")
    st.stop()

cols = st.columns(len(latest))
for c, r in zip(cols, latest):
    ok = bool(r["up"])
    c.metric(
        label=f"{'🟢' if ok else '🔴'} {r['name']}",
        value="EN LIGNE" if ok else "HORS LIGNE",
        delta=f"HTTP {r['status_code']} • {r['response_time_s']}s",
    )
    c.write(f"[{r['url']}]({r['url']})")
    c.write(f"🔒 SSL : {r['ssl_days_left']} jours restants ({r['ssl_issuer']})")
    c.write(f"🛡️ Headers : {r['sec_score']} — manquants : {r['sec_missing'] or 'aucun'}")
    # Statut fonctionnel chatbot (POST /api/agent/chat "Bonjour")
    if str(r.get("chat_ok", "")) != "":
        if r["chat_ok"] == 1:
            c.success(f"💬 Chatbot fonctionnel : OK en {r['chat_time_s']}s — « {r.get('chat_preview','')[:120]}… »")
        else:
            c.error(f"💬 Chatbot fonctionnel : KO — {r.get('chat_error','')}")
    if r["error"]:
        c.error(r["error"])

st.divider()

# --- Historique ---
if not CSV.exists():
    st.info("Pas encore d'historique.")
    st.stop()

df = pd.read_csv(CSV, parse_dates=["timestamp"])
df = df.sort_values("timestamp")

# Uptime % sur la période chargée
st.subheader("📈 Disponibilité & temps de réponse")
for name, g in df.groupby("name"):
    uptime = g["up"].mean() * 100
    avg_rt = g["response_time_s"].mean()
    st.write(f"**{name}** — uptime {uptime:.2f}% sur {len(g)} checks • réponse moyenne {avg_rt:.2f}s")

# Courbes temps de réponse
pivot_rt = df.pivot_table(index="timestamp", columns="name", values="response_time_s", aggfunc="mean")
st.line_chart(pivot_rt)

# Statut UP/DOWN dans le temps
pivot_up = df.pivot_table(index="timestamp", columns="name", values="up", aggfunc="max")
st.bar_chart(pivot_up)

with st.expander("Voir l'historique brut"):
    st.dataframe(df.sort_values("timestamp", ascending=False), use_container_width=True)

st.caption("Astuce : ce dashboard est fait pour être consulté en direct. Pour le mail quotidien, envoyez le rapport HTML (report.py) plutôt qu'une capture d'écran — plus léger, cliquable et archivable.")
