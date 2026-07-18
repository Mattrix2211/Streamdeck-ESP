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
  **declencheur** (le nom du processus, ex `obs64.exe`). Un menu deroulant
  liste directement toutes les applications actuellement ouvertes sur
  votre PC (comme Alt+Tab) - choisissez la vôtre dedans, le declencheur et
  un nom de profil suggere se remplissent tout seuls. Pas besoin de
  connaitre le nom exact du `.exe`, ni de jongler entre cette page et
  l'application a detecter.
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
  Assistant numerique (volume, luminosite, batterie...) - choisie dans une
  liste recherchable (voir "Choisir une entite Home Assistant" ci-dessous),
  pas besoin de connaitre l'entity_id exact.
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
| `home_assistant`  | emplacement : entite + service choisis dans la popup (voir "Choisir une entite Home Assistant" ci-dessous) ; encodeurs : format compact `domaine.service:entite`, ex `light.toggle:light.bureau` | appelle un service Home Assistant (bascule une lumiere/prise/scene...) |
| `audio_output`    | emplacement : peripheriques choisis dans la popup (liste recherchable, `streamdeck_companion/audio_devices.py`) - identifiant opaque, pas destine a etre tape a la main | bascule le peripherique de sortie audio par defaut (casque/enceintes...) - Windows uniquement |

## Bibliotheque d'applications (type d'action `launch`)

Pour eviter d'avoir a connaitre/taper un chemin (pas accessible au grand
public), la popup d'un emplacement affiche une vraie bibliotheque
d'applications - grille avec icones et recherche, comme un logiciel de
Stream Deck du commerce - des que le type d'action est `launch` :

- **Applications ouvertes en ce moment** (point vert) : meme source que le
  declencheur de profil (`profile_watcher.py::list_open_windows()`) - le
  chemin exact de l'executable est resolu automatiquement, pratique quand
  l'appli tourne deja et que vous voulez juste pointer dessus sans chercher
  son raccourci.
- **Applications detectees** : les raccourcis du menu Demarrer (utilisateur
  + tous les utilisateurs), listes automatiquement
  (`streamdeck_companion/app_library.py`).
- **Barre de recherche** : filtre la grille en tapant les premieres lettres
  du nom. Une meme application presente dans plusieurs sources n'apparait
  qu'une fois (priorite a la version "ouverte en ce moment").
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

## Choisir une entite Home Assistant

Comme pour les applications, la popup d'un emplacement propose une
**liste recherchable de vos entites Home Assistant** (`streamdeck_companion/ha_client.py::list_entities()`)
plutot que de taper un entity_id a la main - inspire de
[cgiesche/streamdeck-homeassistant](https://github.com/cgiesche/streamdeck-homeassistant) :

- **Source d'un widget** (type `barre`/`texte`) : tapez quelques lettres
  du nom (ex "temp", "volume", "salon"), cliquez l'entite trouvee - son
  `entity_id` remplit le champ automatiquement.
- **Action `home_assistant`** (type `bouton`) : meme recherche, puis un
  menu deroulant **"Service"** propose les services courants pour le
  domaine de l'entite choisie (ex `light.*` -> toggle/turn_on/turn_off,
  `media_player.*` -> play/pause/volume...) - pas besoin de connaitre le
  nom exact d'un service Home Assistant. Le champ compact
  `domaine.service:entite` en dessous se remplit tout seul, et reste
  modifiable directement pour les cas avances.

Necessite Home Assistant configure dans **Reglages** (URL + jeton d'acces
longue duree). Si la connexion echoue, un message clair s'affiche
(URL injoignable / jeton refuse) au lieu d'une erreur technique brute.

**Limitation actuelle** : ce picker equipe la popup d'un **emplacement**.
Les 3 encodeurs utilisent encore le champ texte compact
`domaine.service:entite` a taper a la main (pas encore de picker dedie -
possible dans un prochain chantier si besoin).

## Couleur d'une ampoule sur le bouton

Pour un emplacement `bouton` dont l'action `home_assistant` cible une
entite du domaine `light`, une case **"Afficher la couleur de l'ampoule
sur le bouton"** apparait sous le choix du service. Une fois cochee :

- `ha_poller.py` lit l'etat de l'ampoule a chaque sondage (~15s, meme
  cycle que les widgets) et pousse une couleur hex vers l'ecran
  (`streamdeck_companion/ha_client.py::light_color_hex()`).
- **Ampoule RGB** : sa vraie couleur (`attributes.rgb_color`).
- **Ampoule "blanc variable"** (temperature de couleur, sans RGB propre) :
  couleur approximee depuis `color_temp_kelvin`/`color_temp` (algorithme
  de Tanner Helland - assez fidele pour un indicateur visuel, pas une
  reproduction exacte).
- **Ampoule on/off simple** (aucune info de couleur) : un blanc chaud
  generique tant qu'elle est allumee.
- **Eteinte** : le bouton revient a sa couleur par defaut.

