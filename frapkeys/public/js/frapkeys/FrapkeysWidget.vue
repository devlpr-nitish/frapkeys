<template>
	<button
		id="frapkeys-navbar-button"
		type="button"
		class="frapkeys-navbar-button"
		aria-controls="frapkeys-shortcut-dialog"
		:aria-expanded="dialogOpen"
		:title="t('Keyboard Shortcuts')"
		@click="openDialog"
	>
		<svg viewBox="0 0 24 24" aria-hidden="true">
			<rect x="3" y="5" width="18" height="14" rx="2" />
			<path d="M7 9h.01M11 9h.01M15 9h.01M18 9h.01M7 13h.01M11 13h.01M15 13h.01M8 16h8" />
		</svg>
		<span class="sr-only">{{ t("Keyboard Shortcuts") }}</span>
	</button>

	<Teleport to="body">
		<div v-if="dialogOpen" class="frapkeys-modal-backdrop" @mousedown.self="closeDialog">
			<section
				id="frapkeys-shortcut-dialog"
				class="frapkeys-modal"
				role="dialog"
				aria-modal="true"
				aria-labelledby="frapkeys-dialog-title"
			>
				<header class="frapkeys-modal__header">
					<div>
						<h2 id="frapkeys-dialog-title">{{ t("Keyboard Shortcuts") }}</h2>
						<p>{{ t("Shortcuts currently available to you in Desk.") }}</p>
					</div>
					<button type="button" class="frapkeys-icon-button" :aria-label="t('Close')" @click="closeDialog">
						<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
					</button>
				</header>

				<div class="frapkeys-modal__body">
					<div v-if="loading" class="frapkeys-empty-state">{{ t("Loading shortcuts…") }}</div>
					<div v-else-if="errorMessage" class="frapkeys-empty-state frapkeys-error">
						{{ errorMessage }}
					</div>
					<div v-else-if="!shortcuts.length" class="frapkeys-empty-state">
						{{ t("No shortcuts have been configured yet.") }}
					</div>
					<div v-else class="frapkeys-shortcut-list">
						<article v-for="shortcut in shortcuts" :key="shortcut.name" class="frapkeys-shortcut-row">
							<div class="frapkeys-shortcut-copy">
								<strong>{{ shortcut.shortcut_name }}</strong>
								<p>{{ shortcut.description }}</p>
							</div>
							<div class="frapkeys-shortcut-actions">
								<kbd>{{ formatShortcut(shortcut.key_combination) }}</kbd>
								<button v-if="canManage" type="button" class="btn btn-xs btn-default" @click="editShortcut(shortcut)">
									{{ t("Edit") }}
								</button>
							</div>
						</article>
					</div>
				</div>

				<footer class="frapkeys-modal__footer">
					<button v-if="canManage" type="button" class="btn btn-default btn-sm" @click="manageShortcuts">
						{{ t("Manage Shortcuts") }}
					</button>
					<div class="frapkeys-modal__footer-end">
						<button type="button" class="btn btn-default btn-sm" @click="closeDialog">{{ t("Close") }}</button>
						<button v-if="canManage" type="button" class="btn btn-primary btn-sm" @click="addShortcut">
							{{ t("Add Shortcut") }}
						</button>
					</div>
				</footer>
			</section>
		</div>
	</Teleport>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
	initialShortcuts: { type: Array, default: () => [] },
	canManage: { type: Boolean, default: false },
});

const dialogOpen = ref(false);
const loading = ref(false);
const errorMessage = ref("");
const shortcuts = ref([...props.initialShortcuts]);
const isMac = /Mac|iPhone|iPad|iPod/i.test(navigator.userAgentData?.platform || navigator.platform || "");

const t = (message) => (window.__ ? window.__(message) : message);

function formatShortcut(value) {
	const labels = {
		ctrl: isMac ? "⌘" : "Ctrl",
		left_ctrl: "Left Ctrl",
		right_ctrl: "Right Ctrl",
		left_cmd: "Left ⌘",
		right_cmd: "Right ⌘",
		alt: isMac ? "⌥" : "Alt",
		left_alt: isMac ? "Left ⌥" : "Left Alt",
		right_alt: isMac ? "Right ⌥" : "Right Alt",
		shift: isMac ? "⇧" : "Shift",
		left_shift: isMac ? "Left ⇧" : "Left Shift",
		right_shift: isMac ? "Right ⇧" : "Right Shift",
	};
	return String(value || "")
		.split("+")
		.map((part) => {
			return labels[part] ||
				(part.length === 1 ? part.toUpperCase() : part[0].toUpperCase() + part.slice(1));
		})
		.join(isMac ? " " : " + ");
}

async function loadShortcuts() {
	loading.value = true;
	errorMessage.value = "";
	try {
		const response = await fetch("/api/method/frapkeys.api.shortcuts.get_shortcuts", {
			headers: { Accept: "application/json" },
			credentials: "same-origin",
		});
		const result = await response.json();
		if (!response.ok || !result.message) throw new Error(t("Unable to load shortcuts."));
		shortcuts.value = result.message.shortcuts || [];
	} catch (error) {
		errorMessage.value = error.message || t("Unable to load shortcuts.");
	} finally {
		loading.value = false;
	}
}

function openDialog() {
	dialogOpen.value = true;
	loadShortcuts();
}

function closeDialog() {
	dialogOpen.value = false;
}

function addShortcut() {
	closeDialog();
	window.frappe?.new_doc("Frapkeys Shortcut");
}

function manageShortcuts() {
	closeDialog();
	window.frappe?.set_route("List", "Frapkeys Shortcut");
}

function editShortcut(shortcut) {
	closeDialog();
	window.frappe?.set_route("Form", "Frapkeys Shortcut", shortcut.name);
}

function closeOnEscape(event) {
	if (event.key === "Escape" && dialogOpen.value) closeDialog();
}

function applyRefreshedShortcuts(event) {
	shortcuts.value = event.detail?.shortcuts || [];
}

onMounted(() => {
	document.addEventListener("keydown", closeOnEscape);
	window.addEventListener("frapkeys:open", openDialog);
	window.addEventListener("frapkeys:shortcuts-refreshed", applyRefreshedShortcuts);
});
onBeforeUnmount(() => {
	document.removeEventListener("keydown", closeOnEscape);
	window.removeEventListener("frapkeys:open", openDialog);
	window.removeEventListener("frapkeys:shortcuts-refreshed", applyRefreshedShortcuts);
});
</script>
