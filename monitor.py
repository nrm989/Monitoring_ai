"""Monitoring quotidien : dispo + perf + SSL + headers sécurité.
Usage: python monitor.py
Sorties: data/history.csv (append), data/latest.json
"""
import csv
import json
import socket
import ssl
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

BASE = Path(__file__).parent
CFG = yaml.safe_load((BASE / "config.yaml").read_text(encoding="utf-8"))

CSV_PATH = BASE / CFG["settings"]["history_csv"]
JSON_PATH = BASE / CFG["settings"]["latest_json"]
SEC_HEADERS = CFG["settings"]["security_headers"]


def check_ssl_expiry(hostname: str, port: int = 443, timeout: int = 10):
    """Retourne (expire_le, jours_restants, issuer) ou (None, None, None) en cas d'échec."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        exp_str = cert.get("notAfter")  # ex: 'Sep  7 16:59:25 2027 GMT'
        exp = datetime.strptime(exp_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days = (exp - datetime.now(timezone.utc)).days
        issuer = dict(x[0] for x in cert.get("issuer", ()))
        issuer_str = issuer.get("organizationName", issuer.get("commonName", "?"))
        return exp.isoformat(), days, issuer_str
    except Exception as e:
        return None, None, f"ERR: {e}"


def check_chatbot_functional(cfg: dict, timeout: int = 60):
    """Test fonctionnel Idarati : GET /api/agent/session + POST /api/agent/chat (SSE).

    Retourne (ok: bool, elapsed_s: float, preview: str, error: str).
    Découvert dans /assets/index-*.js : base `/api/agent`, events SSE
    `token` / `done` / `error`.
    """
    base = (cfg.get("base_url") or "").rstrip("/")
    message = cfg.get("message", "Bonjour")
    expect = [w.strip().lower() for w in (cfg.get("expect_contains") or "").split(",") if w.strip()]
    t0 = time.time()
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": CFG["settings"]["user_agent"],
            "Origin": base,
            "Referer": base + "/",
            "Accept": "text/event-stream",
        })
        # 1. Bootstrap session (200 {"status":"ok","required":false} observé)
        s.get(f"{base}/api/agent/session", timeout=15)

        # 2. Question test
        payload = {
            "user_text": message,
            "session_id": str(uuid.uuid4()),
            "history": [],
            "is_first_question": True,
            "input_mode": "text",
        }
        r = s.post(f"{base}/api/agent/chat", json=payload, timeout=timeout, stream=True)
        if r.status_code == 429:
            return False, round(time.time() - t0, 2), "", "HTTP 429 rate_limit"
        if not r.ok:
            return False, round(time.time() - t0, 2), "", f"HTTP {r.status_code}"

        full_text, done_text = "", ""
        for raw_line in r.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            try:
                evt = json.loads(line[5:].strip())
            except Exception:
                continue
            if evt.get("type") == "token":
                full_text += evt.get("delta", "")
            elif evt.get("type") == "done":
                done_text = evt.get("text") or full_text
                break
            elif evt.get("type") == "error":
                return False, round(time.time() - t0, 2), full_text[:200], f"stream error: {evt.get('message', evt.get('code', '?'))}"

        elapsed = round(time.time() - t0, 2)
        text = (done_text or full_text).strip()
        if not text:
            return False, elapsed, "", "reponse vide (pas d'event done)"
        if expect and not any(w in text.lower() for w in expect):
            return False, elapsed, text[:200], f"contenu inattendu (attendu un de: {expect})"
        return True, elapsed, text[:200], ""
    except Exception as e:
        return False, round(time.time() - t0, 2), "", f"{type(e).__name__}: {e}"


def check_one(target: dict):
    url = target["url"]
    name = target["name"]
    timeout = target.get("timeout", 20)
    keyword = target.get("keyword", "")
    host = urlparse(url).hostname or ""

    t0 = time.time()
    try:
        r = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": CFG["settings"]["user_agent"]},
        )
        elapsed = round(time.time() - t0, 2)
        status = r.status_code
        size = len(r.content or b"")
        final_url = r.url
        headers = dict(r.headers)
        keyword_ok = (keyword.lower() in r.text.lower()) if keyword else True
        ok = (200 <= status < 400) and keyword_ok
        error = "" if ok else f"HTTP {status}" + ("" if keyword_ok else " + keyword manquant")
    except Exception as e:  # DOWN / timeout / DNS
        elapsed, status, size, final_url, headers = round(time.time() - t0, 2), 0, 0, url, {}
        keyword_ok, ok, error = False, False, f"{type(e).__name__}: {e}"

    ssl_exp, ssl_days, ssl_issuer = check_ssl_expiry(host)

    present = [h for h in SEC_HEADERS if h in headers]
    missing = [h for h in SEC_HEADERS if h not in headers]

    # --- Test fonctionnel chatbot (optionnel, seul Idarati l'active) ---
    ftest = target.get("functional_test") or {}
    if ftest.get("enabled"):
        chat_ok, chat_time, chat_preview, chat_error = check_chatbot_functional(
            ftest, timeout=int(ftest.get("timeout", 60))
        )
        # Un chatbot qui répond 200 mais ne répond pas = DOWN fonctionnel
        if ok and not chat_ok:
            ok = False
            error = f"Chatbot KO: {chat_error}" if error == "" else f"{error} | Chatbot KO: {chat_error}"
    else:
        chat_ok, chat_time, chat_preview, chat_error = None, None, "", ""

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "url": url,
        "final_url": final_url,
        "up": int(ok),
        "status_code": status,
        "response_time_s": elapsed,
        "size_bytes": size,
        "keyword_ok": int(keyword_ok),
        "error": error,
        "ssl_expires": ssl_exp or "",
        "ssl_days_left": ssl_days if ssl_days is not None else -1,
        "ssl_issuer": ssl_issuer or "",
        "sec_score": f"{len(present)}/{len(SEC_HEADERS)}",
        "sec_missing": ";".join(missing),
        "hsts": headers.get("Strict-Transport-Security", ""),
        "server": headers.get("Server", ""),
        "chat_ok": "" if chat_ok is None else int(chat_ok),
        "chat_time_s": "" if chat_time is None else chat_time,
        "chat_preview": chat_preview,
        "chat_error": chat_error,
    }


def main():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = [check_one(t) for t in CFG["targets"]]

    # Migration douce : ancien history.csv sans colonnes chat_* -> on ajoute les colonnes
    fieldnames = list(results[0].keys())
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            old_rows = list(csv.DictReader(f))
        if old_rows and any(c not in old_rows[0] for c in fieldnames):
            for row in old_rows:
                for c in fieldnames:
                    row.setdefault(c, "")
            with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(old_rows)

    new_file = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if new_file:
            w.writeheader()
        w.writerows(results)

    JSON_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    for r in results:
        state = "[UP]" if r["up"] else "[DOWN]"
        chat_info = ""
        if str(r.get("chat_ok", "")) != "":
            chat_info = f" | chat={'OK' if r['chat_ok'] == 1 else 'KO'} {r['chat_time_s']}s"
        print(f"{state} | {r['name']} | {r['url']} | HTTP {r['status_code']} | "
              f"{r['response_time_s']}s | SSL {r['ssl_days_left']}j | sec {r['sec_score']}{chat_info} | {r['error']}".encode('ascii', 'replace').decode())

    # Code retour != 0 si un site DOWN -> utile pour GitHub Actions / Task Scheduler
    if any(not r["up"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
