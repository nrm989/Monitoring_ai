# Monitoring MMSP — Prometheus + Grafana

Surveillance en continu (toutes les 30 secondes) des 5 solutions :

- https://ai.mmsp.gov.ma/ (AI Marketplace)
- https://chatbot.idarati.ma/ (Assistant Citoyen)
- https://meeting.ai.mmsp.gov.ma/ (Assistant de Réunion)
- https://pdf.ai.mmsp.gov.ma/ (Assistant PDF)
- https://bo.ai.mmsp.gov.ma/ (Back-office Recherche)

Pour chaque site : état en ligne / hors ligne, code HTTP, temps de réponse, mot-clé anti-page-blanche, certificat SSL, headers de sécurité — et pour le chatbot un vrai test fonctionnel `POST /api/agent/chat` avec le message `Bonjour`.

## Architecture

`exporter.py` (checks toutes les 30s) → Prometheus (stocke l'historique + règles) → Grafana (dashboard + alertes mail via Gmail).

## Démarrage

Prérequis : Docker Desktop lancé + fichier `.env` renseigné (voir `.env.example` : `SMTP_USER`, `SMTP_PASS` = mot de passe d'application Gmail, `MAIL_TO`).

```powershell
cd "E:\MTNRA IA\monitoring_ai"
docker compose up -d --build
```

- Grafana : http://localhost:3000 (admin / admin, dashboard « Websites MMSP »)
- Prometheus : http://localhost:9090
- Métriques brutes : http://localhost:8000/metrics

Arrêter : `docker compose down`.

## Dashboard Grafana

État actuel (1 = UP / 0 = DOWN) • Temps de réponse HTTP • Chatbot Idarati (test Bonjour + temps + texte de la réponse) • Jours restants SSL • Code HTTP (200 vert, 4xx orange, autre rouge) • Uptime 30j (%).

**Uptime 30j (%)** = `avg_over_time(website_up[30d]) × 100`. `website_up` vaut 1 ou 0 à chaque scrape ; la moyenne sur 30 jours glissants donne le % de temps en ligne. Avec peu d'historique, le % se calcule sur les données disponibles.

## Alertes mail

5 règles (`grafana/provisioning/alerting/websites.yml`) envoient un mail à `MAIL_TO` dès qu'un problème persiste : site DOWN (1 min), chatbot KO sur « Bonjour » (2 min), contenu inattendu (2 min), SSL < 30 jours (5 min), site lent > 30s (5 min). Objet explicite, ex. `[FIRING] Monitoring MMSP : Site DOWN` avec le nom du site et l'URL dans le corps. Rappel toutes les 4h + mail de résolution.

## Ajouter / modifier un site

1. Éditer `config.yaml` (`targets` : `name`, `url`, `keyword` attendu dans le HTML).
2. Reconstruire l'exporter : `docker compose up -d --build exporter`.

## Commandes utiles

```powershell
docker compose ps
docker compose logs -f exporter
docker compose restart grafana   # après modif du dashboard ou des alertes
```

## Fichiers

```
config.yaml                  sites surveillés
monitor.py                   logique des checks (utilisée par l'exporter)
exporter.py                  expose les métriques Prometheus (:8000)
Dockerfile.exporter          image de l'exporter
docker-compose.yml           exporter + prometheus + grafana
prometheus/                  scrape 30s + règles d'alerte
grafana/                     datasource, dashboard, alertes mail
.env                         secrets Gmail (jamais commité)
```
