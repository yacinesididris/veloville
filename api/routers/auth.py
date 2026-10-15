"""Route d'authentification."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Utilisateur
from api.schemas import ConnexionReponse, ConnexionRequete
from api.securite import creer_jeton, verifier_mot_de_passe

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=ConnexionReponse)
def login(
    requete: ConnexionRequete,
    db: Session = Depends(get_db),
) -> ConnexionReponse:
    utilisateur = db.scalar(
        select(Utilisateur).where(Utilisateur.username == requete.username)
    )
    if utilisateur is None or not verifier_mot_de_passe(
        requete.password, utilisateur.mot_de_passe_hash
    ):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    return ConnexionReponse(
        access_token=creer_jeton(utilisateur),
        token_type="bearer",
        role=utilisateur.role,
    )
