# EpicQuiz — Déploiement en réseau fermé de studio

Contrainte structurante : **aucun accès internet** sur le réseau du studio, ni pendant le déploiement ni pendant l'exploitation.

## 1. Ce que ça interdit

- Tout appel à un CDN externe dans les apps front-end (fonts, librairies JS, icônes).
- Tout `pip install` / `npm install` en direct sur le réseau du studio.
- Toute vérification de licence en ligne, télémétrie, ou mise à jour automatique de dépendance.
- Toute résolution DNS publique — le réseau doit fonctionner avec des adresses/hostnames internes uniquement.

## 2. Stratégie d'empaquetage

| Composant | Approche |
| --- | --- |
| Dépendances Python | Résolues et téléchargées en environnement connecté, empaquetées en wheel-house locale (dossier de fichiers `.whl`), installées via `pip install --no-index --find-links=./wheelhouse` sur site |
| Dépendances front-end (JS/CSS) | Toutes vendorisées dans le bundle applicatif au build, aucune référence `https://cdn...` dans le code livré |
| Images Docker (si conteneurisation retenue) | Construites et exportées (`docker save`) en environnement connecté, transférées et chargées (`docker load`) sur le réseau studio |
| Base PostgreSQL / Redis | Installées depuis un miroir de paquets local ou binaires embarqués, aucune dépendance à un dépôt en ligne au démarrage |

## 3. Procédure de mise en place avant tournage

1. **Préparation en environnement connecté** (bureau, avant déplacement studio) : build complet de l'application, constitution de la wheel-house, export des images si conteneurs, tests de bout en bout en simulant la coupure réseau.
2. **Transfert physique** vers le réseau studio (clé USB, disque, ou réseau local temporaire isolé — jamais via internet).
3. **Installation sur site** : déploiement des composants (PostgreSQL, Redis, ASGI worker, worker Celery, nginx pour les bundles Svelte statiques — cf. `01-architecture-backend.md` §4) sur le(s) poste(s) serveur du studio.
4. **Test de charge léger avant chaque tournage** : ouverture simultanée des connexions WebSocket des 4-6 appareils attendus (2 joueurs, animateur, 2-3 TV, régie, manager) pour valider la stabilité avant le direct.
5. **Répétition technique** : dérouler un épisode de test complet (grille factice) pour valider la synchronisation TV/tablettes en conditions réelles de plateau (Wi-Fi du lieu, distance, interférences).

## 4. Résilience réseau local (même sans internet, le Wi-Fi studio reste faillible)

- Chaque app front-end doit gérer la reconnexion automatique WebSocket sans intervention utilisateur (cf. chaque spec d'app, section reconnexion).
- Le serveur applicatif tourne sur une machine dédiée au studio, idéalement reliée aux tablettes/écrans par un réseau filaire pour les points fixes (écrans TV, régie) et Wi-Fi dédié uniquement pour les tablettes mobiles (joueurs, animateur), afin d'isoler les sources d'instabilité.
- PostgreSQL doit être sauvegardé (snapshot) après chaque épisode tourné, sur un support local — cette persistance est la seule donnée dont la perte serait irrécupérable (voir aussi la discussion sur le cycle de vie applicatif one-shot vs persistant, tranchée en faveur d'un Postgres permanent + compute applicatif éphémère par session de tournage).

## 5. Ce qui reste hors scope de ce document

- Le choix définitif conteneurs (Docker/Podman) vs installation native sur le(s) poste(s) studio — à trancher selon le matériel serveur réellement disponible en tournage.
- Le plan réseau physique détaillé (adressage, VLAN éventuel) — à établir avec l'équipe technique du lieu de tournage.
