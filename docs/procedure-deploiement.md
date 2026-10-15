# Procédure de déploiement

## Prérequis 

 - VSCode (ou similaire) avec Python 3.13 minimum
 - PGadmin (ou similaire) avec PostgreSQL 18 avec accès SUPERUSER
 - Git et compte GitHub pour clonage du dépôt

## Installation

### Création de la base de donnée

Lancer PGAdmin avec vos identifiants administrateurs de la base et lancer la ligne suivante :

```sql
CREATE ROLE veloville LOGIN PASSWORD 'veloville';
```

C'est l'identifiant et le mot de passe qui seront utilisés par la solution pour se connecter au serveur

Ensuite, depuis PGAdmin4, créer la database `veloville` avec comme owner le compte créé précedemment

Enfin, se connecter sur la database et lancer les deux scripts dans le dossier `SQL` **dans l'ordre suivant** :
 - ``schema.sql``
 - ``comptes.sql``


### Importation du dépôt

Depuis VSCode, le terminal pointant sur le dossier dans lequel vous souhaitez installer la solution :

1. Cloner le dépôt :
   ```python
   git clone https://github.com/yacinesididris/veloville.git
   cd veloville
   ```

2. Créer l'environnement virtuel
    ```python
    python -m venv venv
    ```
    puis 
    ```python
    .venv\Scripts\activate
    ```

3. Installer les dépendances :
    ```python
    pip install -r requirements.txt
    ```

4. Créer le fichier .env
     - A la racine du dossier se trouve le ficiher ``.env.example``. Le renommer en ``.env`` et le completer
        
     - Pour générer une clé secrète JWT, lancer sur le terminal la ligne de code suivante :
    ```python
    python -m api.securite
    ```

     - Sur la ligne ``DATABASE_URL``, remplacez le nom d'utilisateur par ``veloville`` et le mot de passe pr celui choisi précédemment
     - Idem pour la ligne ``TEST_DATABASE_URL``

  
  
### Importation des données

Il y'a actuellement 3 fichiers dans le dossier :
``incidents.csv``, ``stations.csv``, ``trajets.csv``

On va utiliser le script d'importation des csv pour peupler les tables créées précédemment.
Un rapport de nettoyage des données et d'importation dans la base de donnée apparaitra dans docs/rapports.

***Le script n'insere pas de lignes déjà présentes dans la base de donnée et si l'un des fichiers n'est pas présent,
 un message d'erreur apparait dans le rapport. Le script d'importation se terminera sans erreur dans les deux cas.***
  


Depuis le terminal, lancer la commande suivante pour lancer le script :

```python
python scripts/importer.py
```


### Création d'un base de donnée test

Pour les test qui se feront sur base de donnée, afin d'éviter tout problème à la Base Production on va créer une Base Test.

Pour ce faire : 
   1. Sur PGAdmin, donner (temporairement) des droits ``SUPERUSER`` à l'utilisateur ``veloville``
   (clic-droit sur l'utilisateur > ``Properties...`` > onglet ``Privilèges`` > activer ``Superuser?`` )

   2. Lancer le script creer_bdd_test.py depuis le terminal
   ```python
   python -m scripts.creer_bdd_test
   ```
   3. Retirer les droits ``SUPERUSER`` à l'utilisateur ``veloville``


## Lancement des tests

Pour lancer les tests, toujours depuis le terminal : 

```python
pytest --cov=api/services --cov-report=term-missing
```
La couverture et le pourcentage de réussite s'afficheront dans le terminal 

## Lancement du programme

Dans le terminal, lancer l'API :


```python
uvicorn api.main:app --reload
```

Puis dans un autre terminal, toujours à la racine, lancer le front

```python
streamlit run front/app.py
```
