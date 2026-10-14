# Schéma de données

À compléter : MLD textuel ou image, description des tables, clés et contraintes,
règles de gestion portées par le schéma.


## trajets.csv

| défauts identifiés | nombre de lignes concernées | traitement retenu |
|:-------- |:--------:| --------:|
| lignes en doublons     | 12   | suppression des lignes en doublons    |
| Durée de trajet invalide (null ou <0)     | 9   | suppression des trajets invalides    |

Nombre de ligne initial : 2030  
Nombre de ligne final : 2009  
  
  
## incidents.csv

| défauts identifiés | nombre de lignes concernées | traitement retenu |
|:-------- |:--------:| --------:|
| `status` a des lignes qui ne repectent pas la casse     | 125   | modification des lignes concernées   |
| `date_resolution` invalide (< date_signalement)    | 3   | suppression des lignes concernées   |

Nombre de ligne initial : 180  
Nombre de ligne final : 177  
  

## stations.csv  
  
Pas d'erreurs identifiées