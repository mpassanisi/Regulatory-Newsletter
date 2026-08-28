"""Point d'entrée du job planifié : collecte → dédup → classification → stockage.

Usage :
    python pipeline.py            # run complet (écrit dans la base)
    python pipeline.py --dry-run  # collecte + dédup seulement, sans appel LLM

La page web (app.py) lit ensuite la même base pour afficher les résultats.
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import config
import storage
from collectors import collect_all
from dedup import deduplicate
from models import Deal


def _too_old(item) -> bool:
    if item.published is None:
        return False
    published = item.published
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - published > timedelta(days=config.MAX_AGE_DAYS)


def run(dry_run: bool = False) -> None:
    sources = config.load_sources()

    items = collect_all(sources)
    print(f"\n{len(items)} items collectés au total.")

    items = deduplicate(items)
    items = [i for i in items if not _too_old(i)]
    print(f"{len(items)} items après déduplication et filtre d'âge.")

    engine = storage.connect()
    items = [i for i in items if not storage.already_known(engine, i.url)]
    print(f"{len(items)} items nouveaux à analyser.")

    if dry_run:
        for i in items[:20]:
            print(f"  · [{i.source_id}] {i.title}")
        print("\n(dry-run : pas d'appel LLM, pas d'écriture)")
        return

    from classify import classify, keep  # import tardif : besoin de la clé API

    kept = 0
    for item in items:
        analysis = classify(item)
        if analysis and keep(analysis):
            storage.save_deal(engine, Deal.from_classification(item, analysis))
            kept += 1
            print(f"  ✓ {analysis.get('societe')} — {analysis.get('montant')}")
    print(f"\n{kept} levée(s) de fonds retenue(s).")

    # Rendu local + envoi email optionnel (la page web lit directement la base)
    from render import render_html, render_linkedin

    deals = storage.unsent_deals(engine)
    out = Path(config.ROOT / "out")
    out.mkdir(exist_ok=True)
    stamp = date.today().isoformat()
    (out / f"newsletter-{stamp}.html").write_text(render_html(deals), encoding="utf-8")
    (out / f"linkedin-{stamp}.txt").write_text(render_linkedin(deals), encoding="utf-8")
    print(f"Livrables écrits dans {out}/ ({len(deals)} deal(s)).")

    if os.environ.get("BREVO_API_KEY") and deals:
        send_email(render_html(deals))

    storage.mark_sent(engine, [d.url for d in deals])


def send_email(html: str) -> None:
    """Envoi via l'API Brevo (ex-Sendinblue). À adapter à ta liste de contacts."""
    import httpx

    resp = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": os.environ["BREVO_API_KEY"],
                 "content-type": "application/json"},
        json={
            "sender": {"name": "Veille Biotech",
                       "email": os.environ.get("SENDER_EMAIL", "veille@example.com")},
            "to": [{"email": os.environ.get("TEST_RECIPIENT", "toi@example.com")}],
            "subject": f"Levées de fonds biotech & pharma — {date.today():%d/%m/%Y}",
            "htmlContent": html,
        },
        timeout=30,
    )
    print(f"Email Brevo : HTTP {resp.status_code}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
