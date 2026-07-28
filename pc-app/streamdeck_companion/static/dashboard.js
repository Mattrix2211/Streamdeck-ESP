/* Fichier principal (state partage + maquette d'ecran + popups
 * emplacement/encodeur) - voir aussi app-library.js (bibliotheque
 * d'applications du picker "launch") et profiles.js (onglets de profils),
 * charges apres ce fichier et qui referencent son state/ses fonctions.
 *
 * Maquette fidele de l'ecran (memes proportions/disposition que le
 * firmware) : les emplacements visibles s'affichent dans la grille de
 * l'ecran, les masques dans une "tray" a part (rien de tout ca n'apparait
 * sur l'ecran reel). Popup de config par emplacement/encodeur, glisser-
 * deposer (echange) entre n'importe quels deux emplacements. Plusieurs
 * profils (onglets) - chacun sa propre grille - basculent automatiquement
 * selon l'application au premier plan sur le PC (voir profile_watcher.py).
 * Pas de framework - vanilla JS. */

let profiles = JSON.parse(JSON.stringify(INITIAL_PROFILES));
let activeEditIndex = Math.max(0, profiles.findIndex((p) => p.name === ACTIVE_PROFILE_NAME));
let liveActiveProfileName = ACTIVE_PROFILE_NAME;
let manualOverride = MANUAL_OVERRIDE;
/* `slots`/`encoders` referencent toujours le profil en cours d'edition
 * (activeEditIndex) - memes tableaux, pas une copie : les mutations faites
 * via les popups s'appliquent donc directement a `profiles[activeEditIndex]`.
 * switchProfileTab() les re-pointe vers le profil choisi. */
let slots = profiles[activeEditIndex].slots;
let encoders = profiles[activeEditIndex].encoders;
let dragSrcIndex = null;
let currentIndex = null;
let currentEncoderIndex = null;
let editingProfileIndex = null;

const screenGrid = document.getElementById("slot-grid");
const hiddenTray = document.getElementById("hidden-tray");
const encoderMock = document.getElementById("encoder-mock");
const modal = document.getElementById("slot-modal");
const encoderModal = document.getElementById("encoder-modal");
const profileModal = document.getElementById("profile-modal");
const iconPicker = document.getElementById("icon-picker");

function renderIconPicker(selectedIcon, query) {
  iconPicker.innerHTML = "";
  const noneChoice = document.createElement("div");
  noneChoice.className = "icon-choice none-choice" + (selectedIcon ? "" : " selected");
  noneChoice.textContent = "Aucune";
  noneChoice.dataset.icon = "";
  noneChoice.addEventListener("click", () => selectIcon(""));
  iconPicker.appendChild(noneChoice);

  const q = (query || "").trim().toLowerCase();
  const choices = q
    ? ICON_CHOICES.filter((c) => c.label.toLowerCase().includes(q) || c.key.toLowerCase().includes(q))
    : ICON_CHOICES;

  choices.forEach((choice) => {
    const el = document.createElement("div");
    el.className = "icon-choice" + (choice.key === selectedIcon ? " selected" : "");
    el.textContent = choice.char;
    el.title = choice.label;
    el.dataset.icon = choice.key;
    el.addEventListener("click", () => selectIcon(choice.key));
    iconPicker.appendChild(el);
  });

  if (q && choices.length === 0) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "Aucune icone trouvee.";
    iconPicker.appendChild(empty);
  }
}

function selectIcon(key) {
  document.querySelectorAll(".icon-choice").forEach((el) => {
    el.classList.toggle("selected", el.dataset.icon === key);
  });
  modal.dataset.selectedIcon = key;
}

function iconChar(key) {
  const found = ICON_CHOICES.find((c) => c.key === key);
  return found ? found.char : "";
}

/* Grille invisible de cases carrees (9 colonnes x 4 lignes - voir
 * firmware/slot_grid.yaml, package.yaml::action_grid et
 * profiles.py::GRID_COLS/GRID_ROWS, ces 3 endroits doivent rester
 * coherents) : un emplacement occupe 1 ou plusieurs cases ("colspan"/
 * "rowspan"), facon "sections" de Home Assistant, au lieu d'une grille
 * fixe a une seule taille de tuile. */
const GRID_COLS = 9;
const GRID_ROWS = 4;

