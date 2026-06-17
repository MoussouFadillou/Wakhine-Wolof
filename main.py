from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="Wakhin Wolof API",
    description="Backend Python pour l'application d'apprentissage du Wolof",
    version="1.0.0"
)

# =================================================================
# 1. CONFIGURATION DES CORS (Accepte tout le monde sans crash)
# =================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Autorise ton frontend Vercel et ton PC local
    allow_credentials=False, # Obligatoire à False lorsque la ligne du dessus utilise "*"
    allow_methods=["*"],     # Autorise toutes les requêtes (GET, POST, OPTIONS...)
    allow_headers=["*"],     # Autorise tous les en-têtes de requêtes
)

# =================================================================
# 2. MODÈLES DE DONNÉES (Schemas Pydantic)
# =================================================================
class MotForm(BaseModel):
    wolof: str
    francais: str
    audioUrl: Optional[str] = ""  # Reçoit le lien envoyé depuis React

class MotResponse(BaseModel):
    id: int
    wolof: str
    francais: str
    audioUrl: str

# =================================================================
# 3. BASE DE DONNÉES TEMPORAIRE (Mots de test corrigés)
# =================================================================
base_de_donnees_mots = [
    {
        "id": 1, 
        "wolof": "Naam", 
        "francais": "Oui / J'écoute", 
        "audioUrl": "https://docs.google.com/uc?export=download&id=1i4Nmu25ja6TQpW0usdxdFXep2bP-NCcJ"
    },
    {
        "id": 2, 
        "wolof": "Déedéet", 
        "francais": "Non", 
        "audioUrl": ""
    },
    {
        "id": 3, 
        "wolof": "Jërëjëf", 
        "francais": "Merci", 
        "audioUrl": ""
    }
]
compteur_id = 3

# =================================================================
# 4. LES POINTS D'ACCÈS (Routes de l'API)
# =================================================================

# Route pour récupérer la liste des mots (Appelée au chargement de ton site React)
@app.get("/api/mots", response_model=List[MotResponse])
def obtenir_tous_les_mots():
    return base_de_donnees_mots


# Route pour ajouter et sauvegarder un nouveau mot (Appelée par ton formulaire)
@app.post("/api/mots", response_model=MotResponse, status_code=201)
def ajouter_un_mot(mot: MotForm):
    global compteur_id
    
    lien_audio = mot.audioUrl.strip() if mot.audioUrl else ""
    
    # Sécurité : On nettoie et transforme automatiquement le lien Google Drive si nécessaire
    try:
        if "drive.google.com" in lien_audio and "/view" in lien_audio:
            if "/file/d/" in lien_audio:
                # Extraction de l'identifiant unique situé entre /file/d/ et /view
                id_drive = lien_audio.split("/file/d/")[1].split("/view")[0]
                # Reconstruction du lien pour forcer le téléchargement/flux direct de l'audio
                lien_audio = f"https://docs.google.com/uc?export=download&id={id_drive}"
    except Exception as e:
        # Si le découpage plante à cause d'un format bizarre, on ne bloque pas le serveur
        print(f"Erreur lors de la conversion automatique du lien Drive : {e}")

    compteur_id += 1
    nouveau_mot = {
        "id": compteur_id,
        "wolof": mot.wolof.strip(),
        "francais": mot.francais.strip(),
        "audioUrl": lien_audio
    }
    
    base_de_donnees_mots.append(nouveau_mot)
    return nouveau_mot


# Route de vérification (Pour tester si le serveur répond depuis ton navigateur)
@app.get("/")
def verifier_serveur():
    return {"message": "Le serveur de Wakhin Wolof tourne à merveille !"}
