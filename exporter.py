"""Exporter Prometheus — monitoring continu des 2 sites.
Garde toutes les infos du monitoring quotidien : HTTP, temps réponse,
keyword, SSL, headers sécu, test fonctionnel chatbot POST /api/agent/chat.

Usage local sans docker : python exporter.py  (http://localhost:8000/metrics)
Via docker-compose : scrape toutes les 30s par Prometheus.
"""
import os
import time
import traceback

from prometheus_client import Gauge, Info, start_http_server

from monitor import CFG, check_one

INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "30"))
PORT = int(os.getenv("EXPORTER_PORT", "8000"))

LABELS = ["site", "url"]

g_up = Gauge("website_up", "1 = en ligne (HTTP OK + keyword + chatbot OK), 0 = DOWN", LABELS)
g_status = Gauge("website_status_code", "Code HTTP (0 = exception réseau)", LABELS)
g_rt = Gauge("website_response_time_seconds", "Temps de réponse HTTP", LABELS)
g_size = Gauge("website_size_bytes", "Taille du body HTTP", LABELS)
g_kw = Gauge("website_keyword_ok", "1 si mot-clé attendu trouvé dans le HTML", LABELS)
g_ssl_days = Gauge("website_ssl_days_left", "Jours restants certificat SSL (-1 = erreur)", LABELS)
g_sec_ok = Gauge("website_security_headers_present", "Nombre de headers sécu présents", LABELS)
g_sec_total = Gauge("website_security_headers_total", "Nombre de headers sécu suivis", LABELS)
g_chat_ok = Gauge("website_chat_ok", "1 = chatbot répond à 'Bonjour', 0 = KO, -1 = non testé", LABELS)
g_chat_rt = Gauge("website_chat_response_time_seconds", "Temps de réponse du chatbot", LABELS)
i_ssl = Info("website_ssl", "Infos certificat SSL", LABELS)
i_check = Info("website_check", "Dernier détail : erreur, headers manquants, preview chatbot", LABELS)


def collect_once():
    for target in CFG["targets"]:
        try:
            r = check_one(target)
        except Exception as e:
            print(f"check_one failed for {target.get('name')}: {e}")
            traceback.print_exc()
            continue
        lb = {"site": r["name"], "url": r["url"]}
        g_up.labels(**lb).set(r["up"])
        g_status.labels(**lb).set(r["status_code"])
        g_rt.labels(**lb).set(r["response_time_s"])
        g_size.labels(**lb).set(r["size_bytes"])
        g_kw.labels(**lb).set(r["keyword_ok"])
        g_ssl_days.labels(**lb).set(r["ssl_days_left"])
        try:
            present, total = r["sec_score"].split("/")
            g_sec_ok.labels(**lb).set(int(present))
            g_sec_total.labels(**lb).set(int(total))
        except Exception:
            pass
        chat_raw = str(r.get("chat_ok", ""))
        if chat_raw == "":
            g_chat_ok.labels(**lb).set(-1)
            g_chat_rt.labels(**lb).set(0)
        else:
            g_chat_ok.labels(**lb).set(int(float(chat_raw)))
            try:
                g_chat_rt.labels(**lb).set(float(r.get("chat_time_s") or 0))
            except Exception:
                g_chat_rt.labels(**lb).set(0)
        i_ssl.labels(**lb).info({
            "expires": r.get("ssl_expires", ""),
            "issuer": r.get("ssl_issuer", ""),
        })
        i_check.labels(**lb).info({
            "error": (r.get("error") or "none")[:200],
            "sec_missing": (r.get("sec_missing") or "none")[:200],
            "chat_preview": (r.get("chat_preview") or "na")[:200],
            "chat_error": (r.get("chat_error") or "none")[:200],
        })
        state = "UP" if r["up"] else "DOWN"
        print(f"[{state}] {r['name']} HTTP {r['status_code']} {r['response_time_s']}s "
              f"SSL {r['ssl_days_left']}j chat={r.get('chat_ok','-')}", flush=True)


if __name__ == "__main__":
    start_http_server(PORT)
    print(f"Exporter : http://localhost:{PORT}/metrics — scrape toutes les {INTERVAL}s", flush=True)
    while True:
        collect_once()
        time.sleep(INTERVAL)
