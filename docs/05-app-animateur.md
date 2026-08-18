# EpicQuiz — App tablette Animateur (présentateur)

Outil de conduite du jeu. L'animateur fait avancer le direct, mais n'a aucun pouvoir de contournement des règles — ça reste le rôle du Manager.

## 1. Écrans / zones fonctionnelles

1. **Connexion** — identique au principe de l'app Joueur (`username` + nom → token → WebSocket en écoute seule, cf. `04-app-joueur.md` §1).
2. **Tableau de bord de partie** — vue permanente pendant le direct :
   - Grille complète en mode "vue animateur" : contrairement aux joueurs, l'animateur voit la nature de chaque case (normale/vide/spéciale) même non jouée — nécessaire pour l'annoncer ou gérer l'antenne, mais **jamais diffusé** vers les TV ou tablettes joueurs.
   - Scores des deux participants en temps réel.
   - Statut de phase courant (`reveal`, `in_progress`, `ad_break`, `finished`).
   - Bouton **Démarrer la partie** (actif uniquement en phase `ready`) → `POST /episodes/<eid>/start-game/`.
3. **Validation de sélection** — quand un joueur annonce sa case à l'oral plutôt que sur tablette (cf. règles v1.3 §5.2 "à l'oral ou via sa tablette"), l'animateur peut effectuer lui-même `POST /episodes/<eid>/select-cell/` en son nom. Le serveur applique la même validation de tour que si le joueur l'avait fait lui-même.
4. **Lancement de question** — après sélection de case, bouton **Révéler la question** → `POST /episodes/<eid>/launch-question/`. Déclenche l'affichage synchronisé sur TV et tablette du joueur actif via l'événement `question_revealed`.
5. **Suivi de résolution** — affichage en direct de la réponse du joueur dès soumission, avant même l'expiration du temps, pour que l'animateur puisse commenter à l'antenne sans attendre.
6. **Verrouillage joueur** — boutons **Verrouiller** / **Déverrouiller**, par joueur individuel ou globalement, → `POST /episodes/<eid>/lock-players/` / `unlock-players/ {target: "all" | "participant", participant_id?}` (cf. `03-protocole-websocket.md` §6). Utile pour geler l'interaction le temps de régler un aléa plateau sans passer par le Manager.
7. **Pause publicitaire** — boutons **Lancer la pause** / **Reprendre** → `POST /episodes/<eid>/start-ad-break/` / `resume-game/`, actifs selon compteur `cells_played` (indicatif à ~20, décision humaine).
8. **Fin de partie** — bouton **Terminer la partie** → `POST /episodes/<eid>/end-game/`, actif seulement quand les 48 cases sont jouées ; affiche un récapitulatif immédiat du vainqueur.

## 2. Ce qui n'est PAS dans cette app

- Aucune fonction de correction ou d'override — si une case a été mal résolue techniquement, c'est une intervention du Manager (`07-app-manager.md`), pas de l'animateur, pour garder un canal d'exception unique et traçable.
- Aucun contrôle direct sur les écrans TV (bascule de vue) ni sur le son — c'est le rôle de l'Opérateur.

## 3. Permissions

L'animateur a accès à tous les endpoints du canal Jeu sauf `manager-intervention` (cf. `03-protocole-websocket.md` §5). Le serveur refuse (403) côté API toute tentative hors de ce périmètre — utile en cas de bug côté app plutôt que de mauvaise volonté.

`lock-players`/`unlock-players` (§1.6) sont à l'inverse **exclusifs à l'Animateur** — ni le Joueur ni le Manager ne peuvent les appeler (le Manager passe par `manager-intervention` s'il a besoin d'un effet équivalent en dernier recours).

## 4. Reconnexion et redondance

Vu le rôle critique de cette app en plein direct, prévoir :
- Reconnexion automatique du WebSocket en arrière-plan dès perte détectée (sans intervention de l'animateur) — cette connexion n'est utilisée qu'en écoute, donc une coupure de quelques secondes n'empêche pas d'agir (les actions passent par HTTP indépendamment du WebSocket). Distinction coupure réseau vs token invalidé : voir `11-frontend-svelte.md` §3.
- Un indicateur visuel discret mais clair de l'état de connexion WebSocket (connecté / reconnexion en cours) — l'animateur doit savoir si l'affichage qu'il voit est à jour avant d'agir à l'antenne.
