/* Grille visuelle des 16 emplacements : rendu, popup de config par
 * emplacement, glisser-deposer (echange deux emplacements). Pas de
 * framework - vanilla JS, coherent avec le reste de l'appli (Flask +
 * template simple, pas d'etape de build). */

let slots = INITIAL_SLOTS.map((s) => ({ ...s }));
let dragSrcIndex = null;
let currentIndex = null;

const grid = document.getElementById("slot-grid");
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

function renderGrid() {
  grid.innerHTML = "";
  slots.forEach((slot, index) => {
    const tile = document.createElement("div");
    tile.className = "slot-tile" + (slot.visible ? "" : " hidden-slot");
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

    const typeTag = document.createElement("div");
    typeTag.className = "type-tag";
    typeTag.textContent = slot.type;
    tile.appendChild(typeTag);

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

    grid.appendChild(tile);
  });
}

function updateModalFieldsVisibility() {
  const type = document.getElementById("modal-type").value;
  document.getElementById("modal-action-fields").style.display = type === "bouton" ? "block" : "none";
  document.getElementById("modal-source-fields").style.display = type === "bouton" ? "none" : "block";
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
