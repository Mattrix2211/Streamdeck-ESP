"""Execution des actions locales declenchees par le Stream Deck."""

import platform
import subprocess
import webbrowser

try:
    import keyboard
except ImportError:
    keyboard = None

SYSTEM = platform.system()  # "Windows", "Linux" ou "Darwin"

# Noms reconnus par le module `keyboard` pour les touches multimedia
# (fonctionne sur Windows et Linux/X11 - pas sur macOS, voir _media_macos).
_MEDIA_KEYS = {
    "play_pause": "play/pause media",
    "next": "next track",
    "previous": "previous track",
    "vol_up": "volume up",
    "vol_down": "volume down",
    "mute": "volume mute",
}


def run(action: dict) -> None:
    """Execute une action decrite par un dict {type, target} depuis config.yaml."""
    kind = action.get("type")
    target = action.get("target")
    if kind == "keys":
        _send_keys(target)
    elif kind == "launch":
        _launch(target)
    elif kind == "url":
        webbrowser.open(target)
    elif kind == "media":
        _media(target)
    elif kind == "audio_output":
        from . import audio_devices
        audio_devices.set_default_playback_device(target)
    elif kind == "app_volume":
        _app_volume(target)
    elif kind == "app_mute":
        _app_mute(target)
    else:
        raise ValueError(f"Type d'action inconnu: {kind!r}")


def _send_keys(keys: list) -> None:
    if keyboard is None:
        raise RuntimeError(
            "Le module 'keyboard' n'est pas disponible sur cette plateforme"
        )
    keyboard.send("+".join(keys))


def _launch(target: str) -> None:
    # shell=True (plutot que os.startfile/Popen liste) pour supporter les
    # cibles avec arguments (ex: Discord se lance via
    # "%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe" sur
    # Windows, un jeu peut avoir des flags de lancement...) ET les chemins
    # de raccourci .lnk (voir app_library.py) - le shell les ouvre via la
    # meme association que l'Explorateur, donc la cible reelle est toujours
    # suivie meme si une appli auto-mise-a-jour a change de dossier. La
    # cible vient de la config de l'utilisateur (dashboard_config.yaml),
    # pas d'une entree distante non authentifiee.
    if SYSTEM == "Darwin" and not target.strip().startswith("open "):
        subprocess.Popen(["open", target])  # noqa: S603
    else:
        subprocess.Popen(target, shell=True)  # noqa: S602,S607


def _media(name: str) -> None:
    if name not in _MEDIA_KEYS:
        raise ValueError(f"Touche multimedia inconnue: {name!r}")
    if SYSTEM == "Darwin":
        _media_macos(name)
        return
    if keyboard is None:
        raise RuntimeError(
            "Le module 'keyboard' n'est pas disponible sur cette plateforme"
        )
    keyboard.send(_MEDIA_KEYS[name])


def _app_volume(target: str) -> None:
    """target: 'up:<app_key>' / 'down:<app_key>' (voir app_volume.py) -
    meme convention que 'media' vol_up/vol_down, mais pour une appli
    precise plutot que le volume general Windows."""
    direction_str, _, app_key = target.partition(":")
    if not app_key or direction_str not in ("up", "down"):
        raise ValueError(f"Cible de volume par application invalide: {target!r}")
    from . import app_volume
    app_volume.adjust_app_volume(app_key, 1 if direction_str == "up" else -1)


def _app_mute(app_key: str) -> None:
    """target: nom du processus (ex 'chrome.exe') - bascule le mute de
    cette session audio, typiquement configure sur l'appui d'un encodeur
    dont la rotation regle deja le volume via 'app_volume'."""
    if not app_key:
        raise ValueError("Cible de coupure du son par application invalide")
    from . import app_volume
    app_volume.toggle_app_mute(app_key)


def _media_macos(name: str) -> None:
    # macOS ne permet pas d'emuler les touches multimedia sans permissions
    # d'accessibilite ni outil tiers (ex: nowplaying-cli). Seul le volume
    # systeme est gere ici nativement via osascript.
    if name == "vol_up":
        subprocess.run(
            ["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 10)"],
            check=False,
        )
    elif name == "vol_down":
        subprocess.run(
            ["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 10)"],
            check=False,
        )
    elif name == "mute":
        subprocess.run(["osascript", "-e", "set volume with output muted"], check=False)
    else:
        raise NotImplementedError(
            f"'{name}' necessite un outil tiers sur macOS (voir pc-app/README.md)"
        )
