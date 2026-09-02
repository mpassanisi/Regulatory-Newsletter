"""Application web : affiche les résultats en direct depuis la base partagée.

Routes :
  /            -> tableau de bord HTML des levées détectées
  /newsletter  -> la newsletter HTML de l'édition en cours (deals non diffusés)
  /linkedin    -> le texte prêt à coller dans LinkedIn (text/plain)
  /health      -> sonde de disponibilité (pour Render)

Le job planifié (pipeline.py) écrit dans la même base ; ici on ne fait que lire.
Démarrage en production : gunicorn app:app
"""
from datetime import date

from flask import Flask, Response, render_template, request

import pressreview
import storage
from render import render_html, render_linkedin

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 Mo max par upload
engine = storage.connect()


@app.route("/")
def dashboard():
    deals = storage.all_deals(engine, limit=200)
    return render_template(
        "dashboard.html.j2",
        deals=deals,
        total=len(deals),
        today=date.today().strftime("%d/%m/%Y"),
    )


@app.route("/newsletter")
def newsletter():
    deals = storage.recent_deals(engine, days=7)
    return render_html(deals)


@app.route("/linkedin")
def linkedin():
    deals = storage.recent_deals(engine, days=7)
    return Response(render_linkedin(deals), mimetype="text/plain; charset=utf-8")


@app.route("/health")
def health():
    return {"status": "ok"}

UPLOAD_PAGE = """<!DOCTYPE html><html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<body style="font-family:Arial;max-width:640px;margin:40px auto;padding:0 20px;color:#1a1a1a;">
<h1 style="font-size:20px;">Déposer une ou plusieurs revues de presse (PDF)</h1>
<p style="color:#6b6b6b;font-size:14px;">Le système en extrait les levées biotech/pharma belges et les ajoute à la veille. Optionnel : le reste tourne sans ça.</p>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" accept="application/pdf" multiple required>
  <button type="submit" style="margin-left:8px;">Analyser</button>
</form>
<p style="font-size:12px;color:#9b9b9b;margin-top:16px;">Le traitement peut prendre 10 à 30 secondes.</p>
</body></html>"""


def _upload_result(error, found, saved):
    if error:
        msg = f'<p style="color:#b00">{error}</p>'
    else:
        msg = (f'<p><strong>{found}</strong> levée(s) biotech belge(s) détectée(s), '
               f'<strong>{saved}</strong> nouvelle(s) ajoutée(s).</p>')
    return f"""<!DOCTYPE html><html lang="fr"><meta charset="utf-8">
<body style="font-family:Arial;max-width:640px;margin:40px auto;padding:0 20px;">
<h1 style="font-size:20px;">Revue de presse</h1>{msg}
<p><a href="/upload">← Déposer un autre PDF</a> · <a href="/">Tableau de bord</a></p>
</body></html>"""


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return UPLOAD_PAGE
    files = [f for f in request.files.getlist("file")
             if f and f.filename.lower().endswith(".pdf")]
    if not files:
        return _upload_result("Merci de déposer au moins un fichier PDF.", 0, 0)
    total_found, total_saved = 0, 0
    for file in files:
        try:
            deals = pressreview.deals_from_pdf(file.read())
        except Exception as exc:
            print(f"  [!] {file.filename} : {exc}")
            continue
        total_found += len(deals)
        for d in deals:
            if not storage.already_known(engine, d.url):
                storage.save_deal(engine, d)
                total_saved += 1
    return _upload_result(None, total_found, total_saved)

if __name__ == "__main__":
    # Développement local uniquement. En prod, Render lance gunicorn.
    app.run(host="0.0.0.0", port=5000, debug=True)
