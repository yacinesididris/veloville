"""Client HTTP centralisé vers l'API VéloVille."""

import os
from datetime import date
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDES = float(os.getenv("API_TIMEOUT_SECONDES", "5"))


class ErreurApi(Exception):
    """Erreur levée lorsque l'API est injoignable ou répond en erreur."""


def _requete(
    methode: str,
    chemin: str,
    token: str | None = None,
    params: dict[str, Any] | None = None,
    donnees: dict[str, Any] | None = None,
) -> Any:
    entetes = {}
    if token is not None:
        entetes["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            methode,
            f"{API_URL}{chemin}",
            params=params,
            json=donnees,
            headers=entetes,
            timeout=API_TIMEOUT_SECONDES,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        response = exc.response
        detail = None
        if response is not None:
            try:
                detail = response.json().get("detail")
            except (ValueError, AttributeError):
                detail = None

        if isinstance(detail, str):
            message = detail
        elif response is not None:
            message = f"Erreur HTTP {response.status_code} lors de l'appel à l'API."
        else:
            message = "L'API a refusé la requête."
        raise ErreurApi(message) from exc
    except requests.Timeout as exc:
        raise ErreurApi("L'API n'a pas répondu dans le délai prévu.") from exc
    except requests.ConnectionError as exc:
        raise ErreurApi("Impossible de joindre l'API.") from exc
    except requests.RequestException as exc:
        raise ErreurApi("Une erreur est survenue lors de l'appel à l'API.") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise ErreurApi("La réponse de l'API n'est pas au format JSON attendu.") from exc


def post_login(username: str, password: str) -> dict[str, Any]:
    return _requete(
        "POST",
        "/auth/login",
        donnees={"username": username, "password": password},
    )


def get_stations(
    token: str,
    commune: str | None = None,
    page: int = 1,
    taille_page: int = 20,
) -> dict[str, Any]:
    params = {"page": page, "taille_page": taille_page}
    if commune:
        params["commune"] = commune
    return _requete("GET", "/stations", token=token, params=params)


def get_station(token: str, station_id: str) -> dict[str, Any]:
    return _requete("GET", f"/stations/{station_id}", token=token)


def get_trajets(
    token: str,
    date_debut: date | None = None,
    date_fin: date | None = None,
    station: str | None = None,
    page: int = 1,
    taille_page: int = 20,
) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "taille_page": taille_page}
    if date_debut is not None:
        params["date_debut"] = date_debut
    if date_fin is not None:
        params["date_fin"] = date_fin
    if station:
        params["station"] = station
    return _requete("GET", "/trajets", token=token, params=params)


def get_incidents(
    token: str,
    statut: str | None = None,
    page: int = 1,
    taille_page: int = 20,
) -> dict[str, Any]:
    params = {"page": page, "taille_page": taille_page}
    if statut:
        params["statut"] = statut
    return _requete("GET", "/incidents", token=token, params=params)


def put_incident_statut(
    token: str,
    incident_id: str,
    statut: str,
) -> dict[str, Any]:
    return _requete(
        "PUT",
        f"/incidents/{incident_id}/statut",
        token=token,
        donnees={"statut": statut},
    )


def get_activite_par_jour(
    token: str,
    date_debut: date | None = None,
    date_fin: date | None = None,
) -> dict[str, Any]:
    params = {}
    if date_debut is not None:
        params["date_debut"] = date_debut
    if date_fin is not None:
        params["date_fin"] = date_fin
    return _requete(
        "GET",
        "/indicateurs/activite-par-jour",
        token=token,
        params=params,
    )


def get_stations_actives(token: str, limite: int = 10) -> dict[str, Any]:
    return _requete(
        "GET",
        "/indicateurs/stations-actives",
        token=token,
        params={"limite": limite},
    )


def get_incidents_par_statut(token: str) -> dict[str, Any]:
    return _requete(
        "GET",
        "/indicateurs/incidents-par-statut",
        token=token,
    )
