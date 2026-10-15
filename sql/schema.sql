-- Schéma de la base veloville (PostgreSQL 14+).
-- À compléter en respectant le contrat du sujet (types, clés, contraintes).
-- Le script doit être rejouable : prévoir les DROP ... IF EXISTS ou
-- CREATE TABLE IF NOT EXISTS.

-- ---------------------------------------------------------------
-- 1. Table station
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS station (
    station_id VARCHAR(10) PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    commune VARCHAR(100) NOT NULL,
    capacite INTEGER NOT NULL CHECK (capacite > 0),
    latitude NUMERIC(8,5) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude NUMERIC(8,5) NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    date_mise_en_service DATE NOT NULL
);

-- ---------------------------------------------------------------
-- 2. Table trajet
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trajet (
    trajet_id VARCHAR(12) PRIMARY KEY,
    velo_id VARCHAR(8) NOT NULL,
    depart_horodatage TIMESTAMP NOT NULL,
    station_depart VARCHAR(10) NOT NULL REFERENCES station(station_id),
    station_arrivee VARCHAR(10) REFERENCES station(station_id),
    duree_secondes INT NOT NULL CHECK (duree_secondes > 0),
    type_usager VARCHAR(50) NOT NULL CHECK (type_usager IN ('abonne', 'occasionnel')),
    usager_ref VARCHAR(9),
    CONSTRAINT chk_usager_ref CHECK (
        (type_usager = 'occasionnel' AND usager_ref IS NULL) 
        OR 
        (type_usager = 'abonne' AND usager_ref IS NOT NULL))
);


-- ---------------------------------------------------------------
-- 3. Table incident
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incident (
    incident_id VARCHAR(12) PRIMARY KEY,
    date_signalement TIMESTAMP NOT NULL,
    cible VARCHAR(50) NOT NULL 
        CHECK (cible IN ('velo', 'station')),
    velo_id VARCHAR(8),
    station_id VARCHAR(10) REFERENCES station(station_id),
    type_incident VARCHAR (30) NOT NULL
		CHECK (type_incident IN ('vandalisme', 
								'selle abimee', 
								'eclairage HS', 
								'chaine deraillee', 
								'ecran borne illisible', 
								'pneu creve', 
								'frein defectueux', 
								'borne hors service')),
	statut VARCHAR(10) NOT NULL 
        CHECK (statut IN ('ouvert', 'en_cours', 'resolu')),
    date_resolution TIMESTAMP,
    technicien VARCHAR(100),

    CONSTRAINT chk_velo_id CHECK (
        (cible = 'velo' AND velo_id IS NOT NULL) 
        OR 
        (cible = 'station' AND velo_id IS NULL)),
    CONSTRAINT chk_station_id CHECK (
        (cible = 'station' AND station_id IS NOT NULL) 
        OR 
        (cible = 'velo' AND station_id IS NULL)),
    CONSTRAINT chk_date_resolution CHECK (
        (statut = 'resolu' 
            AND date_resolution >= date_signalement 
            AND date_resolution IS NOT NULL  ) 
        OR 
        (statut IN ('ouvert', 'en_cours') AND date_resolution IS NULL)) 
);


-- ---------------------------------------------------------------
-- 4. Table utilisateur
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS utilisateur (
    id_utilisateur SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    mot_de_passe_hash VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('exploitant', 'direction'))
);


-- ---------------------------------------------------------------
-- 5. Index utiles aux filtres et aux indicateurs
-- ---------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_nom ON station(nom);
CREATE INDEX IF NOT EXISTS idx_station_depart on trajet(station_depart);
CREATE INDEX IF NOT EXISTS idx_station_arrivee on trajet(station_arrivee);
CREATE INDEX IF NOT EXISTS idx_date_signalement on incident(date_signalement);
CREATE INDEX IF NOT EXISTS idx_resolution on incident(date_resolution);
CREATE INDEX IF NOT EXISTS idx_username on utilisateur(username);






