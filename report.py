"""Rapport email quotidien (HTML) + alerte si DOWN.
Usage:
  # test sans envoi : python report.py --to example_mail@gmail.com --dry-run

Pourquoi pas de screenshot ? Fragile (fenêtre, résolution, login), lourd, non cliquable.
Le HTML ci-dessous contient déjà tout. Option screenshot Playwright en bas si vraiment exigé.
"""
import argparse
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).parent
LATEST = BASE / "data" / "latest.json"

load_dotenv(BASE / ".env")


def build_html(results: list) -> str:
    rows = ""
    for r in results:
        badge = "🟢 EN LIGNE" if r["up"] else "🔴 HORS LIGNE"
        color = "#137333" if r["up"] else "#a50e0e"
        chat = "—"
        if str(r.get("chat_ok", "")) != "":
            if r["chat_ok"] == 1:
                chat = f"💬 OK {r['chat_time_s']}s<br><small>{r.get('chat_preview','')[:120]}</small>"
            else:
                chat = f"💬 KO<br><small>{r.get('chat_error','')}</small>"
        rows += f"""
        <tr>
          <td><b>{r['name']}</b><br><a href="{r['url']}">{r['url']}</a></td>
          <td style="color:{color};font-weight:bold">{badge}</td>
          <td>{r['status_code']}</td>
          <td>{r['response_time_s']}s</td>
          <td>{r['ssl_days_left']} j<br><small>{r['ssl_issuer']}</small></td>
          <td>{r['sec_score']}<br><small>{r['sec_missing'] or 'OK'}</small></td>
          <td>{chat}</td>
          <td><small>{r['error'] or '—'}</small></td>
        </tr>"""
    all_up = all(r["up"] for r in results)
    title = "✅ Tout est en ligne" if all_up else "🚨 Incident détecté"
    return f"""<html><body style="font-family:Arial,sans-serif">
    <h2>{title} — Monitoring MMSP (5 sites)</h2>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse">
      <tr style="background:#f0f0f0"><th>Service</th><th>État</th><th>HTTP</th>
      <th>Réponse</th><th>SSL</th><th>Sécurité</th><th>Chatbot</th><th>Détail</th></tr>
      {rows}
    </table>
    <p>Dashboard Grafana : http://localhost:3000 (dashboard « Websites MMSP »)<br>
    Historique complet : <code>data/history.csv</code></p>
    <p><small>Envoyé automatiquement par monitor.py + report.py</small></p>
    </body></html>"""


def send(to: str, subject: str, html: str):
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    if not user or not pwd:
        raise SystemExit("SMTP_USER / SMTP_PASS manquants dans .env. Voir .env.example.")
    msg = MIMEMultipart("alternative")
    msg["From"], msg["To"], msg["Subject"] = user, to, subject
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL(host, port) as s:
        s.login(user, pwd)
        s.sendmail(user, [to], msg.as_string())
    print(f"Email envoye a {to}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", default=os.getenv("MAIL_TO", "snajnihal2002@gmail.com"))
    ap.add_argument("--dry-run", action="store_true", help="affiche le HTML sans envoyer")
    args = ap.parse_args()

    results = json.loads(LATEST.read_text(encoding="utf-8"))
    html = build_html(results)
    subject = ("[OK] Monitoring MMSP en ligne" if all(r["up"] for r in results)
               else "[DOWN] Monitoring MMSP incident")

    if args.dry_run:
        out = BASE / "data" / "preview.html"
        out.write_text(html, encoding="utf-8")
        print(f"Preview ecrit : {out}")
        return
    send(args.to, subject, html)


if __name__ == "__main__":
    main()

# --- Option screenshot (déconseillée, sur demande) ---
# pip install playwright && playwright install chromium
# from playwright.sync_api import sync_playwright
# with sync_playwright() as p:
#     b = p.chromium.launch(); pg = b.new_page(); pg.goto("http://localhost:8501")
#     pg.wait_for_timeout(4000); pg.screenshot(path="dashboard.png", full_page=True); b.close()
# Puis joindre dashboard.png au mail via MIMEImage.
