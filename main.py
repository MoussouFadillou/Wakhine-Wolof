@app.post("/api/contribuer")
async def ajouter_contribution(
    age: int = Form(...),
    sexe: str = Form(...),
    region: str = Form(...),
    departement: str = Form(...),
    accent: str = Form(...),
    alphabetisation: str = Form(...),
    type_parole: str = Form(...),
    transcription: str = Form(""), # 🌟 ICI : Si rien n'est écrit, il mettra du vide sans bloquer
    audioFile: UploadFile = File(...)
):
    chemin_temporaire = f"temp_{audioFile.filename}"
    try:
        service = obtenir_service_drive()
        
        contenu_audio = await audioFile.read()
        with open(chemin_temporaire, "wb") as f_temp:
            f_temp.write(contenu_audio)
            
        type_propre = type_parole.split('(')[0].strip().replace(' ', '_')
        nom_fichier_drive = f"{region}_{departement}_{type_propre}_{audioFile.filename}"
        
        file_metadata = {
            'name': nom_fichier_drive,
            'parents': [ID_DOSSIER_DRIVE]
        }
        
        media = MediaFileUpload(chemin_temporaire, mimetype=audioFile.content_type, resumable=True)
        fichier_drive = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        id_fichier = fichier_drive.get('id')
        
        service.permissions().create(fileId=id_fichier, body={'type': 'anyone', 'role': 'reader'}).execute()
        lien_audio_direct = f"https://docs.google.com/uc?export=download&id={id_fichier}"

        liste_contributions = charger_donnees()
        nouvelle_entree = {
            "id": len(liste_contributions) + 1,
            "age": age,
            "sexe": sexe,
            "region": region,
            "departement": departement,
            "accent": accent,
            "alphabetisation": alphabetisation,
            "type_parole": type_parole,
            "transcription": transcription, # Sera enregistré vide ou rempli
            "audioUrl": lien_audio_direct
        }
        
        liste_contributions.append(nouvelle_entree)
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
            json.dump(liste_contributions, f, ensure_ascii=False, indent=4)
        
        return nouvelle_entree

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur critique du serveur : {str(e)}")
        
    finally:
        if os.path.exists(chemin_temporaire):
            os.remove(chemin_temporaire)
