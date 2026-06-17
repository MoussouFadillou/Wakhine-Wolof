from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Wakhin Wolof API")

# Configuration CORS sécurisée (Option 2 : accepte tout sans crash)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Indispensable à False avec ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèle de données simplifié en chaînes de caractères (str) pour éviter les bugs de validation
class MotForm(BaseModel):
    wolof: str
    francais: str
    audioUrl: Optional[str] = ""

class MotResponse(BaseModel):
    id: int
    wolof: str
    francais: str
    audioUrl: str

# Base de données temporaire
base_de_donnees_mots = [
    {"id": 1, "wolof": "Naam", "francais": "Oui / J'écoute", "audioUrl": ""},
    {"id": 2, "wolof": "Déedéet", "francais": "Non", "audioUrl": ""},
    {"id": 3, "wolof": "Jërëjëf", "francais": "Merci", "audioUrl": ""}
]
compteur_id = 3

@app.get("/api/mots", response_model=List[MotResponse])
def obtenir_tous_les_mots():
    return base_de_donnees_mots

# ✅ CORRIGÉ : Le status_code est bien 201 maintenant
@app.post("/api/mots", response_model=MotResponse, status_code=201)
def ajouter_un_mot(mot: MotForm):
    global compteur_id
    
    lien_audio = mot.audioUrl.strip() if mot.audioUrl else ""
    
    # 🛡️ FILET DE SÉCURITÉ : On entoure le traitement de l'URL pour éviter tout plantage du serveur
    try:
        if "drive.google.com" in lien_audio and "/view" in lien_audio:
            if "/file/d/" in lien_audio:
                id_drive = lien_audio.split("/file/d/")[1].split("/view")[0]
                lien_audio = f"https://docs.google.com/uc?export=download&id={1i4Nmu25ja6TQpW0usdxdFXep2bP-NCcJ}"
    except Exception as e:
        # Si le découpage du lien Drive échoue, on ne plante pas ! 
        # On garde juste le lien brut envoyé par l'utilisateur
        print(f"Attention, échec de la conversion du lien Drive : {e}")

    compteur_id += 1
    nouveau_mot = {
        "id": compteur_id,
        "wolof": mot.wolof.strip(),
        "francais": mot.francais.strip(),
        "audioUrl": lien_audio
    }
    
    base_de_donnees_mots.append(nouveau_mot)
    return nouveau_mot

@app.get("/")
def racine():
    return {"message": "Le serveur est en ligne !"}
