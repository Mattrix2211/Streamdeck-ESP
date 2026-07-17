/* Maquette fidele de l'ecran (memes proportions/disposition que le
 * firmware) : les emplacements visibles s'affichent dans la grille de
 * l'ecran, les masques dans une "tray" a part (rien de tout ca n'apparait
 * sur l'ecran reel). Popup de config par emplacement, glisser-deposer
 * (echange) entre n'importe quels deux emplacements, meme entre l'ecran
 * et la tray. Pas de framework - vanilla JS. */

let slots = INITIAL_SLOTS.map((s) => ({ ...s }));
let encoders = INITIAL_ENCODERS.map((e) => ({ ...e }));
let dragSrcIndex = null;
let currentIndex = null;
let currentEncoderIndex = null;

const screenGrid = document.getElementById("slot-grid");
const hiddenTray = document.getElementById("hidden-tray");
const encoderMock = document.getElementById("encoder-mock");
const modal = document.getElementById("slot-modal");
const encoderModal = document.getElementById("encoder-modal");
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
  icon.textContent = iconChar(slot.icon);
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
}

function updateLaunchPickerVisibility() {
  const isLaunch = document.getElementById("modal-action-type").value === "launch";
  document.getElementById("modal-app-library").style.display = isLaunch ? "block" : "none";
  document.getElementById("modal-action-target").placeholder = isLaunch
    ? "Choisissez une application ci-dessus, ou tapez une commande"
    : "ctrl+shift+s / https://... / vol_up / light.toggle:light.bureau";
  if (isLaunch) loadAppLibraryIfNeeded();
}

/* Bibliotheque d'applications du picker "launch" : detectees (menu
 * Demarrer, via app_library.py) + personnalisees (ajoutees via la tuile
 * "+ Ajouter", persistees cote serveur - custom_apps.py). Chargee une
 * seule fois par session, la tuile "+ Ajouter" met a jour le cache local
 * ensuite sans recharger. */
let appLibrary = null;
let selectedAppTarget = null;

function loadAppLibraryIfNeeded() {
  if (appLibrary !== null) { renderAppGrid(); return; }
  const status = document.getElementById("modal-app-status");
  status.textContent = "Chargement de la bibliotheque d'applications...";
  fetch("/installed-apps")
    .then((r) => r.json())
    .then((data) => {
      appLibrary = { detected: data.apps || [], custom: data.custom || [] };
      status.textContent = data.detect_error
        ? "Detection automatique indisponible sur ce systeme - ajoutez vos applications avec \"+ Ajouter\"."
        : "";
      renderAppGrid();
    })
    .catch(() => {
      appLibrary = { detected: [], custom: [] };
      status.textContent = "Impossible de charger la bibliotheque d'applications.";
      renderAppGrid();
    });
}

function renderAppGrid() {
  const grid = document.getElementById("modal-app-grid");
  grid.innerHTML = "";
  if (!appLibrary) return;

  const query = document.getElementById("modal-app-search").value.trim().toLowerCase();
  const all = [
    ...appLibrary.custom.map((a) => ({ ...a, custom: true })),
    ...appLibrary.detected,
  ].filter((a) => a.name.toLowerCase().includes(query));

  all.forEach((app) => grid.appendChild(makeAppTile(app)));

  const addTile = document.createElement("div");
  addTile.className = "app-tile add-tile";
  addTile.title = "Ajouter une application a la bibliotheque";
  addTile.innerHTML = '<div class="app-icon">+</div><div class="app-name">Ajouter...</div>';
  addTile.addEventListener("click", addCustomApp);
  grid.appendChild(addTile);
}

function makeAppTile(app) {
  const tile = document.createElement("div");
  tile.className = "app-tile" + (app.target === selectedAppTarget ? " selected" : "");
  tile.title = app.name;

  const icon = document.createElement("div");
  icon.className = "app-icon";
  icon.textContent = "\uE5C3"; /* "apps" (Material Icons) - glyphe generique */
  tile.appendChild(icon);

  const name = document.createElement("div");
  name.className = "app-name";
  name.textContent = app.name;
  tile.appendChild(name);

  tile.addEventListener("click", () => selectApp(app));

  if (app.custom) {
    const remove = document.createElement("div");
    remove.className = "app-remove";
    remove.textContent = "Retirer";
    remove.addEventListener("click", (e) => { e.stopPropagation(); removeCustomApp(app.target); });
    tile.appendChild(remove);
  }

  return tile;
}

function selectApp(app) {
  selectedAppTarget = app.target;
  document.getElementById("modal-action-target").value = app.target;
  const labelField = document.getElementById("modal-label");
  if (!labelField.value.trim() || /^Slot \d+$/.test(labelField.value.trim())) {
    labelField.value = app.name;
  }
  renderAppGrid();
}

function addCustomApp() {
  fetch("/custom-apps", { method: "POST" })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert("Impossible d'ouvrir le selecteur de fichier : " + data.error);
        return;
      }
      if (!data.target) return;
      appLibrary.custom = data.apps || appLibrary.custom;
      selectApp({ name: data.name, target: data.target });
    })
    .catch(() => alert("Impossible de contacter l'appli pour ouvrir le selecteur de fichier."));
}

function removeCustomApp(target) {
  fetch("/custom-apps/remove", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: "target=" + encodeURIComponent(target),
  })
    .then((r) => r.json())
    .then((data) => {
      appLibrary.custom = data.apps || [];
      renderAppGrid();
    })
    .catch(() => {});
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
document.getElementById("modal-app-search").addEventListener("input", renderAppGrid);
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

document.getElementById("config-form").addEventListener("submit", () => {
  document.getElementById("slots_json").value = JSON.stringify(slots);
  document.getElementById("encoders_json").value = JSON.stringify(encoders);
});

renderGrid();
renderEncoderMock();
