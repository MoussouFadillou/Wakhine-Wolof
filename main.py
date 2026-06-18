from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="Wakhin Wolof API Sécurisée")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Le modèle attend maintenant le code de sécurité du frontend
class RegionForm(BaseModel):
    wolof: str
    audioUrl: Optional[str] = ""
    codeSecurite: str  # 👈 Ajout du champ pour la sécurité

FICHIER_SAUVEGARDE = "regions_wolof.json"
CODE_SECRET_ATTENDU = "SENEGAL2026"  # 👈 C'est le code magique pour pouvoir enregistrer !

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [
        {"id": 1, "wolof": "Ndakaaru", "audioUrl": ""},
        {"id": 2, "wolof": "Cees", "audioUrl": ""}
    ]

def sauvegarder_donnees(donnees):
    with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4)

@app.get("/api/mots")
def obtenir_toutes_les_regions():
    return charger_donnees()

@app.post("/api/mots", status_code=201)
def ajouter_une_region(region: RegionForm):
    # 🔐 VERIFICATION DU CODE DE SÉCURITÉ
    if region.codeSecurite != CODE_SECRET_ATTENDU:
        raise HTTPException(
            status_code=403, 
            detail="Code de sécurité incorrect. Vous n'avez pas les droits d'enregistrement."
        )

    try:
        liste_actuelle = charger_donnees()
        lien_audio = region.audioUrl.strip() if region.audioUrl else ""
        
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
    return {"statut": "Serveur sécurisé opérationnel"}
