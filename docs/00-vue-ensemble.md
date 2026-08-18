# EpicQuiz — Vue d'ensemble du système

Version : 1.0
Contexte : plateforme de production pour l'émission télévisée EpicQuiz (grille 48 cases, cf. Règles v1.3), déployée **dans un réseau fermé de studio, sans accès internet**.

## 1. Objectif du document

Ce dossier définit les spécifications techniques du **cœur système** (backend Django 6.x + WebSocket) et des **5 applications front-end** utilisées en studio. Chaque fichier de ce dossier couvre une brique :

| Fichier | Contenu |
| --- | --- |
| `01-architecture-backend.md` | Stack technique, composants serveur, contraintes réseau fermé |
| `02-modele-donnees.md` | Modèles Django (persistant + event log) |
| `03-protocole-websocket.md` | Protocole de messages temps réel, permissions par rôle |
| `04-app-joueur.md` | App tablette joueur (×2) |
| `05-app-animateur.md` | App tablette présentateur |
| `06-app-ecran-tv.md` | App écran TV plateau (×2-3) |
| `07-app-manager.md` | App manager (config amont + supervision live) |
| `08-app-operateur.md` | App opérateur régie technique |
| `09-deploiement-reseau-ferme.md` | Contraintes et procédure de déploiement offline |
| `10-rapport-audit.md` | Génération du rapport d'audit de fin de partie (algorithme, formats de sortie) |
| `11-frontend-svelte.md` | Structure du monorepo frontend, composants et stores partagés entre les 5 apps |

## 2. Les acteurs et leurs rôles

| Rôle | Appareil | Intervient | Peut modifier les règles du jeu ? |
| --- | --- | --- | --- |
| **Joueur** (×2) | Tablette | Pendant le direct | Non — agit dans les règles (sélection case, réponse) |
| **Animateur** | Tablette | Pendant le direct | Fait avancer le jeu (révélation, validation), pas de contournement des règles |
| **Écran TV** (×2-3) | Affichage plateau | Pendant le direct | Non — lecture seule |
| **Manager** | Tablette/PC | Avant (config) + pendant (supervision) | **Oui** — peut forcer une correction, override un état, en dernier recours |
| **Opérateur** | Poste régie | Pendant le direct | Non — agit uniquement sur la couche présentation (bascule d'écran, son, effets), jamais sur l'état du jeu |

Cette distinction est structurante pour tout le reste des specs : le **Manager** a un canal de commandes privilégié qui touche le moteur de jeu (avec traçabilité renforcée dans l'event log), l'**Opérateur** n'a accès qu'à une couche de présentation strictement séparée de la logique de jeu.

## 3. Principes directeurs

1. **Le serveur est seul autoritaire.** Aucun client n'envoie un état, il envoie une *intention*. Le serveur valide, calcule, persiste, diffuse.
2. **Tout événement de jeu est journalisé** (event sourcing) avant d'être diffusé. L'état affiché à tout instant est une projection du journal, jamais l'inverse.
3. **Séparation stricte présentation / logique de jeu.** L'Opérateur ne peut agir que sur ce qui s'affiche, jamais sur ce qui se joue.
4. **Toute intervention manuelle du Manager pendant le direct est un événement de type spécial**, horodaté et attribué, jamais une simple correction silencieuse en base.
5. **Fonctionnement 100% hors-ligne.** Aucune dépendance à un service externe (pas de CDN, pas d'API tierce, pas de licence en ligne) — voir `09-deploiement-reseau-ferme.md`.
6. **Résilience au direct.** Une tablette qui perd la liaison WiFi 3 secondes doit pouvoir se reconnecter et retrouver l'état exact sans intervention humaine.
