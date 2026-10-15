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


load_dotenv()
engine_test = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
SessionTest = sessionmaker(bind=engine_test, autoflush=False, autocommit=False)

# Va créer une session temporaire
@pytest.fixture()
def db_session():
    connexion = engine_test.connect()
    transaction = connexion.begin()
    session = SessionTest(bind=connexion, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connexion.close()

# fournit une session SQLAlchemy qui sera rollback à la fin
@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()