Cote firmware, chaque emplacement expose une 5e entite `text` ("Slot N -
couleur", format `#RRGGBB`) qui met a jour le fond du bouton via
`lvgl.obj.update` (voir `firmware/slots_*.yaml`) - **necessite de
reflasher le firmware** pour beneficier de cette fonctionnalite, un
`git pull` cote appli PC ne suffit pas.

## Reglage couleur/chaleur/intensite par appui long

Sur un emplacement `bouton` eligible (meme condition que ci-dessus :
action `home_assistant` domaine `light` + case "Afficher la couleur..."
cochee), un **appui long** sur l'ecran ouvre un mode reglage en direct via
les 3 encodeurs :

- **Encodeur 1** : teinte (hue).
- **Encodeur 2** : temperature de couleur (chaleur).
- **Encodeur 3** : intensite (luminosite).

Chaque cran d'encodeur met a jour l'apercu sur le bouton immediatement et
appelle Home Assistant en direct (limite a ~8 appels/s max par axe pour ne
pas le spammer si l'encodeur tourne vite - voir
`device_client.py::_send_color_mode_update`). Le mode se ferme tout seul
apres 10s d'inactivite, ou en touchant le bouton "X" qui apparait en haut
a droite de l'ecran pendant le reglage. **Necessite de reflasher le
firmware** (nouvel evenement `hold_N` par emplacement, bouton "X" flottant
et switch `Mode couleur actif` dans `firmware/package.yaml`).

## Ajustement tactile des widgets "barre"

Un emplacement de type `barre` avec une source Home Assistant configuree
(champ "Source Home Assistant") accepte maintenant le tactile directement
sur l'ecran : toucher la **moitie gauche** diminue la valeur de 5%,
la **moitie droite** l'augmente - via deux zones tactiles invisibles
superposees au widget (voir `firmware/slot_widgets.yaml`), actives
uniquement quand l'emplacement est bien de type `barre`. Domaines pris en
charge : `light` (luminosite), `media_player` (volume), `fan` (vitesse),
`cover` (position) - voir `ha_client.py::adjust_entity_percent()`.
**Necessite de reflasher le firmware.**

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
- Le changement de sortie audio (`audio_devices.py`) passe par une interface
  COM non documentee par Microsoft (`IPolicyConfig::SetDefaultEndpoint`,
  identique a ce qu'utilisent les Parametres son de Windows en interne et
  des outils comme EarTrumpet/SoundSwitch - aucune API publique n'existe
  pour ca). Le picker/l'enumeration des peripheriques (`pycaw`) est fiable,
  mais le changement effectif n'a pas pu etre teste sur une vraie machine
  Windows depuis ce sandbox de developpement - a confirmer.
- Le mode reglage couleur/chaleur/intensite par appui long et
  l'ajustement tactile des widgets "barre" reposent sur du code LVGL/C++
  (appui long, zones tactiles superposees, evenements) qui n'a pas pu
  etre compile ni teste sur du vrai materiel depuis ce sandbox Linux (pas
  d'ESP32-P4 ni d'ecran tactile disponibles ici) - la logique cote appli
  PC (calcul teinte/chaleur/intensite, ajustement pourcentage, limitation
  de frequence) est testee unitairement avec des reponses HA simulees,
  mais l'integration firmware complete reste a confirmer sur l'appareil
  reel apres reflash.
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
  REST toutes les ~15s (`ha_poller.py`), pas en temps reel instantane -
  meme cadence pour la couleur d'une ampoule liee a un bouton (pas de
  changement instantane au moment du clic, jusqu'a ~15s de decalage).
- L'approximation de couleur pour les ampoules "blanc variable" (sans
  RGB propre, juste une temperature de couleur) est une conversion
  standard temperature -> RGB (Tanner Helland), pas une calibration
  fidele a un modele d'ampoule precis - suffisant comme indicateur visuel.
- La couleur de bouton necessite de **reflasher le firmware** (nouvelle
  entite `Slot N - couleur` par emplacement, voir `firmware/slots_*.yaml`)
  en plus de mettre a jour l'appli PC.
- Le picker d'entites Home Assistant charge **toutes** les entites de
  l'installation (`GET /api/states`, pas de filtre par domaine cote
  serveur) - fonctionne bien jusqu'a quelques centaines d'entites, la
  recherche est limitee aux 50 premiers resultats affiches par requete.
  Testee avec des donnees simulees (pas de vraie instance Home Assistant
  accessible depuis le sandbox de developpement) - a confirmer sur votre
  installation reelle.
- Les services proposes par domaine dans le picker d'action
  `home_assistant` sont une liste courante curatee
  (`ha_client.py::COMMON_SERVICES`), pas une introspection complete de
  l'API Home Assistant - pour un service plus specifique/rare, tapez
  directement le format compact `domaine.service:entite` dans le champ en
  dessous.
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
  personnalise -, picker d'entites Home Assistant - recherche, selection,
  choix de service -, creation/edition/suppression de profils, sauvegarde,
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
