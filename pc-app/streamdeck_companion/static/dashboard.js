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

function renderIconPicker(selectedIcon) {
  iconPicker.innerHTML = "";
  const noneChoice = document.createElement("div");
  noneChoice.className = "icon-choice none-choice" + (selectedIcon ? "" : " selected");
  noneChoice.textContent = "Aucune";
  noneChoice.dataset.icon = "";
  noneChoice.addEventListener("click", () => selectIcon(""));
  iconPicker.appendChild(noneChoice);

  ICON_CHOICES.forEach((choice) => {
    const el = document.createElement("div");
    el.className = "icon-choice" + (choice.key === selectedIcon ? " selected" : "");
    el.textContent = choice.char;
    el.title = choice.label;
    el.dataset.icon = choice.key;
    el.addEventListener("click", () => selectIcon(choice.key));
    iconPicker.appendChild(el);
  });
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

function makeTile(slot, index) {
  const tile = document.createElement("div");
  tile.className = "slot-tile shape-" + (SHAPE === "rond" ? "rond" : "carre");
  if (slot.type && slot.type !== "bouton") tile.classList.add("has-widget");
  tile.draggable = true;
  tile.dataset.index = String(index);

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
  tile.addEventListener("dragover", (e) => { e.preventDefault(); tile.classList.add("drag-over"); });
  tile.addEventListener("dragleave", () => tile.classList.remove("drag-over"));
  tile.addEventListener("drop", (e) => {
    e.preventDefault();
    tile.classList.remove("drag-over");
    if (dragSrcIndex === null || dragSrcIndex === index) return;
    const tmp = slots[index];
    slots[index] = slots[dragSrcIndex];
    slots[dragSrcIndex] = tmp;
    dragSrcIndex = null;
    renderGrid();
  });

  return tile;
}

function renderGrid() {
  screenGrid.innerHTML = "";
  hiddenTray.innerHTML = "";
  let hiddenCount = 0;

  slots.forEach((slot, index) => {
    const tile = makeTile(slot, index);
    if (slot.visible) {
      screenGrid.appendChild(tile);
    } else {
      hiddenTray.appendChild(tile);
      hiddenCount += 1;
    }
  });

  if (hiddenCount === 0) {
    const empty = document.createElement("p");
    empty.className = "hidden-tray-empty";
    empty.textContent = "Aucun - les 16 emplacements sont visibles sur l'ecran.";
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

document.getElementById("modal-apply").addEventListener("click", () => {
  if (currentIndex === null) return;
  const slot = slots[currentIndex];
  slot.visible = document.getElementById("modal-visible").checked;
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

/* Picker "app_volume" (encodeurs) : liste des applications ayant une
 * session audio active (voir app_volume.py::list_audio_sessions et la
 * route /audio-sessions), chargee une seule fois par session comme
 * audioDevices dans audio-devices.js. Le champ cible reste un input texte
 * libre ("up:chrome.exe" / "down:chrome.exe") - ce picker se contente d'y
 * ecrire une valeur, sans empecher de la modifier a la main ensuite. */
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
  const isAppVolume = type === "app_volume";
  select.style.display = isAppVolume ? "block" : "none";
  if (!isAppVolume) return;
  loadAudioSessionsIfNeeded(() => {
    populateEncoderAppPicker(direction);
    const target = document.getElementById(`encoder-modal-${direction}-target`).value;
    const app = target.includes(":") ? target.split(":")[1] : "";
    if (app) select.value = app;
  });
}

function applyEncoderAppSelection(direction) {
  const app = document.getElementById(`encoder-modal-${direction}-app`).value;
  if (!app) return;
  const prefix = direction === "anticlockwise" ? "down" : "up";
  document.getElementById(`encoder-modal-${direction}-target`).value = `${prefix}:${app}`;
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
