from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="Wakhin Wolof API - Régions du Sénégal")

# Configuration des CORS pour autoriser ton Frontend Vercel sans blocage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RegionForm(BaseModel):
    wolof: str
    audioUrl: Optional[str] = ""

FICHIER_SAUVEGARDE = "regions_wolof.json"

# Base de données de départ avec l'orthographe officielle en Wolof
def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [
        {"id": 1, "wolof": "Ndakaaru", "audioUrl": ""},
        {"id": 2, "wolof": "Cees", "audioUrl": ""},
        {"id": 3, "wolof": "Ndar", "audioUrl": ""},
        {"id": 4, "wolof": "Ndoxum Ngéej", "audioUrl": ""},
        {"id": 5, "wolof": "Géejawaay", "audioUrl": ""}
    ]

def sauvegarder_donnees(donnees):
    with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4)

@app.get("/api/mots")
def obtenir_toutes_les_regions():
    return charger_donnees()

@app.post("/api/mots", status_code=201)
def ajouter_une_region(region: RegionForm):
    try:
        liste_actuelle = charger_donnees()
        lien_audio = region.audioUrl.strip() if region.audioUrl else ""
        
        # Transformation magique du lien Google Drive pour la lecture directe
        if "drive.google.com" in lien_audio and "/view" in lien_audio:
            if "/file/d/" in lien_audio:
                id_drive = lien_audio.split("/file/d/")[1].split("/view")[0]
                lien_audio = f"https://docs.google.com/uc?export=download&id={id_drive}"

        prochain_id = max([r["id"] for r in liste_actuelle], default=0) + 1

        nouvelle_region = {
            "id": prochain_id,
            "wolof": region.wolof.strip(),
            "audioUrl": lien_audio
        }

        liste_actuelle.append(nouvelle_region)
        sauvegarder_donnees(liste_actuelle)
        return nouvelle_region

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")

@app.get("/")
def racine():
    return {"statut": "Serveur Wolof opérationnel sur Render"}
