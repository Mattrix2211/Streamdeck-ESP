/* Maquette fidele de l'ecran (memes proportions/disposition que le
 * firmware) : les emplacements visibles s'affichent dans la grille de
 * l'ecran, les masques dans une "tray" a part (rien de tout ca n'apparait
 * sur l'ecran reel). Popup de config par emplacement, glisser-deposer
 * (echange) entre n'importe quels deux emplacements, meme entre l'ecran
 * et la tray. Pas de framework - vanilla JS. */

let slots = INITIAL_SLOTS.map((s) => ({ ...s }));
let dragSrcIndex = null;
let currentIndex = null;

const screenGrid = document.getElementById("slot-grid");
const hiddenTray = document.getElementById("hidden-tray");
const encoderMock = document.getElementById("encoder-mock");
const modal = document.getElementById("slot-modal");
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
  for (let i = 1; i <= 3; i++) {
    const card = document.createElement("div");
    card.className = "encoder-mock-card";

    const icon = document.createElement("div");
    icon.className = "icon";
    icon.textContent = ""; /* volume_up, matche le firmware */
    card.appendChild(icon);

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = `ENCODEUR ${i}`;
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
  updateBrowseButtonVisibility();
}

function updateBrowseButtonVisibility() {
  const isLaunch = document.getElementById("modal-action-type").value === "launch";
  document.getElementById("modal-browse-app").style.display = isLaunch ? "inline-block" : "none";
  document.getElementById("modal-browse-hint").style.display = isLaunch ? "block" : "none";
  document.getElementById("modal-action-target").placeholder = isLaunch
    ? "Choisissez une application ci-dessus, ou tapez une commande"
    : "ctrl+shift+s / https://... / vol_up / light.toggle:light.bureau";
  document.getElementById("modal-app-picker-row").style.display = isLaunch ? "flex" : "none";
  if (isLaunch) loadInstalledAppsIfNeeded();
}

/* null = pas encore charge, false = echec (systeme non supporte), [] ou
 * tableau = charge avec succes. Charge une seule fois par session (la
 * liste ne change pas pendant qu'on configure des emplacements). */
let installedApps = null;

function loadInstalledAppsIfNeeded() {
  if (installedApps !== null) return;
  const picker = document.getElementById("modal-app-picker");
  const status = document.getElementById("modal-app-picker-status");
  status.textContent = "Chargement de la liste des applications...";
  fetch("/installed-apps")
    .then((r) => r.json())
    .then((data) => {
      if (data.error || !data.apps) {
        installedApps = false;
        document.getElementById("modal-app-picker-row").style.display = "none";
        status.textContent = "";
        return;
      }
      installedApps = data.apps;
      installedApps.forEach((app, index) => {
        const opt = document.createElement("option");
        opt.value = String(index);
        opt.textContent = app.name;
        picker.appendChild(opt);
      });
      status.textContent = installedApps.length
        ? `${installedApps.length} applications trouvees.`
        : "Aucune application trouvee - utilisez \"Parcourir...\" ci-dessous.";
    })
    .catch(() => {
      installedApps = false;
      document.getElementById("modal-app-picker-row").style.display = "none";
      status.textContent = "";
    });
}

function applyAppPickerSelection() {
  const picker = document.getElementById("modal-app-picker");
  if (!picker.value || !installedApps) return;
  const app = installedApps[Number(picker.value)];
  if (!app) return;
  document.getElementById("modal-action-target").value = app.target;
  const labelField = document.getElementById("modal-label");
  if (!labelField.value.trim() || /^Slot \d+$/.test(labelField.value.trim())) {
    labelField.value = app.name;
  }
}

function browseForApp() {
  const btn = document.getElementById("modal-browse-app");
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Choix en cours...";
  fetch("/browse-app", { method: "POST" })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert("Impossible d'ouvrir le selecteur de fichier : " + data.error);
        return;
      }
      if (data.path) {
        const target = document.getElementById("modal-action-target");
        target.value = data.path;
        const labelField = document.getElementById("modal-label");
        if (!labelField.value.trim() || /^Slot \d+$/.test(labelField.value.trim())) {
          labelField.value = guessAppName(data.path);
        }
      }
    })
    .catch(() => alert("Impossible de contacter l'appli pour ouvrir le selecteur de fichier."))
    .finally(() => {
      btn.disabled = false;
      btn.textContent = original;
    });
}

function guessAppName(path) {
  const clean = path.replace(/^"|"$/g, "");
  const fileName = clean.split(/[\\/]/).pop() || clean;
  return fileName.replace(/\.(exe|lnk|bat|app)$/i, "");
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
  renderIconPicker(slot.icon || "");
  updateModalFieldsVisibility();
  modal.classList.remove("hidden");
}

function closeModal() {
  modal.classList.add("hidden");
  currentIndex = null;
}

document.getElementById("modal-type").addEventListener("change", updateModalFieldsVisibility);
document.getElementById("modal-action-type").addEventListener("change", updateBrowseButtonVisibility);
document.getElementById("modal-browse-app").addEventListener("click", browseForApp);
document.getElementById("modal-app-picker").addEventListener("change", applyAppPickerSelection);
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

document.getElementById("config-form").addEventListener("submit", () => {
  document.getElementById("slots_json").value = JSON.stringify(slots);
});

renderGrid();
renderEncoderMock();
