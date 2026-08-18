# EpicQuiz — App Écran TV plateau

Application d'affichage pur, sans aucune interaction utilisateur. Une instance par écran physique (2 à 3 selon le plateau), chacune peut afficher une vue différente si la régie le souhaite (ex. un écran sur la grille, un autre sur la question active).

## 1. Connexion

Même principe que les autres apps de plateau : saisie du `username` (distribué par le Manager, tag `screen:<n>` associé pour distinguer les écrans entre eux) et d'un nom identifiant l'appareil (ex. "Écran plateau 1"). Envoi `POST /api/auth/join/ {username, name}`, obtention du token, ouverture de la connexion WebSocket en écoute seule sur les deux canaux (Jeu et Broadcast, cf. §3). Dans la pratique, cette saisie est généralement faite une fois par la régie technique au moment de l'installation du poste, pas à chaque émission.

## 2. Vues disponibles

| Vue | Contenu |
| --- | --- |
| `grid` | Grille complète, cases jouées avec leur résultat, cases non jouées en couleur neutre (ou avec attributs visibles pendant la phase de révélation) |
| `active_question` | Question + propositions de la case en cours, avec chronomètre visuel synchronisé serveur |
| `scores` | Scores des deux participants, grand format, pour plan large caméra |
| `cell_replay` | Rappel de la dernière case résolue (résultat, points, lot éventuel) |
| `idle` | Écran neutre avant le début de l'émission ou entre deux segments |

## 3. Mécanisme de bascule

Chaque écran TV se connecte au canal Broadcast (`03-protocole-websocket.md` §1) et reste **en écoute uniquement** : quand l'Opérateur appelle `POST /episodes/<eid>/change-tv-view/`, le serveur diffuse l'événement correspondant sur le canal Broadcast et l'écran change d'affichage en conséquence. L'écran TV n'émet jamais rien lui-même, ni commande ni requête HTTP applicative.

Pour le contenu de chaque vue (données de grille, question, scores), l'écran TV s'abonne également en lecture aux diffusions du canal Jeu — techniquement via le même relais serveur que celui utilisé par le Manager en supervision, mais sans jamais pouvoir y écrire. Cette distinction "canal Jeu en lecture seule" doit être appliquée strictement au niveau du Consumer, pas seulement côté app (un écran TV compromis ne doit pas pouvoir envoyer une requête HTTP applicative même en modifiant l'app — vérification de rôle/permissions systématique côté serveur, cf. `03-protocole-websocket.md` §2).

## 4. Comportement pendant la révélation de grille

Pendant les 30 secondes de révélation (initiale ou au retour de pause pub), la vue `grid` doit afficher les couleurs des cases à attribut spécial. Passé ce délai, le passage en mode "jeu" (cases non jouées neutres) doit être strictement synchronisé avec ce que voient les tablettes joueurs au même instant — piloté par le même événement serveur (`grid_reveal_ended`), jamais par un minuteur local indépendant sur l'écran TV.

## 5. Contraintes d'affichage plateau

- Résolution et proportions à adapter selon le matériel réel du plateau (à définir avec l'Opérateur/régie technique) — l'app doit supporter au minimum les formats 16:9 standards de diffusion TV.
- Pas de bordures, boutons ou éléments d'interface visibles à l'écran — c'est un habillage broadcast, pas une application interactive.
- Dégradation propre en cas de coupure réseau : conserver le dernier affichage connu plutôt que d'afficher une erreur technique visible à l'antenne, avec reconnexion silencieuse en arrière-plan.

## 6. Reconnexion

Identique au principe de l'app Joueur (`04-app-joueur.md` §4) : à la reconnexion, resynchronisation intégrale sur `full_state` avant tout réaffichage, sans transition brutale visible si possible (fondu plutôt que flash). Distinction coupure réseau vs token invalidé : voir `11-frontend-svelte.md` §3 — un token invalidé sur un écran TV (cas rare, ex. reprovisioning accidentel) doit ramener à l'écran de Connexion plutôt que boucler indéfiniment.
