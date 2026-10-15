from sqlalchemy import create_engine, text
from api.config import DATABASE_URL


def cloner_base_de_donnees(base_a_copier: str, nom_base_test: str):
    """  Créer une BDD test à partir de la vraie. """

    engine = create_engine(
        DATABASE_URL,

        # isolation_level="AUTOCOMMIT" : permet ne pas faire de transaction (postgresql refuse les CREATE DATABASE dans une transaction)
        isolation_level="AUTOCOMMIT" 
    )

    acces_restreint = False

    try:

        with engine.connect() as connexion:

            # Empêche les nouvelles connexions sur la base source
            connexion.execute(
                text(
                    f'REVOKE CONNECT ON DATABASE "{base_a_copier}" FROM PUBLIC'
                )
            )

            acces_restreint = True

            # Ferme toutes les connexions actuellement ouvertes
            connexion.execute(
                text(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = :nom_base
                    AND pid <> pg_backend_pid()
                    """
                ),
                {"nom_base": base_a_copier}
            )

            # Création de la base test en copiant la bdd
            connexion.execute(
                text(
                    f'CREATE DATABASE "{nom_base_test}" '
                    f'WITH TEMPLATE "{base_a_copier}"'
                )
            )

            print(
                f"Base '{nom_base_test}' créée à partir de "
                f"'{base_a_copier}'."
            )

    finally:

        # Rétablit les droits même si une erreur survient
        if acces_restreint:

            with engine.connect() as connexion:

                connexion.execute(
                    text(
                        f'GRANT CONNECT ON DATABASE "{base_a_copier}" TO PUBLIC'
                    )
                )

                print(
                    f"Accès rétabli sur la base "
                    f"'{base_a_copier}'."
                )
        # ferme toutes les connexions
        engine.dispose()


if __name__ == "__main__":
    cloner_base_de_donnees("veloville", "veloville_bdd_test")
