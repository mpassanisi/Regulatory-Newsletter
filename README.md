# Veille — levées de fonds biotech &amp; pharma (Wallonie / Belgique)

Application déployable **clé sur porte** : tu pousses le repo sur GitHub, tu le
connectes à Render, et tout tourne seul. Un job planifié collecte l'actualité,
ne retient que les **vraies levées de fonds d'acteurs wallons/belges** (filtrage
LLM), les stocke, et une **page web** affiche les résultats en direct.

## Ce que ça fait

```
Cron (Render)  →  collecte + tri LLM  →  Postgres  →  Page web (Render)
   chaque lundi                          (partagé)      /  /newsletter  /linkedin
```

- `/` — tableau de bord des levées détectées
- `/newsletter` — la newsletter HTML de l'édition en cours (à envoyer par email)
- `/linkedin` — le texte prêt à coller dans LinkedIn

## Déploiement sur Render (clé sur porte)

1. Pousse ce dossier sur un repo GitHub.
2. Sur Render : **New > Blueprint**, sélectionne ton repo. Render lit `render.yaml`
   et crée automatiquement les 3 ressources : base Postgres, service web, cron job.
3. Renseigne les secrets dans le dashboard (marqués `sync: false` dans le blueprint) :
   - `ANTHROPIC_API_KEY` (obligatoire)
   - `BREVO_API_KEY`, `SENDER_EMAIL` (optionnels, pour l'envoi email)
4. C'est en ligne. Tu peux lancer le cron une première fois à la main
   (bouton **Run** sur le service cron) pour peupler la base sans attendre lundi.

### Coûts (vérifie toujours la page Render, ça évolue)

| Ressource | Plan | Coût |
|---|---|---|
| Service web | free | 0 € (se met en veille après inactivité → léger délai au réveil) |
| Cron job | starter | ~1 $/mois (les cron ne sont pas gratuits chez Render) |
| Postgres | free | 0 € — **mais le Postgres gratuit Render expire.** Voir ci-dessous. |
| API Claude | — | quelques € de tokens/mois à ce volume |

> **Base pérenne :** le Postgres gratuit de Render est temporaire. Pour une base
> gratuite qui dure, crée une base sur **Neon** (neon.tech, tier gratuit durable),
> supprime le bloc `databases:` de `render.yaml`, et colle l'URL Neon dans la
> variable `DATABASE_URL` des deux services. Rien d'autre à changer : le code
> détecte Postgres via `DATABASE_URL`.

### Alternative 100 % gratuite

Tu peux garder le **cron sur GitHub Actions** (gratuit, fichier
`.github/workflows/veille.yml` fourni) et ne mettre sur Render que la page web.
Les deux pointent alors sur la même base Neon via `DATABASE_URL`.

## Développement local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."

python pipeline.py --dry-run   # collecte + dédup, sans appel LLM ni écriture
python pipeline.py             # run complet (base SQLite locale : deals.db)
python app.py                  # page web sur http://localhost:5000
```

En local, sans `DATABASE_URL`, le code utilise automatiquement SQLite (`deals.db`).

## Configurer les sources

Tout est dans `sources.yaml`. Pour ajouter une source : teste d'abord
`<url>/feed/` (si XML → `type: rss`, fiable et sans entretien) ; sinon `type: scrape`
avec les sélecteurs CSS à ajuster en inspectant la page. Puis vérifie avec
`python pipeline.py --dry-run`.

## Réglages (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Clé API Claude (obligatoire) |
| `DATABASE_URL` | SQLite local | Postgres en ligne (fourni par Render/Neon) |
| `CLASSIFY_MODEL` | `claude-haiku-4-5-...` | Modèle de classification |
| `MIN_CONFIANCE` | `0.6` | Seuil de confiance minimal |
| `MAX_AGE_DAYS` | `14` | Ancienneté max des articles classés |
| `BREVO_API_KEY` | — | Active l'envoi email (optionnel) |

## Sur LinkedIn

L'API de LinkedIn ne permet pas de publier une newsletter native par programme.
L'app produit le **texte** (`/linkedin`) ; le dernier clic (coller + publier) reste
manuel — ce qui te laisse la main sur l'édito.

## Structure

```
biotech-veille/
├── render.yaml          # Blueprint Render (web + cron + base)
├── app.py               # page web Flask (lecture de la base)
├── pipeline.py          # job planifié (collecte → tri → stockage)
├── sources.yaml         # sources déclaratives (à personnaliser)
├── config.py            # paramètres & seuils
├── models.py            # RawItem, Deal
├── collectors.py        # RSS + scraping → RawItem
├── dedup.py             # déduplication
├── classify.py          # classification LLM (tool use → JSON)
├── storage.py           # SQLAlchemy : SQLite (local) / Postgres (en ligne)
├── render.py            # rendu HTML (email) + texte (LinkedIn)
├── templates/
│   ├── dashboard.html.j2    # page web
│   └── newsletter.html.j2   # email
└── .github/workflows/veille.yml   # cron gratuit alternatif (GitHub Actions)
```
