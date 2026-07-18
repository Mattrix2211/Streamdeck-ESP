# Appli compagnon PC

Deux pages, comme gerer les pages d'applications sur un telephone :

- **Accueil** : un ou plusieurs **profils** (onglets), chacun avec sa
  propre grille de 16 emplacements ET ses 3 encodeurs - chaque
  emplacement/encodeur se configure via sa propre popup (glisser-deposer
  pour reordonner les emplacements). L'ecran **bascule automatiquement**
  sur le bon profil selon l'application au premier plan sur le PC (ex : la
  grille change toute seule en passant sur OBS, Discord, un jeu...) - voir
  "Profils par application" plus bas. C'est la seule page dont vous avez
  besoin au quotidien.
- **Reglages** (icone &#9881;) : connexion a l'ecran, cle API, Home
  Assistant, forme des boutons - demandee automatiquement au tout premier
  lancement, puis on n'y revient quasiment plus.

Tourne en icone dans la barre des taches (pas de fenetre de terminal), se
connecte directement au Stream Deck (pas besoin de Home Assistant pour que
ca fonctionne - meme si HA continue de voir l'appareil nativement en
parallele, et peut en plus alimenter des widgets en temps reel, voir plus
bas).

## Installation

```bash
cd pc-app
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

Pas de fichier a copier a la main : au tout premier lancement, l'appli
cree `dashboard_config.yaml` automatiquement (vide) et vous redirige vers
la page **Reglages** pour renseigner l'IP de l'ecran et la cle API (meme
valeur que `firmware/secrets.yaml` ; l'IP se trouve dans Home Assistant :
l'appareil "Stream Deck" > Adresse IP). Une fois valide, vous arrivez sur
l'accueil et n'avez plus besoin d'y retoucher.

## Lancer au quotidien (recommande)

Icone de barre des taches, pas de terminal a garder ouvert :

```powershell
pythonw -m streamdeck_companion.tray
```

Pour qu'elle demarre automatiquement a l'ouverture de session Windows :

```powershell
powershell -ExecutionPolicy Bypass -File install_startup.ps1
```

Clic sur l'icone (ou "Configurer le Stream Deck" dans son menu) pour
ouvrir la page de configuration - `http://127.0.0.1:8080`.

## Lancer manuellement (sans icone, avec logs dans le terminal)

```bash
python -c "from streamdeck_companion.tray import main; main()"
```

## Les 2 pages

### Accueil (`/`)

Une maquette fidele de l'ecran (memes proportions 1024x600, meme
disposition header/grille/encodeurs/statut, tuiles carrees ou rondes selon
vos reglages) : ce que vous voyez dans le navigateur correspond vraiment a
ce qui s'affichera sur l'ecran physique, avant meme d'envoyer.

- Les emplacements **visibles** apparaissent dans la maquette d'ecran, a la
  meme place qu'ils occuperont reellement.
- Les emplacements **masques** apparaissent a part, sous la maquette, dans
  une section "Emplacements masques" (comme la bibliotheque d'apps d'un
  iPhone) - ils n'apparaissent jamais sur l'ecran reel tant qu'ils restent
  la.
- Cliquez une tuile (dans la maquette ou dans les masques) pour ouvrir sa
  popup de reglages (visibilite, libelle, icone, type, action).
- Glissez-deposez une tuile sur une autre - dans la maquette, dans les
  masques, ou de l'un vers l'autre - pour les echanger (utile pour faire
  passer un emplacement masque a l'ecran, ou reordonner ceux deja
  visibles).

12 emplacements sont visibles par defaut (comme l'ancien systeme a 12
boutons), les 4 derniers sont masques - faites-les glisser sur l'ecran (ou
cochez "Visible sur l'ecran" dans leur popup) des que vous en avez besoin,
sans reflasher. "Enregistrer et envoyer a l'ecran" sauvegarde et pousse
immediatement la grille (emplacements + encodeurs) vers l'ecran.

