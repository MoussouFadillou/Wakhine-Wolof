```python
import csv
import io
import os

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from database import create_contribution, list_all_contributions
from storage import upload_audio


# ============================================================
# CONFIGURATION
# ============================================================

app = FastAPI(
    title="Wakhin Wolof API",
    version="6.0.0"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://wakhine-wolof-frontend-qfq4.vercel.app"
)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PAGE D'ACCUEIL
# ============================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Wakhin Wolof API",
        "version": "6.0.0",
        "storage": "Supabase Storage",
        "database": "Supabase"
    }


# ============================================================
# TEST DU SERVEUR
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "wakhin-wolof-api",
        "database": "Supabase",
        "storage": "Supabase Storage"
    }


# ============================================================
# ENREGISTRER UNE CONTRIBUTION
# ============================================================

@app.post("/api/contribuer")
async def contribuer(
    age: int = Form(...),
    sexe: str = Form(...),
    region: str = Form(...),
    departement: str = Form(...),
    accent: str = Form(...),
    alphabetisation: str = Form(...),
    type_parole: str = Form(...),
    transcription: str = Form(""),
    audioFile: UploadFile = File(...)
):

    # --------------------------------------------------------
    # Vérification de l'âge
    # --------------------------------------------------------

    if age < 1 or age > 120:
        raise HTTPException(
            status_code=400,
            detail="L'âge doit être compris entre 1 et 120."
        )

    # --------------------------------------------------------
    # Vérification des champs
    # --------------------------------------------------------

    fields = {
        "sexe": sexe,
        "region": region,
        "departement": departement,
        "accent": accent,
        "alphabetisation": alphabetisation,
        "type_parole": type_parole
    }

    for field, value in fields.items():
        if not value or not value.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Le champ {field} est obligatoire."
            )

    # --------------------------------------------------------
    # Vérification du fichier audio
    # --------------------------------------------------------

    if not audioFile:
        raise HTTPException(
            status_code=400,
            detail="Aucun fichier audio reçu."
        )

    content = await audioFile.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est vide."
        )

    filename = audioFile.filename or "audio.wav"
    content_type = audioFile.content_type or "audio/wav"

    # --------------------------------------------------------
    # Upload audio vers Supabase Storage
    # --------------------------------------------------------

    try:
        audio_path = upload_audio(
            content=content,
            original_name=filename,
            content_type=content_type
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'enregistrement audio : {exc}"
        )

    # --------------------------------------------------------
    # Enregistrement des métadonnées dans Supabase
    # --------------------------------------------------------

    try:
        row = create_contribution(
            age=age,
            sexe=sexe,
            region=region,
            departement=departement,
            accent=accent,
            alphabetisation=alphabetisation,
            type_parole=type_parole,
            transcription=transcription,
            audio_path=audio_path,
            audio_filename=filename,
            audio_content_type=content_type
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'enregistrement des données : {exc}"
        )

    # --------------------------------------------------------
    # Réponse
    # --------------------------------------------------------

    return {
        "success": True,
        "message": "Contribution enregistrée avec succès.",
        "contribution": row,
        "audio_path": audio_path
    }


# ============================================================
# EXPORT CSV — ADMIN UNIQUEMENT
# ============================================================

@app.get("/api/contributions/csv")
def contributions_csv(
    x_admin_token: str | None = Header(default=None)
):

    # --------------------------------------------------------
    # Vérification du ADMIN_TOKEN
    # --------------------------------------------------------

    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_TOKEN n'est pas configuré sur Render."
        )

    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Code administrateur incorrect."
        )

    # --------------------------------------------------------
    # Récupération des contributions
    # --------------------------------------------------------

    try:
        rows = list_all_contributions()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des contributions : {exc}"
        )

    # --------------------------------------------------------
    # Création du CSV
    # --------------------------------------------------------

    output = io.StringIO()

    fields = [
        "id",
        "age",
        "sexe",
        "region",
        "departement",
        "accent",
        "alphabetisation",
        "type_parole",
        "transcription",
        "audio_path",
        "audio_filename",
        "audio_content_type",
        "created_at"
    ]

    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        delimiter=";"
    )

    writer.writeheader()

    for row in rows:
        writer.writerow({
            field: row.get(field, "")
            for field in fields
        })

    # --------------------------------------------------------
    # Téléchargement du fichier
    # --------------------------------------------------------

    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
            'attachment; filename="corpus_wakhin_wolof.csv"'
        }
    )
```

### Après avoir remplacé `main.py`

Fais seulement ces 4 étapes :

1. **Enregistre `main.py`.**
2. Envoie la modification sur GitHub.
3. Dans Render, fais **Manual Deploy → Deploy latest commit**.
4. Attends que le statut soit **Deployed**.

Puis ouvre :

```text
https://TON-URL-RENDER/health
```

Le résultat doit maintenant être :

```json
{
  "status": "healthy",
  "service": "wakhin-wolof-api",
  "database": "Supabase",
  "storage": "Supabase Storage"
}
```

### ⚠️ Important

Pour que ce `main.py` fonctionne, ton dossier `backend` doit aussi contenir :

```text
backend/
├── main.py
├── database.py
├── storage.py
├── supabase_client.py
├── requirements.txt
└── .python-version
```

Et `requirements.txt` :

```text
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.20
supabase==2.15.0
```

**Ne modifie rien d'autre maintenant.** Une fois le nouveau déploiement terminé, teste `/health`.