function slotGrid(slot) {
  const g = slot.grid || {};
  return {
    col: Math.max(0, Math.min(GRID_COLS - 1, g.col ?? 0)),
    row: Math.max(0, Math.min(GRID_ROWS - 1, g.row ?? 0)),
    colspan: Math.max(1, Math.min(GRID_COLS, g.colspan ?? 1)),
    rowspan: Math.max(1, Math.min(GRID_ROWS, g.rowspan ?? 1)),
  };
}

function rectsOverlap(a, b) {
  return a.col < b.col + b.colspan && a.col + a.colspan > b.col &&
         a.row < b.row + b.rowspan && a.row + a.rowspan > b.row;
}

/* True si `rect` (candidat de position/taille) chevauche un AUTRE
 * emplacement visible que celui d'index `excludeIndex` - empeche de
 * deposer/redimensionner une carte par-dessus une autre. */
function hasCollision(excludeIndex, rect) {
  return slots.some((slot, i) => {
    if (i === excludeIndex || !slot.visible) return false;
    return rectsOverlap(rect, slotGrid(slot));
  });
}

/* Premiere case libre (ordre de lecture) pour un emplacement colspan x
 * rowspan - utilise quand on rend un emplacement visible autrement que par
 * glisser-depose (ex: case a cocher "Visible" de la popup), pour eviter
 * qu'il chevauche silencieusement un autre emplacement deja affiche a la
 * meme position enregistree. */
function findFreeCell(excludeIndex, colspan, rowspan) {
  for (let row = 0; row <= GRID_ROWS - rowspan; row++) {
    for (let col = 0; col <= GRID_COLS - colspan; col++) {
      if (!hasCollision(excludeIndex, { col, row, colspan, rowspan })) return { col, row };
    }
  }
  return { col: 0, row: 0 };
}

function pointToCell(clientX, clientY) {
  const rect = screenGrid.getBoundingClientRect();
  const col = Math.floor(((clientX - rect.left) / rect.width) * GRID_COLS);
  const row = Math.floor(((clientY - rect.top) / rect.height) * GRID_ROWS);
  return {
    col: Math.max(0, Math.min(GRID_COLS - 1, col)),
    row: Math.max(0, Math.min(GRID_ROWS - 1, row)),
  };
}