Les 3 encodeurs de la maquette sont cliquables comme les emplacements :
leur popup regle l'action de chacun des 3 sens (horaire, antihoraire,
appui). Chaque encodeur affiche sur l'ecran une barre 0-100% (type "barre
de son") au lieu d'un simple compteur qui s'incremente sans limite -
pratique pour un encodeur de volume par exemple. La valeur repart de 0
a chaque redemarrage de l'ecran (pas de memorisation du dernier niveau).

## Profils par application

Au-dessus de la maquette, une barre d'onglets liste vos **profils** - chacun
une grille de 16 emplacements + 3 encodeurs independante. Un point vert sur
un onglet indique le profil **reellement affiche sur l'ecran en ce moment**.

- **Creer un profil** : "+ Nouveau profil" - donnez-lui un nom et un
  **declencheur** (le nom du processus, ex `obs64.exe`). Le bouton
  "Detecter l'appli active" remplit le declencheur automatiquement avec
  l'application actuellement au premier plan sur votre PC (lancez-la,
  revenez sur cette page, cliquez) - pas besoin de connaitre le nom exact
  du `.exe`.
- **Bascule automatique** : des que l'application du declencheur passe au
  premier plan, l'ecran change de grille tout seul, sans intervention
  (`streamdeck_companion/profile_watcher.py`, sonde la fenetre active
  toutes les ~1.5s). Le profil sans declencheur (typiquement "Defaut")
  s'affiche quand aucun declencheur ne correspond.
  Le premier profil dont le declencheur correspond gagne, dans l'ordre
  de creation - evitez plusieurs profils avec le meme declencheur.
- **Forcer un profil manuellement** : le bouton "Forcer ce profil" fige
  l'ecran sur l'onglet actuellement affiche (pratique pour previsualiser un
  profil qu'on vient d'editer sans attendre que son application prenne le
  focus) ; "Automatique" a cote reprend la bascule normale.
- **Modifier/supprimer** un profil : cliquez l'icone crayon sur son onglet.
  Le profil sans declencheur ne peut pas etre supprime s'il ne reste que lui.

Chaque onglet garde ses propres modifications en memoire meme en changeant
d'onglet - "Enregistrer et envoyer a l'ecran" sauvegarde **tous les profils
d'un coup**, mais ne pousse vers l'ecran que celui reellement actif (les
autres sont juste enregistres, prets a s'activer a leur tour).

### Reglages (`/reglages`)

Connexion (IP/port/cle API), forme des boutons (carre/rond, s'applique aux
16 emplacements), Home Assistant (URL + jeton). Des reglages qu'on ne
touche presque jamais une fois l'ecran configure - a l'ecart de la page
qu'on utilise au quotidien.

### Type d'emplacement (`bouton` / `barre` / `texte`)

- **bouton** : declenche une action au clic (voir tableau ci-dessous).
- **barre** : jauge 0-100, alimentee par l'etat d'une entite Home
  Assistant numerique (volume, luminosite, batterie...) - reglee via
  "Source Home Assistant (entity_id)" dans la popup.
- **texte** : affiche la valeur brute d'une entite HA + son unite (ex
  "21.5°C") - meme reglage de source.

Les widgets (`barre`/`texte`) sont rafraichis toutes les ~15 secondes par
`streamdeck_companion/ha_poller.py`, qui interroge l'API REST de Home
Assistant en arriere-plan (pas de websocket, suffisant pour quelques
entites).

Dans la maquette de l'accueil, une tuile `barre` affiche une petite jauge
sous le libelle et une tuile `texte` affiche un espace reserve pour la
valeur ("--") - de quoi voir tout de suite quel type est configure sur
chaque emplacement. La jauge/valeur affichee dans le navigateur est un
espace reserve (pas la vraie valeur HA en direct : seul l'ecran physique
la recoit, via `ha_poller.py`).

## Types d'actions (`type` / cible)

