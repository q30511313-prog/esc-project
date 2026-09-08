#!/usr/bin/env python3
"""Harden the D5 direct-install handover on Android 12+.

The old D5 build was based on an upstream revision that allowed a manual
"plugin released" acknowledgement after peer discovery. On Android 12+ that is
not evidence that Samsung's plugin has released the accessory channel: the only
observable release condition is that the plugin's Nearby devices permission is
actually off. A false acknowledgement can therefore make the UI claim READY and
COMPLETE while the watch keeps the previous face.

This patch makes the modern-Android rule an invariant rather than an instruction:
- refreshEnvironment clears/ignores manual acknowledgement on API 31+;
- install refuses to start unless pluginNearbyGranted is explicitly false;
- the manual acknowledgement button is only rendered on pre-Android-12 devices.
"""

from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_golden_d5_transport_fix.py FITFACE_ROOT")

    root = Path(sys.argv[1]).resolve()
    installer = root / (
        "core/delivery/src/main/kotlin/dev/fitface/studio/core/delivery/"
        "Fit3DirectInstaller.kt"
    )
    editor = root / (
        "feature/editor/src/main/kotlin/dev/fitface/studio/feature/editor/"
        "EditorScreen.kt"
    )

    replace_once(
        installer,
        """        mutableState.update { current ->
            val nextPhase = when {
                current.isTerminal -> current.phase
                current.isActive -> current.phase
""",
        """        mutableState.update { current ->
            // API 31+ has an observable, per-app Nearby devices switch. A manual
            // acknowledgement is not evidence that the stock plugin released the
            // accessory channel, so never carry or consult it on modern Android.
            val effectiveReleaseAcknowledgement =
                current.pluginNearbyReleaseAcknowledged &&
                    Build.VERSION.SDK_INT < Build.VERSION_CODES.S
            val nextPhase = when {
                current.isTerminal -> current.phase
                current.isActive -> current.phase
""",
        "refreshEnvironment modern handover invariant",
    )

    replace_once(
        installer,
        """                current.peersCached &&
                    (pluginGranted == false || current.pluginNearbyReleaseAcknowledged) ->
                    DirectInstallPhase.READY
""",
        """                current.peersCached &&
                    (pluginGranted == false || effectiveReleaseAcknowledgement) ->
                    DirectInstallPhase.READY
""",
        "refreshEnvironment READY gate",
    )

    replace_once(
        installer,
        """                pluginNearbyGranted = pluginGranted,
                message = if (nextPhase == current.phase && current.isTerminal) {
""",
        """                pluginNearbyGranted = pluginGranted,
                pluginNearbyReleaseAcknowledged = effectiveReleaseAcknowledgement,
                message = if (nextPhase == current.phase && current.isTerminal) {
""",
        "refreshEnvironment clears modern manual acknowledgement",
    )

    replace_once(
        installer,
        """        if (!current.pluginChannelReleased) {
            mutableState.update {
""",
        """        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            current.pluginNearbyGranted != false
        ) {
            mutableState.update {
                it.copy(
                    phase = DirectInstallPhase.PEERS_CACHED,
                    pluginNearbyReleaseAcknowledged = false,
                    message = "Turn the stock Fit3 plugin's Nearby devices access OFF, " +
                        "then return here. Disconnecting the watch or acknowledging the " +
                        "handoff does not release the channel on Android 12+.",
                )
            }
            return
        }
        if (!current.pluginChannelReleased) {
            mutableState.update {
""",
        "install modern permission gate",
    )

    replace_once(
        installer,
        """    fun confirmPluginChannelReleased() {
        mutableState.update {
""",
        """    fun confirmPluginChannelReleased() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            // The permission state is the proof on modern Android. Keeping this guard
            // as well as the UI gate prevents a stale/programmatic acknowledgement from
            // bypassing the handover contract.
            mutableState.update {
                it.copy(
                    pluginNearbyReleaseAcknowledged = false,
                    phase = if (it.peersCached) DirectInstallPhase.PEERS_CACHED else it.phase,
                    message = if (it.peersCached) {
                        "Turn the stock Fit3 plugin's Nearby devices access OFF first."
                    } else {
                        it.message
                    },
                )
            }
            return
        }
        mutableState.update {
""",
        "confirmPluginChannelReleased modern guard",
    )

    replace_once(
        editor,
        """        if (state.peersCached && !state.pluginChannelReleased) {
            FitButton(
                stringResource(R.string.editor_setup_confirm_released),
""",
        """        if (state.peersCached && !state.pluginChannelReleased && !nearbySwitch) {
            FitButton(
                stringResource(R.string.editor_setup_confirm_released),
""",
        "hide manual release confirmation on Android 12+",
    )

    print("Golden D5 Android 12+ transport handover fix applied")


if __name__ == "__main__":
    main()
