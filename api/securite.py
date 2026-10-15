"""Fonctions de sécurité : bcrypt et JWT."""

from datetime import datetime, timedelta, timezone
from typing import Callable

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from api.database import get_db
from api.models import Utilisateur

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain_password: str) -> str:
    """Transforme un mot de passe en hash bcrypt avant stockage en base."""

    # gensalt() génère un sel aléatoire intégré directement dans le hash bcrypt.
    salt = bcrypt.gensalt()

    # hashpw() produit le hash à partir du mot de passe + du sel.
    hashed = bcrypt.hashpw(
        plain_password.encode("utf-8"),
        salt,
    )

    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie si le mot de passe saisi correspond au hash stocké."""

    # checkpw() refait le calcul bcrypt avec les informations contenues dans le hash.
    # On ne déchiffre donc jamais le mot de passe enregistré.
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(utilisateur: Utilisateur) -> str:
    """Crée un JWT signé pour l'utilisateur authentifié."""

    now = datetime.now(timezone.utc)
    expiration = now + timedelta(minutes=JWT_EXPIRE_MINUTES)

    payload = {
        # sub ("subject") identifie l'utilisateur auquel appartient le token.
        "sub": str(utilisateur.id_utilisateur),

        # sub ("subject") : le role
        "role": utilisateur.role,

        # iat indique quand le token a été créé.
        "iat": now,

        # exp fixe la date après laquelle le token n'est plus accepté.
        "exp": expiration,

    }

    # encode() signe le contenu avec JWT_SECRET.
    # Le token peut être lu, mais une modification casserait sa signature.
    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Vérifie la signature et l'expiration puis retourne le payload."""

    # decode() refuse un token modifié, mal signé ou expiré.
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    """Retourne l'utilisateur associé au JWT fourni dans l'en-tête."""

    authentication_error = HTTPException(
        status_code=401,
        detail="Authentification requise",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise authentication_error

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise authentication_error from exc

    utilisateur = db.get(Utilisateur, user_id)
    if utilisateur is None:
        raise authentication_error
    return utilisateur


def require_role(role: str) -> Callable:
    """Construit une dépendance qui limite l'accès à un rôle."""

    def check_role(
        utilisateur: Utilisateur = Depends(get_current_user),
    ) -> Utilisateur:
        if utilisateur.role != role:
            raise HTTPException(
                status_code=403,
                detail="Acces reserve au role exploitant",
            )
        return utilisateur

    return check_role