| type              | cible                             | effet                                    |
|-------------------|------------------------------------|-------------------------------------------|
| `none`            | -                                  | rien configure                             |
| `keys`            | ex `ctrl+shift+s`                 | envoie une combinaison clavier             |
| `launch`          | chemin ou commande (arguments acceptes) | lance une application/un jeu - voir "Choisir une application" ci-dessous, pas besoin de taper le chemin a la main |
| `url`             | URL ou URI (`steam://...`, `discord://...`) | ouverte via le gestionnaire par defaut du systeme |
| `media`           | `play_pause`/`next`/`previous`/`vol_up`/`vol_down`/`mute` | touche multimedia |
| `home_assistant`  | dans la popup : domaine/service/entite (encodeurs : format compact `domaine.service:entite`, ex `light.toggle:light.bureau`) | appelle un service Home Assistant (bascule une lumiere/prise/scene...) |

## Bibliotheque d'applications (type d'action `launch`)

Pour eviter d'avoir a connaitre/taper un chemin (pas accessible au grand
public), la popup d'un emplacement affiche une vraie bibliotheque
d'applications - grille avec icones et recherche, comme un logiciel de
Stream Deck du commerce - des que le type d'action est `launch` :

- **Applications detectees** : les raccourcis du menu Demarrer (utilisateur
  + tous les utilisateurs), listes automatiquement
  (`streamdeck_companion/app_library.py`).
- **Barre de recherche** : filtre la grille en tapant les premieres lettres
  du nom.
- **Tuile "+ Ajouter..."** : ouvre l'explorateur de fichiers Windows pour
  choisir un `.exe`/`.lnk` non liste (jeu portable, appli sans raccourci
  Demarrer) - l'application choisie **rejoint durablement la bibliotheque**
  (persistee dans `dashboard_config.yaml`, cle `custom_apps`), plus besoin
  de rechercher son chemin une seconde fois. Un lien "Retirer" sur ces
  tuiles personnalisees permet de les enlever de la bibliotheque.

Cliquer une tuile remplit automatiquement le chemin de lancement et le
libelle de l'emplacement. Le champ texte en dessous reste modifiable
directement pour les utilisateurs avances (ex: ajouter des arguments de
ligne de commande apres avoir choisi une application dans la grille).

Windows uniquement pour la detection automatique (necessite
`pywin32`/`winshell`, deja dans `requirements.txt` pour cette plateforme).
Sur les autres systemes, seule la detection automatique est indisponible -
la tuile "+ Ajouter..." (via un selecteur de fichier natif, `tkinter`) et
le champ texte libre restent utilisables partout.

## Icones

Le selecteur d'icone (popup d'un emplacement) propose un catalogue curate
de glyphes Material Icons (`streamdeck_companion/icons.py`) - meme police
chargee dans le navigateur et sur l'ecran (`gfonts://Material Icons` dans
`firmware/package.yaml`), donc l'apercu correspond a ce qui s'affiche
reellement. Pas d'upload d'image personnalisee (voir Limitations).

## Integration Home Assistant

Comme l'ecran expose ses entites nativement (integration ESPHome), Home
Assistant les voit et peut declencher ses propres automatisations en
parallele de cette appli (aucune configuration necessaire cote HA pour ca).

