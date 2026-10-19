<template>
	<div class="frapkeys-recorder">
		<div class="frapkeys-recorder__heading">
			<div>
				<strong>Record key combination</strong>
				<p>Click Record, then press the shortcut. Left and right modifier keys are saved separately.</p>
			</div>
			<span class="frapkeys-platform-badge">{{ platformLabel }}</span>
		</div>

		<div class="frapkeys-recorder__controls">
			<div class="frapkeys-recorder__value" :class="{ 'is-recording': recording }">
				<template v-if="recording">
					<span class="frapkeys-recording-dot"></span>
					Press keys now…
				</template>
				<kbd v-else-if="currentValue">{{ displayShortcut(currentValue) }}</kbd>
				<span v-else class="text-muted">No key combination recorded</span>
			</div>
			<button type="button" class="btn btn-default btn-sm" @click="toggleRecording">
				{{ recording ? "Cancel" : "Record" }}
			</button>
			<button v-if="currentValue" type="button" class="btn btn-link btn-sm" @click="clearShortcut">
				Clear
			</button>
		</div>

		<p v-if="message" class="frapkeys-recorder__message" :class="{ 'text-danger': hasError }">
			{{ message }}
		</p>
		<p v-else class="frapkeys-recorder__hint">
			{{ platformHint }} Function keys can be recorded without a modifier.
		</p>
	</div>
</template>

<script setup>
import { onBeforeUnmount, ref } from "vue";

const props = defineProps({
	initialValue: { type: String, default: "" },
	onRecorded: { type: Function, required: true },
});

const isMac = /Mac|iPhone|iPad|iPod/i.test(navigator.userAgentData?.platform || navigator.platform || "");
const platformLabel = isMac ? "macOS" : /Win/i.test(navigator.platform || "") ? "Windows" : "Linux";
const platformHint = isMac
	? "Left/Right Command and Option are distinct. A generic Ctrl shortcut still accepts either Command key."
	: "Left/Right Ctrl, Alt, and Shift are distinct. Generic modifiers still accept either side.";
const currentValue = ref(props.initialValue);
const recording = ref(false);
const message = ref("");
const hasError = ref(false);
const pressedModifierCodes = new Set();
const modifierTokenByCode = {
	ControlLeft: "left_ctrl",
	ControlRight: "right_ctrl",
	MetaLeft: "left_cmd",
	MetaRight: "right_cmd",
	AltLeft: "left_alt",
	AltRight: "right_alt",
	ShiftLeft: "left_shift",
	ShiftRight: "right_shift",
};
const modifierOrder = [
	"left_ctrl",
	"right_ctrl",
	"left_cmd",
	"right_cmd",
	"left_alt",
	"right_alt",
	"left_shift",
	"right_shift",
];

function displayPart(part) {
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
	return labels[part] || (part.length === 1 ? part.toUpperCase() : part[0].toUpperCase() + part.slice(1));
}

function displayShortcut(value) {
	return String(value)
		.split("+")
		.map(displayPart)
		.join(isMac ? " " : " + ");
}

function keyFromEvent(event) {
	if (/^Key[A-Z]$/.test(event.code)) return event.code.slice(3).toLowerCase();
	if (/^Digit[0-9]$/.test(event.code)) return event.code.slice(5);
	if (/^F([1-9]|1[0-2])$/.test(event.code)) return event.code.toLowerCase();
	const codeKeys = {
		Slash: "/",
		Period: ".",
		Comma: ",",
		Semicolon: ";",
		Quote: "'",
		BracketLeft: "[",
		BracketRight: "]",
		Minus: "-",
		Equal: "=",
	};
	if (codeKeys[event.code]) return codeKeys[event.code];

	const aliases = {
		" ": "space",
		Escape: "esc",
		ArrowUp: "up",
		ArrowDown: "down",
		ArrowLeft: "left",
		ArrowRight: "right",
		PageUp: "pageup",
		PageDown: "pagedown",
	};
	return aliases[event.key] || String(event.key || "").toLowerCase();
}

function captureShortcut(event) {
	if (!recording.value) return;
	if (modifierTokenByCode[event.code]) {
		pressedModifierCodes.add(event.code);
		return;
	}

	event.preventDefault();
	event.stopPropagation();
	event.stopImmediatePropagation();

	const key = keyFromEvent(event);
	const isFunctionKey = /^f([1-9]|1[0-2])$/.test(key);
	const modifiers = [...pressedModifierCodes]
		.map((code) => modifierTokenByCode[code])
		.sort((left, right) => modifierOrder.indexOf(left) - modifierOrder.indexOf(right));
	const genericFamilies = new Set(
		modifiers.map((modifier) => {
			if (modifier.endsWith("_ctrl") || modifier.endsWith("_cmd")) return "ctrl";
			if (modifier.endsWith("_alt")) return "alt";
			if (modifier.endsWith("_shift")) return "shift";
			return modifier;
		})
	);
	if ((event.ctrlKey || event.metaKey) && !genericFamilies.has("ctrl")) modifiers.push("ctrl");
	if (event.altKey && !genericFamilies.has("alt")) modifiers.push("alt");
	if (event.shiftKey && !genericFamilies.has("shift")) modifiers.push("shift");

	if (!key || (!modifiers.length && !isFunctionKey)) {
		hasError.value = true;
		message.value = "Use at least one modifier with letters or numbers.";
		return;
	}

	const value = [...modifiers, key].join("+");
	currentValue.value = value;
	props.onRecorded(value);
	stopRecording();
	hasError.value = false;
	message.value = `Recorded ${displayShortcut(value)}`;
}

function releaseModifier(event) {
	if (modifierTokenByCode[event.code]) pressedModifierCodes.delete(event.code);
}

function clearPressedModifiers() {
	pressedModifierCodes.clear();
}

function startRecording() {
	recording.value = true;
	message.value = "";
	hasError.value = false;
	window.addEventListener("keydown", captureShortcut, true);
	window.addEventListener("keyup", releaseModifier, true);
	window.addEventListener("blur", clearPressedModifiers);
}

function stopRecording() {
	recording.value = false;
	window.removeEventListener("keydown", captureShortcut, true);
	window.removeEventListener("keyup", releaseModifier, true);
	window.removeEventListener("blur", clearPressedModifiers);
	clearPressedModifiers();
}

function toggleRecording() {
	if (recording.value) stopRecording();
	else startRecording();
}

function clearShortcut() {
	currentValue.value = "";
	message.value = "Shortcut cleared. Record a new combination before saving.";
	hasError.value = false;
	props.onRecorded("");
}

onBeforeUnmount(stopRecording);
</script>