function attachResizeHandle(tile, index) {
  const handle = document.createElement("div");
  handle.className = "tile-resize-handle";
  handle.draggable = false;
  handle.title = "Glisser pour redimensionner";
  handle.addEventListener("mousedown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const startY = e.clientY;
    const gridRect = screenGrid.getBoundingClientRect();
    const cellW = gridRect.width / GRID_COLS;
    const cellH = gridRect.height / GRID_ROWS;
    const g0 = slotGrid(slots[index]);
    let finalColspan = g0.colspan;
    let finalRowspan = g0.rowspan;

    function onMove(ev) {
      const dCols = Math.round((ev.clientX - startX) / cellW);
      const dRows = Math.round((ev.clientY - startY) / cellH);
      let colspan = Math.max(1, Math.min(GRID_COLS - g0.col, g0.colspan + dCols));
      let rowspan = Math.max(1, Math.min(GRID_ROWS - g0.row, g0.rowspan + dRows));
      while (colspan > 1 && hasCollision(index, { col: g0.col, row: g0.row, colspan, rowspan })) colspan--;
      while (rowspan > 1 && hasCollision(index, { col: g0.col, row: g0.row, colspan, rowspan })) rowspan--;
      finalColspan = colspan;
      finalRowspan = rowspan;
      tile.style.gridColumn = `${g0.col + 1} / span ${colspan}`;
      tile.style.gridRow = `${g0.row + 1} / span ${rowspan}`;
    }
    function onUp() {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      slots[index].grid = { col: g0.col, row: g0.row, colspan: finalColspan, rowspan: finalRowspan };
      renderGrid();
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
  tile.appendChild(handle);
}

function makeTile(slot, index, isGrid) {
  const tile = document.createElement("div");
  tile.className = "slot-tile shape-" + (SHAPE === "rond" ? "rond" : "carre");
  if (slot.type && slot.type !== "bouton") tile.classList.add("has-widget");
  tile.draggable = true;
  tile.dataset.index = String(index);

  if (isGrid) {
    const g = slotGrid(slot);
    tile.style.gridColumn = `${g.col + 1} / span ${g.colspan}`;
    tile.style.gridRow = `${g.row + 1} / span ${g.rowspan}`;
  }

  const icon = document.createElement("div");
  icon.className = "icon";
  const launchTarget = slot.action && slot.action.type === "launch" ? slot.action.target : "";
  if (launchTarget) {
    const img = document.createElement("img");
    img.src = "/preview-icon.png?target=" + encodeURIComponent(launchTarget);
    img.alt = "";
    img.onerror = () => { img.replaceWith(document.createTextNode(iconChar(slot.icon))); };
    icon.appendChild(img);
  } else {
    icon.textContent = iconChar(slot.icon);
  }
  tile.appendChild(icon);

  const label = document.createElement("div");
  label.className = "label";
  label.textContent = slot.label || `Slot ${index + 1}`;
  tile.appendChild(label);

  /* Sur le vrai ecran, "barre"/"texte" affichent une jauge ou une valeur
   * en bas du bouton (masquees pour "bouton") - meme logique ici pour que
   * l'apercu distingue vraiment les 3 types. Pas de valeur live dans le
   * navigateur (c'est ha_poller.py qui pousse la vraie valeur a l'ecran) :
   * on affiche juste un espace reserve pour montrer OU et COMMENT elle
   * s'affichera. */
  if (slot.type === "barre") {
    const bar = document.createElement("div");
    bar.className = "widget-bar";
    bar.appendChild(document.createElement("span"));
    tile.appendChild(bar);
  } else if (slot.type === "texte") {
    const value = document.createElement("div");
    value.className = "widget-value";
    value.textContent = slot.ha_entity ? "--" : "";
    tile.appendChild(value);
  }

  tile.addEventListener("click", () => openModal(index));
  tile.addEventListener("dragstart", () => { dragSrcIndex = index; });
  tile.addEventListener("dragend", () => { dragSrcIndex = null; });

  if (isGrid) attachResizeHandle(tile, index);

  return tile;
}

/* Deplacer/redimensionner se fait au niveau du CONTENEUR (grille ou tray)
 * plutot que par tuile - une tuile deposee "swap" son contenu entier dans
 * l'ancien systeme a taille fixe, incompatible avec une position/taille
 * libre : ici, deposer met a jour la position de la tuile SOURCE (et sa
 * visibilite), sans toucher aux autres. */
screenGrid.addEventListener("dragover", (e) => { e.preventDefault(); screenGrid.classList.add("drag-over"); });
screenGrid.addEventListener("dragleave", (e) => { if (e.target === screenGrid) screenGrid.classList.remove("drag-over"); });
screenGrid.addEventListener("drop", (e) => {
  e.preventDefault();
  screenGrid.classList.remove("drag-over");
  if (dragSrcIndex === null) return;
  const slot = slots[dragSrcIndex];
  const g = slotGrid(slot);
  const target = pointToCell(e.clientX, e.clientY);
  const candidate = {
    col: Math.min(target.col, GRID_COLS - g.colspan),
    row: Math.min(target.row, GRID_ROWS - g.rowspan),
    colspan: g.colspan,
    rowspan: g.rowspan,
  };
  const srcIndex = dragSrcIndex;
  dragSrcIndex = null;
  if (hasCollision(srcIndex, candidate)) return;
  slot.visible = true;
  slot.grid = candidate;
  renderGrid();
});

hiddenTray.addEventListener("dragover", (e) => { e.preventDefault(); hiddenTray.classList.add("drag-over"); });
hiddenTray.addEventListener("dragleave", (e) => { if (e.target === hiddenTray) hiddenTray.classList.remove("drag-over"); });
hiddenTray.addEventListener("drop", (e) => {
  e.preventDefault();
  hiddenTray.classList.remove("drag-over");
  if (dragSrcIndex === null) return;
  slots[dragSrcIndex].visible = false;
  dragSrcIndex = null;
  renderGrid();
});

function renderGrid() {
  screenGrid.innerHTML = "";
  hiddenTray.innerHTML = "";
  let hiddenCount = 0;

  slots.forEach((slot, index) => {
    if (slot.visible) {
      screenGrid.appendChild(makeTile(slot, index, true));
    } else {
      hiddenTray.appendChild(makeTile(slot, index, false));
      hiddenCount += 1;
    }
  });

  if (hiddenCount === 0) {
    const empty = document.createElement("p");
    empty.className = "hidden-tray-empty";
    empty.textContent = "Aucun - tous les emplacements visibles sont sur l'ecran.";
    hiddenTray.appendChild(empty);
  }
}

function renderEncoderMock() {
  encoderMock.innerHTML = "";
  for (let i = 0; i < 3; i++) {
    const card = document.createElement("div");
    card.className = "encoder-mock-card";
    card.addEventListener("click", () => openEncoderModal(i));

    const icon = document.createElement("div");
    icon.className = "icon";
    icon.textContent = ""; /* volume_up, matche le firmware */
    card.appendChild(icon);

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = `ENCODEUR ${i + 1}`;
    card.appendChild(title);

    const bar = document.createElement("div");
    bar.className = "encoder-mock-bar";
    const fill = document.createElement("span");
    bar.appendChild(fill);
    card.appendChild(bar);

    encoderMock.appendChild(card);
  }
}

function updateModalFieldsVisibility() {
  const type = document.getElementById("modal-type").value;
  document.getElementById("modal-action-fields").style.display = type === "bouton" ? "block" : "none";
  document.getElementById("modal-source-fields").style.display = type === "bouton" ? "none" : "block";
  updateLaunchPickerVisibility();
  updateHaSourceVisibility();
}

function updateLaunchPickerVisibility() {
  const isLaunch = document.getElementById("modal-action-type").value === "launch";
  document.getElementById("modal-app-library").style.display = isLaunch ? "block" : "none";
  document.getElementById("modal-action-target").placeholder = isLaunch
    ? "Choisissez une application ci-dessus, ou tapez une commande"
    : "ctrl+shift+s / https://... / vol_up / light.toggle:light.bureau";
  if (isLaunch) loadAppLibraryIfNeeded();
  updateHaActionVisibility();
  updateAudioPickerVisibility();
}

function openModal(index) {
  currentIndex = index;
  const slot = slots[index];
  document.getElementById("modal-title").textContent = `Emplacement ${index + 1}`;
  document.getElementById("modal-visible").checked = !!slot.visible;
  document.getElementById("modal-label").value = slot.label || "";
  document.getElementById("modal-type").value = slot.type || "bouton";
  document.getElementById("modal-action-type").value = (slot.action && slot.action.type) || "none";
  document.getElementById("modal-action-target").value = slot.action_field || "";
  document.getElementById("modal-ha-entity").value = slot.ha_entity || "";
  document.getElementById("modal-show-light-color").checked = !!slot.show_light_color;
  selectedAppTarget = slot.action_field || null;
  modal.dataset.selectedIcon = slot.icon || "";
  document.getElementById("icon-search").value = "";
  renderIconPicker(slot.icon || "");
  updateModalFieldsVisibility();
  modal.classList.remove("hidden");
}

function closeModal() {
  modal.classList.add("hidden");
  currentIndex = null;
}

document.getElementById("modal-type").addEventListener("change", updateModalFieldsVisibility);
document.getElementById("modal-action-type").addEventListener("change", updateLaunchPickerVisibility);
document.getElementById("modal-cancel").addEventListener("click", closeModal);
document.getElementById("icon-search").addEventListener("input", (e) => {
  renderIconPicker(modal.dataset.selectedIcon || "", e.target.value);
});

document.getElementById("modal-apply").addEventListener("click", () => {
  if (currentIndex === null) return;
  const slot = slots[currentIndex];
  const wasVisible = !!slot.visible;
  slot.visible = document.getElementById("modal-visible").checked;
  if (slot.visible && !wasVisible) {
    /* Rendu visible autrement que par glisser-depose (case a cocher) - la
     * position enregistree peut chevaucher un emplacement deja affiche,
     * on cherche alors la premiere case libre plutot que de superposer. */
    const g = slotGrid(slot);
    if (hasCollision(currentIndex, g)) {
      const free = findFreeCell(currentIndex, g.colspan, g.rowspan);
      slot.grid = { col: free.col, row: free.row, colspan: g.colspan, rowspan: g.rowspan };
    }
  }
  slot.label = document.getElementById("modal-label").value.trim() || `Slot ${currentIndex + 1}`;
  slot.type = document.getElementById("modal-type").value;
  slot.icon = modal.dataset.selectedIcon || "";
  slot.action = { type: document.getElementById("modal-action-type").value, target: null };
  slot.action_field = document.getElementById("modal-action-target").value;
  slot.ha_entity = document.getElementById("modal-ha-entity").value.trim();
  slot.show_light_color = document.getElementById("modal-show-light-color").checked;
  renderGrid();
  closeModal();
});

function openEncoderModal(index) {
  currentEncoderIndex = index;
  document.getElementById("encoder-modal-title").textContent = `Encodeur ${index + 1}`;
  const enc = encoders[index];
  DIRECTIONS.forEach((direction) => {
    const d = enc[direction] || { type: "none", target: "" };
    document.getElementById(`encoder-modal-${direction}-type`).value = d.type || "none";
    document.getElementById(`encoder-modal-${direction}-target`).value = d.target || "";
    updateEncoderAppPickerVisibility(direction);
  });
  encoderModal.classList.remove("hidden");
}

function closeEncoderModal() {
  encoderModal.classList.add("hidden");
  currentEncoderIndex = null;
}

document.getElementById("encoder-modal-cancel").addEventListener("click", closeEncoderModal);
document.getElementById("encoder-modal-apply").addEventListener("click", () => {
  if (currentEncoderIndex === null) return;
  const enc = {};
  DIRECTIONS.forEach((direction) => {
    enc[direction] = {
      type: document.getElementById(`encoder-modal-${direction}-type`).value,
      target: document.getElementById(`encoder-modal-${direction}-target`).value,
    };
  });
  encoders[currentEncoderIndex] = enc;
  closeEncoderModal();
});

/* Picker "app_volume"/"app_mute" (encodeurs) : liste des applications
 * ayant une session audio active (voir app_volume.py::list_audio_sessions
 * et la route /audio-sessions), chargee une seule fois par session comme
 * audioDevices dans audio-devices.js. Le champ cible reste un input texte
 * libre ("up:chrome.exe" / "down:chrome.exe" pour app_volume, "chrome.exe"
 * tout court pour app_mute) - ce picker se contente d'y ecrire une valeur,
 * sans empecher de la modifier a la main ensuite. */
let audioSessions = null;

function loadAudioSessionsIfNeeded(callback) {
  if (audioSessions !== null) { callback(null); return; }
  fetch("/audio-sessions")
    .then((r) => r.json())
    .then((data) => {
      audioSessions = data.sessions || [];
      callback(data.error || null);
    })
    .catch(() => {
      audioSessions = [];
      callback("Impossible de contacter l'appli.");
    });
}

function populateEncoderAppPicker(direction) {
  const select = document.getElementById(`encoder-modal-${direction}-app`);
  const current = select.value;
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Choisir une application...";
  select.appendChild(placeholder);
  (audioSessions || []).forEach((session) => {
    const opt = document.createElement("option");
    opt.value = session.key;
    opt.textContent = session.name;
    select.appendChild(opt);
  });
  select.value = current;
}

function updateEncoderAppPickerVisibility(direction) {
  const type = document.getElementById(`encoder-modal-${direction}-type`).value;
  const select = document.getElementById(`encoder-modal-${direction}-app`);
  const needsPicker = type === "app_volume" || type === "app_mute";
  select.style.display = needsPicker ? "block" : "none";
  if (!needsPicker) return;
  loadAudioSessionsIfNeeded(() => {
    populateEncoderAppPicker(direction);
    const target = document.getElementById(`encoder-modal-${direction}-target`).value;
    const app = type === "app_mute" ? target : (target.includes(":") ? target.split(":")[1] : "");
    if (app) select.value = app;
  });
}

function applyEncoderAppSelection(direction) {
  const app = document.getElementById(`encoder-modal-${direction}-app`).value;
  if (!app) return;
  const type = document.getElementById(`encoder-modal-${direction}-type`).value;
  const value = type === "app_mute" ? app : `${direction === "anticlockwise" ? "down" : "up"}:${app}`;
  document.getElementById(`encoder-modal-${direction}-target`).value = value;
}

DIRECTIONS.forEach((direction) => {
  document.getElementById(`encoder-modal-${direction}-type`)
    .addEventListener("change", () => updateEncoderAppPickerVisibility(direction));
  document.getElementById(`encoder-modal-${direction}-app`)
    .addEventListener("change", () => applyEncoderAppSelection(direction));
});

document.getElementById("config-form").addEventListener("submit", () => {
  document.getElementById("profiles_json").value = JSON.stringify(profiles);
});