En renseignant l'URL et un jeton d'acces longue duree dans la page de
configuration, vous debloquez en plus :
- les emplacements type **barre**/**texte** (etat en direct d'une entite HA)
- le type d'action **home_assistant** (un bouton qui appelle un service HA)

Independamment, si vous voulez que Home Assistant puisse demander une
action a ce PC (ex: depuis une automation HA sans rapport avec le Stream
Deck), activez `receiver.token` dans `dashboard_config.yaml` et utilisez
`home-assistant/rest_command.yaml.snippet` + les exemples dans
`home-assistant/example_automations.yaml`. Rien de tout ceci n'est
necessaire pour que les emplacements/encodeurs du Stream Deck fonctionnent
- c'est un bonus.

## Limitations connues

- Les combinaisons clavier et touches multimedia passent par le module
  `keyboard`, qui necessite les droits administrateur/root sur certaines
  plateformes (et ne fonctionne pas sous Wayland).
- Sur macOS, `keyboard` n'emule pas les touches multimedia : seul le volume
  systeme est gere nativement (`osascript`). Pour play/pause/next sur macOS,
  il faudra integrer un outil tiers (ex. `nowplaying-cli`) dans
  `streamdeck_companion/actions.py::_media_macos`.
- `tray.py` n'a pu etre teste que hors environnement graphique Windows reel
  (logique de connexion/config verifiee en detail ; le rendu de l'icone
  lui-meme necessite un vrai bureau Windows pour etre confirme).
- Un changement d'IP/port/cle API est repris automatiquement au prochain
  essai de reconnexion (jusqu'a ~10s, `device_client.py::connect()` relit
  la config a chaque tentative) - pas besoin de redemarrer l'icone de la
  barre des taches.
- Le bouton "media" (`play_pause` etc.) envoie une touche multimedia - il
  n'affiche pas l'etat de lecture reel (recuperer l'etat "en cours de
  lecture" de facon fiable et multi-plateforme demanderait une integration
  bien plus lourde). Pour un vrai indicateur en direct, utilisez un
  emplacement type `texte`/`barre` avec une source Home Assistant (ex un
  media_player HA) a la place.
- Le glisser-deposer **echange** deux emplacements (pas d'insertion avec
  decalage des autres) - comportement simple et previsible plutot qu'un
  reordonnancement complet.
- Pas d'upload d'icone personnalisee : le catalogue est un jeu curate de
  glyphes Material Icons (`streamdeck_companion/icons.py`). Pour en
  ajouter, il faut aussi ajouter le point de code correspondant au
  `glyphs:` de `font_icons` dans `firmware/package.yaml`, sinon il
  s'affiche comme une case vide sur l'ecran.
- Les widgets Home Assistant (`barre`/`texte`) sont sondes par polling
  REST toutes les ~15s (`ha_poller.py`), pas en temps reel instantane.
- La detection automatique (`app_library.py`) ne liste que les raccourcis
  du menu Demarrer (utilisateur + tous les utilisateurs) - les applications
  sans raccourci Demarrer (portables, certaines apps du Microsoft Store)
  n'y apparaissent pas ; ajoutez-les via la tuile "+ Ajouter...". Detection
  Windows uniquement (le reste de la bibliotheque - ajout manuel, recherche,
  applications personnalisees - fonctionne partout). Logique testee avec
  des donnees simulees dans le sandbox de developpement (qui n'a pas acces
  a `pywin32`/`winshell`), pas encore confirmee de bout en bout sur une
  vraie machine Windows.
- Les icones de la bibliotheque d'applications sont un glyphe generique
  (pas l'icone reelle extraite du `.exe`) - extraire une vraie miniature
  par application demanderait une integration plus lourde
  (`win32gui.ExtractIconEx`), envisageable dans un futur chantier.
- La page de configuration a ete testee de bout en bout avec un navigateur
  headless (rendu de la maquette d'ecran et des masques, popup emplacement
  et popup encodeur, glisser-deposer dans les deux sens et entre les deux,
  bibliotheque d'applications - recherche, selection, ajout/retrait
  personnalise -, creation/edition/suppression de profils, sauvegarde,
  persistance apres rechargement) mais pas visuellement sur l'ecran
  physique - verifiez apres un push que les icones/couleurs/tailles vous
  conviennent et signalez tout ce qui parait cassé (ex une icone qui
  s'affiche comme une case vide).
- La bascule automatique de profil (`profile_watcher.py`) est Windows
  uniquement (necessite `pywin32`+`psutil` pour identifier la fenetre au
  premier plan) - sur les autres systemes, seule la bascule manuelle
  ("Forcer ce profil"/"Automatique") est disponible. Non verifiee sur une
  vraie machine Windows (logique de correspondance testee unitairement
  dans le sandbox de developpement, qui n'a pas de fenetre/bureau reel).
- La correspondance d'un declencheur se fait par **nom de processus exact**
  (ex `obs64.exe`), pas par titre de fenetre ni par plusieurs criteres -
  simple et previsible, mais deux applications qui partagent le meme nom de
  processus ne peuvent pas avoir de profils distincts.
- Le sondage de la fenetre active a lieu toutes les ~1.5s : la bascule
  automatique n'est donc pas instantanee (delai perceptible mais bref en
  changeant d'application).
