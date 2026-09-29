# Monitoring MMSP / Idarati

## Explication du projet

Ce projet surveille chaque jour si les 2 solutions sont en ligne :

- https://ai.mmsp.gov.ma/ (AI Marketplace)
- https://chatbot.idarati.ma/ (Assistant Citoyen)

Pour chaque site il vérifie : HTTP en ligne / hors ligne, temps de réponse, certificat SSL, headers de sécurité, et pour le chatbot un vrai test fonctionnel `POST /api/agent/chat` avec le message `Bonjour`.

Les résultats sont visibles dans un dashboard Streamlit et envoyés par mail à snajnihal2002@gmail.com.

## Le faire fonctionner

Prérequis : Python 3.10+ installé.

```powershell
cd "E:\MTNRA IA\monitoring_ai"
pip install -r requirements.txt
```

1. Lancer un check :

```powershell
python monitor.py
```

2. Voir le dashboard :

```powershell
streamlit run app.py
```

3. Envoyer le rapport par mail :

```powershell
$env:SMTP_USER="votre.gmail@gmail.com"
$env:SMTP_PASS="xxxx xxxx xxxx xxxx"
python report.py --to snajnihal2002@gmail.com
```

Pour un test sans envoi : `python report.py --dry-run` puis ouvrir `data/preview.html`.

Pour l'automatique quotidien : double-cliquez `run_daily.bat` ou planifiez-le à 08h00 dans le Planificateur de tâches Windows.
