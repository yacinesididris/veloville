"""Fixtures pytest communes.

À compléter : client TestClient de l'API, jetons pour exploitant01 et direction01,
session de base de données de test. Aucun secret en dur : lire .env.
"""

import os
from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.database import get_db
from api.main import app