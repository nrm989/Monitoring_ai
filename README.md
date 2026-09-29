# Monitoring MMSP / Idarati

## Explication du projet

Ce projet surveille chaque jour si les 5 solutions sont en ligne :

- https://ai.mmsp.gov.ma/ (AI Marketplace)
- https://chatbot.idarati.ma/ (Assistant Citoyen)
- https://meeting.ai.mmsp.gov.ma/ (Assistant de Réunion)
- https://pdf.ai.mmsp.gov.ma/ (Assistant PDF)
- https://bo.ai.mmsp.gov.ma/ (Back-office Recherche)

Pour chaque site il vérifie : HTTP en ligne / hors ligne, temps de réponse, certificat SSL, headers de sécurité, et pour le chatbot un vrai test fonctionnel `POST /api/agent/chat` avec le message `Bonjour`.

Les résultats sont visibles dans Grafana et envoyés par mail à snajnihal2002@gmail.com. Le contrôle tourne en continu via Prometheus + Grafana (toutes les 30s).

## Le faire fonctionner (ponctuel)

Prérequis : Python 3.10+ installé.

```powershell
cd "E:\MTNRA IA\monitoring_ai"
pip install -r requirements.txt
```

1. Lancer un check :

```powershell
python monitor.py
```

2. Envoyer le rapport par mail (configuré dans `.env`, voir `.env.example`) :

```powershell
python report.py
```

Pour un test sans envoi : `python report.py --dry-run` puis ouvrir `data/preview.html`.

Pour l'automatique quotidien : double-cliquez `run_daily.bat` ou planifiez-le à 08h00 dans le Planificateur de tâches Windows.

## Le faire fonctionner (continu Prometheus + Grafana)

Prérequis : Docker Desktop lancé.

```powershell
docker compose up -d --build
```

- Métriques : http://localhost:8000/metrics
- Prometheus : http://localhost:9090
- Grafana : http://localhost:3000 (admin / admin, dashboard « Websites MMSP » déjà provisionné)

Arrêter : `docker compose down`.

## Les 2 mails et l'uptime 30j

**Uptime 30j (%)** = `avg_over_time(website_up[30d]) × 100`. `website_up` vaut 1 (en ligne) ou 0 (down) toutes les 30s ; la moyenne sur 30 jours donne le % de temps en ligne. Avec peu d'historique, le % se calcule sur les données disponibles.

**Mail 1 — alerte temps réel (Grafana)** : 5 règles dans `grafana/provisioning/alerting/websites.yml` envoient un mail à `MAIL_TO` (depuis `.env`, via Gmail) dès qu'un problème dure 1-5 min : site DOWN, chatbot KO sur « Bonjour », contenu inattendu, SSL < 30 jours, site lent > 30s. L'objet précise le problème, ex. `[FIRING] Monitoring MMSP : Site DOWN`. Rappel toutes les 4h tant que ça dure, + mail de résolution.

**Mail 2 — rapport quotidien (`report.py`)** : résumé des 5 sites, à planifier à 08h00 (voir ci-dessus).
