"""
Prosody_Lab.py — Interactive Edge-TTS Prosody Testing Lab
==========================================================
An interactive tool to manually test and fine-tune
Speed · Volume · Pitch combinations across Edge-TTS voices.

Features
--------
 ★  Interactive Menu  — tweak any parameter, hear results instantly
 ★  Quick Presets     — jump to named prosody presets (excited, whisper, etc.)
 ★  Matrix Sweep      — auto-generate a grid of combinations & listen/compare
 ★  A/B Compare       — hear two settings back-to-back on the same text
 ★  Save Favorites    — bookmark combos you like → JSON export
 ★  Custom Text       — type your own text or pick from curated samples
 ★  Multi-Voice       — test same prosody across multiple voices at once

Usage
-----
  python Prosody_Lab.py                   # Interactive menu
  python Prosody_Lab.py --sweep           # Run the full matrix sweep
  python Prosody_Lab.py --presets         # Audition all named presets
  python Prosody_Lab.py --ab             # A/B comparison mode
  python Prosody_Lab.py --voice hi-IN-SwaraNeural  # Start with specific voice
"""

import asyncio
import edge_tts
import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime
from itertools import product

# ═══════════════════════════════════════════════════════════════════════════════
#                              CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = "prosody_lab_output"
FAVORITES_FILE = "prosody_favorites.json"

# ── Voice Catalog ────────────────────────────────────────────────────────────
VOICES = {
    "1": ("hi-IN-SwaraNeural",              "Hindi Female (Swara)"),
    "2": ("hi-IN-MadhurNeural",             "Hindi Male (Madhur)"),
    "3": ("en-IN-NeerjaExpressiveNeural",    "English-IN Female (Neerja Expr.)"),
    "4": ("en-IN-PrabhatNeural",            "English-IN Male (Prabhat)"),
    "5": ("en-IN-NeerjaNeural",             "English-IN Female (Neerja)"),
    "6": ("en-US-AriaNeural",               "US English Female (Aria)"),
    "7": ("en-US-GuyNeural",                "US English Male (Guy)"),
    "8": ("en-US-AvaMultilingualNeural",     "Multilingual Female (Ava)"),
    "9": ("en-US-AndrewMultilingualNeural",  "Multilingual Male (Andrew)"),
    "10": ("en-US-BrianMultilingualNeural",  "Multilingual Male (Brian)"),
    "11": ("en-US-EmmaMultilingualNeural",   "Multilingual Female (Emma)"),
    "12": ("ur-IN-GulNeural",               "Urdu Female (Gul)"),
    "13": ("ur-IN-SalmanNeural",            "Urdu Male (Salman)"),
    "14": ("en-GB-RyanNeural",              "British Male (Ryan)"),
    "15": ("en-GB-SoniaNeural",             "British Female (Sonia)"),
}

# ── Sample Texts for Testing ────────────────────────────────────────────────
SAMPLE_TEXTS = {
    "1": (
        "Hinglish Conversation",
        "Arre yaar, aaj ka mausam kaafi acha hai. Chal bahar chalte hain, "
        "coffee peete hain aur kuch interesting baat karte hain."
    ),
    "2": (
        "Hindi Narration",
        "Ek samay ki baat hai, ek raja tha jo bahut nyayapriya tha. "
        "Uske rajya mein sabhi praja sukhi thi."
    ),
    "3": (
        "Hindi Excitement",
        "GOAL! GOAL! GOAL! India ne goal kiya! Kya shandar match tha! "
        "Hum jeet gaye bhai! World Cup hamara hai!"
    ),
    "4": (
        "Hindi Whisper/Secret",
        "Shhh. Dheere bol. Woh sun lega. Sirf tujhe bata raha hoon. "
        "Promise kar pehle ki kisi ko nahi bataayega."
    ),
    "5": (
        "Hindi Sad/Emotional",
        "Aaj ka din kitna acha tha, sab kuch perfect tha. "
        "Lekin shaam ko ek phone aaya, aur sab badal gaya, sab bikhar gaya."
    ),
    "6": (
        "English Narration",
        "It was a bright cold day in April, and the clocks were striking thirteen. "
        "Winston Smith slipped quickly through the glass doors of Victory Mansions."
    ),
    "7": (
        "Mixed Script (Devanagari + Latin)",
        "मैं office जा रहा हूँ, meeting है 3 बजे। "
        "बॉस ने बोला performance review next week है।"
    ),
    "8": (
        "Audiobook Chapter Opening",
        "Chapter ek. Naya safar. Jab main pehli baar Mumbai aaya, "
        "meri jeb mein sirf do sau rupaye the. Ek purana bag, kuch sapne, "
        "aur zindagi ka koi plan nahi."
    ),
    "9": (
        "Train Announcement",
        "Kripya dhyan dijiye. Gaadi sankhya 12301 Howrah Rajdhani Express "
        "platform sankhya chaar par aa rahi hai. "
        "Yaatriyon se nivedan hai ki peeli lakeer ke peechhe khade rahein."
    ),
    "10": (
        "Shayari / Poetry",
        "Hazaaron khwahishein aisi, ki har khwahish pe dam nikle. "
        "Bohot nikle mere armaan, lekin phir bhi kam nikle."
    ),
    "11": (
        "News Reading",
        "Aaj ki taaza khabar. Pradhan Mantri ne aaj ek naye scheme ka "
        "udghatan kiya. Is scheme ke tahat gareebi rekha ke neeche ke logon ko "
        "muft ration aur health insurance milega."
    ),
    "12": (
        "Quick Test (Short)",
        "Hello! Yeh ek chhota sa test hai. Suno aur batao kaisa laga."
    ),
}

# ── Named Prosody Presets ────────────────────────────────────────────────────
PRESETS = {
    "normal":    {"rate": "+0%",   "volume": "+0%",   "pitch": "+0Hz",   "desc": "Default / Natural"},
    "excited":   {"rate": "+35%",  "volume": "+20%",  "pitch": "+50Hz",  "desc": "Happy / Excited"},
    "sad":       {"rate": "-35%",  "volume": "-20%",  "pitch": "-50Hz",  "desc": "Sad / Somber"},
    "angry":     {"rate": "+25%",  "volume": "+30%",  "pitch": "+35Hz",  "desc": "Angry / Aggressive"},
    "whisper":   {"rate": "-25%",  "volume": "-40%",  "pitch": "-35Hz",  "desc": "Whisper / Secret"},
    "robotic":   {"rate": "-45%",  "volume": "+15%",  "pitch": "-90Hz",  "desc": "Robotic / Monotone"},
    "slow":      {"rate": "-40%",  "volume": "+0%",   "pitch": "+0Hz",   "desc": "Slow reading"},
    "fast":      {"rate": "+55%",  "volume": "+0%",   "pitch": "+0Hz",   "desc": "Fast reading"},
    "deep":      {"rate": "+0%",   "volume": "+0%",   "pitch": "-150Hz", "desc": "Deep / Bass voice"},
    "high":      {"rate": "+0%",   "volume": "+0%",   "pitch": "+150Hz", "desc": "High / Squeaky voice"},
    "calm_nar":  {"rate": "-15%",  "volume": "-5%",   "pitch": "-10Hz",  "desc": "Calm narrator"},
    "drama":     {"rate": "+15%",  "volume": "+10%",  "pitch": "+20Hz",  "desc": "Dramatic emphasis"},
    "loud":      {"rate": "+10%",  "volume": "+40%",  "pitch": "+25Hz",  "desc": "Loud / Shouting"},
    # ── New experimental presets to try ──
    "news":      {"rate": "+5%",   "volume": "+10%",  "pitch": "+5Hz",   "desc": "Newsreader style"},
    "bedtime":   {"rate": "-30%",  "volume": "-25%",  "pitch": "-20Hz",  "desc": "Bedtime story / soothing"},
    "villain":   {"rate": "-20%",  "volume": "+5%",   "pitch": "-80Hz",  "desc": "Villain / menacing"},
    "cheerful":  {"rate": "+20%",  "volume": "+15%",  "pitch": "+30Hz",  "desc": "Cheerful / upbeat"},
    "teacher":   {"rate": "-10%",  "volume": "+10%",  "pitch": "+0Hz",   "desc": "Teacher / instructional"},
    "dramatic_pause": {"rate": "-25%", "volume": "+5%", "pitch": "+10Hz", "desc": "Dramatic with pauses"},
    "child":     {"rate": "+15%",  "volume": "+0%",   "pitch": "+120Hz", "desc": "Child-like voice"},
    "elder":     {"rate": "-20%",  "volume": "-5%",   "pitch": "-60Hz",  "desc": "Elderly / wise"},
    "sports":    {"rate": "+40%",  "volume": "+35%",  "pitch": "+40Hz",  "desc": "Sports commentary"},
    "meditation":{"rate": "-35%",  "volume": "-30%",  "pitch": "-15Hz",  "desc": "Meditation / zen"},
    "radio_dj":  {"rate": "+10%",  "volume": "+20%",  "pitch": "-30Hz",  "desc": "Radio DJ / cool"},
}

# ── Sweep Ranges (for matrix mode) ──────────────────────────────────────────
RATE_SWEEP   = ["-50%", "-30%", "-15%", "+0%", "+15%", "+30%", "+50%", "+80%"]
VOLUME_SWEEP = ["-40%", "-20%", "+0%",  "+20%", "+40%"]
PITCH_SWEEP  = ["-150Hz", "-80Hz", "-40Hz", "+0Hz", "+40Hz", "+80Hz", "+150Hz"]

# Lighter sweep for quick testing
RATE_QUICK   = ["-30%", "+0%", "+30%"]
VOLUME_QUICK = ["-20%", "+0%", "+20%"]
PITCH_QUICK  = ["-50Hz", "+0Hz", "+50Hz"]


# ═══════════════════════════════════════════════════════════════════════════════
#                              CORE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_player_cmd():
    """Detect available audio player."""
    for player in ["mpv", "ffplay", "aplay", "paplay", "vlc"]:
        try:
            subprocess.run(["which", player], capture_output=True, check=True)
            return player
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None


PLAYER = None  # Will be set at startup


def play_audio(filepath):
    """Play an audio file using the system player."""
    global PLAYER
    if PLAYER is None:
        PLAYER = get_player_cmd()

    if PLAYER is None:
        print("  ⚠  No audio player found (tried mpv, ffplay, aplay, paplay, vlc)")
        print(f"  📁 File saved at: {filepath}")
        return

    try:
        if PLAYER == "mpv":
            subprocess.run(["mpv", "--no-video", "--really-quiet", filepath],
                           capture_output=True)
        elif PLAYER == "ffplay":
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", filepath],
                           capture_output=True)
        elif PLAYER == "vlc":
            subprocess.run(["vlc", "--play-and-exit", "--intf", "dummy", filepath],
                           capture_output=True)
        else:
            subprocess.run([PLAYER, filepath], capture_output=True)
    except Exception as e:
        print(f"  ⚠  Playback error: {e}")
        print(f"  📁 File saved at: {filepath}")


async def generate_audio(text, voice, rate, volume, pitch, filename=None):
    """Generate a single TTS audio clip. Returns filepath."""
    ensure_output_dir()
    if filename is None:
        ts = datetime.now().strftime("%H%M%S")
        safe_voice = voice.split("-")[-1][:8]
        filename = f"{safe_voice}_{rate}_{volume}_{pitch}_{ts}.mp3".replace("+", "p").replace("-", "m").replace("%", "pct").replace("Hz", "hz")
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(filepath)
        return filepath
    except Exception as e:
        print(f"  ✗  Error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#                          DISPLAY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def print_header(title):
    width = 70
    print()
    print(f"  ╔{'═' * (width - 4)}╗")
    print(f"  ║{title:^{width - 4}}║")
    print(f"  ╚{'═' * (width - 4)}╝")
    print()


def print_divider(label=""):
    if label:
        print(f"\n  ── {label} {'─' * (50 - len(label))}\n")
    else:
        print(f"  {'─' * 60}")


def format_prosody(rate, volume, pitch):
    return f"Speed={rate:6s}  Vol={volume:6s}  Pitch={pitch:7s}"


def print_current_settings(voice, voice_desc, rate, volume, pitch, text_name):
    print(f"  🎤 Voice : {voice_desc}")
    print(f"           ({voice})")
    print(f"  ⚡ Speed : {rate}")
    print(f"  🔊 Volume: {volume}")
    print(f"  🎵 Pitch : {pitch}")
    print(f"  📝 Text  : {text_name}")


# ═══════════════════════════════════════════════════════════════════════════════
#                       FAVORITES MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r") as f:
            return json.load(f)
    return []


def save_favorite(voice, rate, volume, pitch, note=""):
    favs = load_favorites()
    favs.append({
        "voice": voice,
        "rate": rate,
        "volume": volume,
        "pitch": pitch,
        "note": note,
        "timestamp": datetime.now().isoformat(),
    })
    with open(FAVORITES_FILE, "w") as f:
        json.dump(favs, f, indent=2)
    print(f"  ⭐ Saved! ({len(favs)} total favorites)")


def show_favorites():
    favs = load_favorites()
    if not favs:
        print("  No favorites saved yet.")
        return
    print_divider("Your Favorites")
    for i, fav in enumerate(favs, 1):
        voice_short = fav["voice"].split("-")[-1][:12]
        note = f' — "{fav["note"]}"' if fav.get("note") else ""
        print(f"  {i:2d}. [{voice_short:12s}]  "
              f"Speed={fav['rate']:6s}  Vol={fav['volume']:6s}  Pitch={fav['pitch']:7s}{note}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#                     MODE 1: INTERACTIVE TUNING
# ═══════════════════════════════════════════════════════════════════════════════

async def interactive_mode(start_voice=None):
    """Main interactive prosody tuning loop."""

    # Defaults
    current_voice_key = "1"
    if start_voice:
        for k, (v, _) in VOICES.items():
            if v == start_voice:
                current_voice_key = k
                break

    current_voice, current_desc = VOICES[current_voice_key]
    rate, volume, pitch = "+0%", "+0%", "+0Hz"
    current_text_key = "1"
    current_text_name, current_text = SAMPLE_TEXTS[current_text_key]

    while True:
        clear_screen()
        print_header("🎛️  PROSODY LAB — Interactive Tuning")
        print_current_settings(current_voice, current_desc, rate, volume, pitch, current_text_name)
        print()
        print_divider("Controls")
        print("  [g] 🔊 Generate & Play      [v] 🎤 Change Voice")
        print("  [t] 📝 Change Text           [c] ✏️  Type Custom Text")
        print("  [s] ⚡ Set Speed (rate)       [o] 🔊 Set Volume")
        print("  [p] 🎵 Set Pitch             [a] 🔄 Set ALL (s/v/p)")
        print("  [r] 🎲 Randomize prosody     [l] 📋 Load Preset")
        print("  [f] ⭐ Save as Favorite       [F] 📂 View Favorites")
        print("  [m] 📊 Matrix Sweep mode      [b] ⚖️  A/B Compare mode")
        print("  [n] 🎤 Multi-Voice Compare    [P] 🎧 Preset Audition")
        print("  [x] 🔁 Reset to Normal        [q] ❌ Quit")
        print()

        choice = input("  ▶ Your choice: ").strip().lower()

        if choice == "q":
            print("\n  Bye! 👋\n")
            break

        elif choice == "g":
            print(f"\n  ⟳  Generating audio...")
            filepath = await generate_audio(current_text, current_voice, rate, volume, pitch)
            if filepath:
                size_kb = os.path.getsize(filepath) // 1024
                print(f"  ✓  Saved: {filepath} ({size_kb} KB)")
                print(f"  ▶  Playing...")
                play_audio(filepath)
            input("\n  Press Enter to continue...")

        elif choice == "v":
            print_divider("Available Voices")
            for k in sorted(VOICES.keys(), key=int):
                v, desc = VOICES[k]
                marker = " ◀ current" if v == current_voice else ""
                print(f"  {k:3s}. {desc:40s} ({v}){marker}")
            print()
            pick = input("  ▶ Pick voice number (Enter to keep): ").strip()
            if pick in VOICES:
                current_voice, current_desc = VOICES[pick]
                current_voice_key = pick

        elif choice == "t":
            print_divider("Sample Texts")
            for k in sorted(SAMPLE_TEXTS.keys(), key=int):
                name, text = SAMPLE_TEXTS[k]
                marker = " ◀ current" if k == current_text_key else ""
                preview = text[:60] + "..." if len(text) > 60 else text
                print(f"  {k:3s}. [{name}]")
                print(f"       {preview}{marker}")
            print()
            pick = input("  ▶ Pick text number (Enter to keep): ").strip()
            if pick in SAMPLE_TEXTS:
                current_text_key = pick
                current_text_name, current_text = SAMPLE_TEXTS[pick]

        elif choice == "c":
            print("\n  Type your custom text (Enter to keep current):")
            custom = input("  ▶ ").strip()
            if custom:
                current_text = custom
                current_text_name = "Custom Text"

        elif choice == "s":
            print(f"\n  Current Speed: {rate}")
            print("  Format: +N% or -N%  (e.g. +30%, -20%, +0%)")
            print(f"  Common values: {', '.join(RATE_SWEEP)}")
            new = input("  ▶ New speed: ").strip()
            if new:
                rate = new

        elif choice == "o":
            print(f"\n  Current Volume: {volume}")
            print("  Format: +N% or -N%  (e.g. +20%, -40%, +0%)")
            print(f"  Common values: {', '.join(VOLUME_SWEEP)}")
            new = input("  ▶ New volume: ").strip()
            if new:
                volume = new

        elif choice == "p":
            print(f"\n  Current Pitch: {pitch}")
            print("  Format: +NHz or -NHz  (e.g. +50Hz, -80Hz, +0Hz)")
            print(f"  Common values: {', '.join(PITCH_SWEEP)}")
            new = input("  ▶ New pitch: ").strip()
            if new:
                pitch = new

        elif choice == "a":
            print("\n  Set all three values at once:")
            print(f"  Current: Speed={rate}  Volume={volume}  Pitch={pitch}")
            new_r = input(f"  ▶ Speed  [{rate}]: ").strip() or rate
            new_v = input(f"  ▶ Volume [{volume}]: ").strip() or volume
            new_p = input(f"  ▶ Pitch  [{pitch}]: ").strip() or pitch
            rate, volume, pitch = new_r, new_v, new_p

        elif choice == "r":
            import random
            rate = random.choice(RATE_SWEEP)
            volume = random.choice(VOLUME_SWEEP)
            pitch = random.choice(PITCH_SWEEP)
            print(f"\n  🎲 Random: Speed={rate}  Vol={volume}  Pitch={pitch}")
            input("  Press Enter to continue...")

        elif choice == "l":
            print_divider("Named Presets")
            preset_list = list(PRESETS.keys())
            for i, name in enumerate(preset_list, 1):
                p = PRESETS[name]
                marker = ""
                if p["rate"] == rate and p["volume"] == volume and p["pitch"] == pitch:
                    marker = " ◀ current"
                print(f"  {i:2d}. {name:18s} — {p['desc']}")
                print(f"       Speed={p['rate']:6s}  Vol={p['volume']:6s}  Pitch={p['pitch']:7s}{marker}")
            print()
            pick = input("  ▶ Pick preset number (Enter to keep): ").strip()
            try:
                idx = int(pick) - 1
                if 0 <= idx < len(preset_list):
                    p = PRESETS[preset_list[idx]]
                    rate, volume, pitch = p["rate"], p["volume"], p["pitch"]
                    print(f"  ✓  Loaded: {preset_list[idx]} — {p['desc']}")
                    input("  Press Enter to continue...")
            except (ValueError, IndexError):
                pass

        elif choice == "x":
            rate, volume, pitch = "+0%", "+0%", "+0Hz"
            print("  ✓  Reset to Normal")
            input("  Press Enter to continue...")

        elif choice == "f":
            note = input("  ▶ Add a note (optional): ").strip()
            save_favorite(current_voice, rate, volume, pitch, note)
            input("  Press Enter to continue...")

        elif choice.upper() == "F":
            show_favorites()
            input("  Press Enter to continue...")

        elif choice == "m":
            await matrix_sweep_mode(current_voice, current_desc, current_text, current_text_name)

        elif choice == "b":
            await ab_compare_mode(current_voice, current_text, rate, volume, pitch)

        elif choice == "n":
            await multi_voice_mode(current_text, rate, volume, pitch)

        elif choice.upper() == "P":
            await preset_audition_mode(current_voice, current_desc, current_text)

        else:
            print("  ⚠  Unknown option. Try again.")
            input("  Press Enter to continue...")


# ═══════════════════════════════════════════════════════════════════════════════
#                    MODE 2: MATRIX SWEEP
# ═══════════════════════════════════════════════════════════════════════════════

async def matrix_sweep_mode(voice, voice_desc, text, text_name):
    """Generate a grid of Speed × Volume × Pitch combinations."""
    clear_screen()
    print_header("📊 MATRIX SWEEP — Explore Combinations")
    print(f"  🎤 Voice: {voice_desc}")
    print(f"  📝 Text : {text_name}")
    print()

    print("  Choose sweep granularity:")
    print("  [1] Quick  (3×3×3 =  27 combos) — fast overview")
    print("  [2] Medium (pick 2 axes, sweep those, fix the 3rd)")
    print("  [3] Custom (you pick exact values for each axis)")
    print("  [4] Single axis (vary one param, fix others)")
    print("  [b] Back to main menu")
    print()

    choice = input("  ▶ Your choice: ").strip()

    if choice == "b":
        return

    if choice == "1":
        rates, volumes, pitches = RATE_QUICK, VOLUME_QUICK, PITCH_QUICK

    elif choice == "2":
        print("\n  Which two axes to sweep?")
        print("  [rv] Rate × Volume    (fix pitch)")
        print("  [rp] Rate × Pitch     (fix volume)")
        print("  [vp] Volume × Pitch   (fix rate)")
        axes = input("  ▶ Axes: ").strip().lower()
        if axes == "rv":
            fixed_pitch = input(f"  ▶ Fixed Pitch [+0Hz]: ").strip() or "+0Hz"
            rates, volumes, pitches = RATE_QUICK, VOLUME_QUICK, [fixed_pitch]
        elif axes == "rp":
            fixed_vol = input(f"  ▶ Fixed Volume [+0%]: ").strip() or "+0%"
            rates, volumes, pitches = RATE_QUICK, [fixed_vol], PITCH_QUICK
        elif axes == "vp":
            fixed_rate = input(f"  ▶ Fixed Rate [+0%]: ").strip() or "+0%"
            rates, volumes, pitches = [fixed_rate], VOLUME_QUICK, PITCH_QUICK
        else:
            print("  ⚠  Invalid choice")
            input("  Press Enter to continue...")
            return

    elif choice == "3":
        print("\n  Enter comma-separated values for each axis:")
        r_input = input(f"  ▶ Rates   (e.g. -30%,+0%,+30%): ").strip()
        v_input = input(f"  ▶ Volumes (e.g. -20%,+0%,+20%): ").strip()
        p_input = input(f"  ▶ Pitches (e.g. -50Hz,+0Hz,+50Hz): ").strip()
        rates = [x.strip() for x in r_input.split(",")]   if r_input else RATE_QUICK
        volumes = [x.strip() for x in v_input.split(",")] if v_input else VOLUME_QUICK
        pitches = [x.strip() for x in p_input.split(",")] if p_input else PITCH_QUICK

    elif choice == "4":
        print("\n  Which axis to sweep?")
        print("  [s] Speed   [v] Volume   [p] Pitch")
        axis = input("  ▶ Axis: ").strip().lower()
        if axis == "s":
            fixed_vol = input(f"  ▶ Fixed Volume [+0%]: ").strip() or "+0%"
            fixed_pitch = input(f"  ▶ Fixed Pitch [+0Hz]: ").strip() or "+0Hz"
            rates, volumes, pitches = RATE_SWEEP, [fixed_vol], [fixed_pitch]
        elif axis == "v":
            fixed_rate = input(f"  ▶ Fixed Rate [+0%]: ").strip() or "+0%"
            fixed_pitch = input(f"  ▶ Fixed Pitch [+0Hz]: ").strip() or "+0Hz"
            rates, volumes, pitches = [fixed_rate], VOLUME_SWEEP, [fixed_pitch]
        elif axis == "p":
            fixed_rate = input(f"  ▶ Fixed Rate [+0%]: ").strip() or "+0%"
            fixed_vol = input(f"  ▶ Fixed Volume [+0%]: ").strip() or "+0%"
            rates, volumes, pitches = [fixed_rate], [fixed_vol], PITCH_SWEEP
        else:
            print("  ⚠  Invalid axis")
            input("  Press Enter to continue...")
            return

    else:
        return

    combos = list(product(rates, volumes, pitches))
    total = len(combos)
    print(f"\n  📊 Generating {total} combinations...")
    print(f"     Rates:   {rates}")
    print(f"     Volumes: {volumes}")
    print(f"     Pitches: {pitches}")
    print()

    confirm = input(f"  ▶ Proceed? (y/n) [y]: ").strip().lower()
    if confirm == "n":
        return

    generated = []
    for i, (r, v, p) in enumerate(combos, 1):
        label = f"r={r:6s} v={v:6s} p={p:7s}"
        print(f"  ⟳  {i:3d}/{total}  {label}", end="", flush=True)
        filename = f"sweep_{i:03d}_r{r}_v{v}_p{p}.mp3".replace("+", "p").replace("-", "m").replace("%", "").replace("Hz", "hz")
        filepath = await generate_audio(text, voice, r, v, p, filename)
        if filepath:
            size_kb = os.path.getsize(filepath) // 1024
            print(f"  ✓ ({size_kb}KB)")
            generated.append((r, v, p, filepath))
        else:
            print(f"  ✗ FAILED")

    print(f"\n  ✅ Generated {len(generated)}/{total} files in {OUTPUT_DIR}/")
    print()

    # Interactive playback
    print_divider("Playback")
    print("  Type the number to play, 'all' to play all, 's' to save favorites, or 'b' to go back.")
    print()
    for i, (r, v, p, fp) in enumerate(generated, 1):
        print(f"  {i:3d}. Speed={r:6s}  Vol={v:6s}  Pitch={p:7s}")

    while True:
        cmd = input("\n  ▶ Play #: ").strip().lower()
        if cmd == "b":
            break
        elif cmd == "all":
            for i, (r, v, p, fp) in enumerate(generated, 1):
                print(f"  ▶ Playing {i}/{len(generated)}: Speed={r} Vol={v} Pitch={p}")
                play_audio(fp)
                proceed = input("  [Enter=next, s=save fav, q=stop] ").strip().lower()
                if proceed == "s":
                    save_favorite(voice, r, v, p, f"sweep pick #{i}")
                elif proceed == "q":
                    break
        elif cmd == "s":
            num = input("  ▶ Which # to save as favorite? ").strip()
            try:
                idx = int(num) - 1
                if 0 <= idx < len(generated):
                    r, v, p, _ = generated[idx]
                    note = input("  ▶ Note: ").strip()
                    save_favorite(voice, r, v, p, note)
            except ValueError:
                pass
        else:
            try:
                idx = int(cmd) - 1
                if 0 <= idx < len(generated):
                    r, v, p, fp = generated[idx]
                    print(f"  ▶ Playing: Speed={r} Vol={v} Pitch={p}")
                    play_audio(fp)
                else:
                    print("  ⚠  Invalid number")
            except ValueError:
                print("  ⚠  Enter a number, 'all', 's', or 'b'")


# ═══════════════════════════════════════════════════════════════════════════════
#                    MODE 3: A/B COMPARE
# ═══════════════════════════════════════════════════════════════════════════════

async def ab_compare_mode(voice, text, rate, volume, pitch):
    """Compare two prosody settings side-by-side on the same text."""
    clear_screen()
    print_header("⚖️  A/B COMPARE — Side-by-Side Listening")
    print(f"  Compare two prosody settings on the same text & voice.\n")

    # Setting A (current)
    print(f"  Setting A (current): Speed={rate}  Vol={volume}  Pitch={pitch}")
    use_current = input("  ▶ Use current as A? (y/n) [y]: ").strip().lower()

    if use_current == "n":
        print("  Enter Setting A:")
        a_rate = input(f"  ▶ Speed  [+0%]: ").strip() or "+0%"
        a_vol  = input(f"  ▶ Volume [+0%]: ").strip() or "+0%"
        a_pit  = input(f"  ▶ Pitch  [+0Hz]: ").strip() or "+0Hz"
    else:
        a_rate, a_vol, a_pit = rate, volume, pitch

    # Setting B
    print("\n  Enter Setting B:")
    print("  (Or type a preset name like 'excited', 'whisper', 'calm_nar', etc.)")
    b_input = input("  ▶ Preset name or 'manual': ").strip().lower()

    if b_input in PRESETS:
        p = PRESETS[b_input]
        b_rate, b_vol, b_pit = p["rate"], p["volume"], p["pitch"]
        print(f"  ✓  Loaded: {b_input} — Speed={b_rate} Vol={b_vol} Pitch={b_pit}")
    else:
        b_rate = input(f"  ▶ Speed  [+0%]: ").strip() or "+0%"
        b_vol  = input(f"  ▶ Volume [+0%]: ").strip() or "+0%"
        b_pit  = input(f"  ▶ Pitch  [+0Hz]: ").strip() or "+0Hz"

    print(f"\n  📊 Comparison:")
    print(f"       A: Speed={a_rate:6s}  Vol={a_vol:6s}  Pitch={a_pit:7s}")
    print(f"       B: Speed={b_rate:6s}  Vol={b_vol:6s}  Pitch={b_pit:7s}")

    print(f"\n  ⟳  Generating A...")
    file_a = await generate_audio(text, voice, a_rate, a_vol, a_pit, "compare_A.mp3")
    print(f"  ⟳  Generating B...")
    file_b = await generate_audio(text, voice, b_rate, b_vol, b_pit, "compare_B.mp3")

    if not file_a or not file_b:
        print("  ✗  Generation failed!")
        input("  Press Enter to continue...")
        return

    while True:
        print(f"\n  [a] Play A   [b] Play B   [ab] Play A then B   [ba] Play B then A")
        print(f"  [sa] Save A as fav   [sb] Save B as fav   [q] Back")
        choice = input("  ▶ ").strip().lower()

        if choice == "q":
            break
        elif choice == "a":
            print(f"  ▶ Playing A: Speed={a_rate} Vol={a_vol} Pitch={a_pit}")
            play_audio(file_a)
        elif choice == "b":
            print(f"  ▶ Playing B: Speed={b_rate} Vol={b_vol} Pitch={b_pit}")
            play_audio(file_b)
        elif choice == "ab":
            print(f"  ▶ Playing A then B...")
            print(f"    A: Speed={a_rate} Vol={a_vol} Pitch={a_pit}")
            play_audio(file_a)
            print(f"    B: Speed={b_rate} Vol={b_vol} Pitch={b_pit}")
            play_audio(file_b)
        elif choice == "ba":
            print(f"  ▶ Playing B then A...")
            print(f"    B: Speed={b_rate} Vol={b_vol} Pitch={b_pit}")
            play_audio(file_b)
            print(f"    A: Speed={a_rate} Vol={a_vol} Pitch={a_pit}")
            play_audio(file_a)
        elif choice == "sa":
            note = input("  ▶ Note: ").strip()
            save_favorite(voice, a_rate, a_vol, a_pit, note)
        elif choice == "sb":
            note = input("  ▶ Note: ").strip()
            save_favorite(voice, b_rate, b_vol, b_pit, note)


# ═══════════════════════════════════════════════════════════════════════════════
#                  MODE 4: MULTI-VOICE COMPARE
# ═══════════════════════════════════════════════════════════════════════════════

async def multi_voice_mode(text, rate, volume, pitch):
    """Test same prosody across multiple voices."""
    clear_screen()
    print_header("🎤 MULTI-VOICE — Same Prosody, Different Voices")
    print(f"  Prosody: Speed={rate}  Vol={volume}  Pitch={pitch}\n")

    print_divider("Select Voices to Compare")
    for k in sorted(VOICES.keys(), key=int):
        v, desc = VOICES[k]
        print(f"  {k:3s}. {desc:40s} ({v})")

    print()
    picks = input("  ▶ Enter voice numbers (comma-separated, e.g. 1,2,3): ").strip()
    if not picks:
        return

    selected = [k.strip() for k in picks.split(",") if k.strip() in VOICES]
    if not selected:
        print("  ⚠  No valid voices selected.")
        input("  Press Enter to continue...")
        return

    generated = []
    for k in selected:
        voice, desc = VOICES[k]
        print(f"  ⟳  Generating: {desc}...", end="", flush=True)
        filename = f"multi_{k}_{voice.split('-')[-1][:8]}.mp3"
        filepath = await generate_audio(text, voice, rate, volume, pitch, filename)
        if filepath:
            size_kb = os.path.getsize(filepath) // 1024
            print(f"  ✓ ({size_kb}KB)")
            generated.append((k, voice, desc, filepath))
        else:
            print(f"  ✗ FAILED")

    print(f"\n  ✅ Generated {len(generated)} voice samples.")
    print()

    while True:
        for i, (k, voice, desc, fp) in enumerate(generated, 1):
            print(f"  {i}. {desc} ({voice})")
        print()
        print("  [#] Play specific   [all] Play all   [b] Back")
        cmd = input("  ▶ ").strip().lower()

        if cmd == "b":
            break
        elif cmd == "all":
            for i, (k, voice, desc, fp) in enumerate(generated, 1):
                print(f"  ▶ Playing {i}/{len(generated)}: {desc}")
                play_audio(fp)
                proceed = input("  [Enter=next, s=save fav, q=stop] ").strip().lower()
                if proceed == "s":
                    save_favorite(voice, rate, volume, pitch, f"multi-voice test: {desc}")
                elif proceed == "q":
                    break
        else:
            try:
                idx = int(cmd) - 1
                if 0 <= idx < len(generated):
                    k, voice, desc, fp = generated[idx]
                    print(f"  ▶ Playing: {desc}")
                    play_audio(fp)
            except ValueError:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
#                  MODE 5: PRESET AUDITION
# ═══════════════════════════════════════════════════════════════════════════════

async def preset_audition_mode(voice, voice_desc, text):
    """Generate & play all named presets one by one so you can audition them."""
    clear_screen()
    print_header("🎧 PRESET AUDITION — Listen to Every Preset")
    print(f"  🎤 Voice: {voice_desc}")
    print()

    preset_list = list(PRESETS.keys())
    print("  Available presets:")
    for i, name in enumerate(preset_list, 1):
        p = PRESETS[name]
        print(f"  {i:2d}. {name:18s} — {p['desc']}")
        print(f"       Speed={p['rate']:6s}  Vol={p['volume']:6s}  Pitch={p['pitch']:7s}")

    print()
    print("  [all] Generate & play all presets sequentially")
    print("  [#]   Generate & play specific preset only")
    print("  [b]   Back to main menu")
    print()
    choice = input("  ▶ ").strip().lower()

    if choice == "b":
        return

    if choice == "all":
        presets_to_play = list(range(len(preset_list)))
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(preset_list):
                presets_to_play = [idx]
            else:
                print("  ⚠  Invalid number")
                input("  Press Enter...")
                return
        except ValueError:
            return

    print(f"\n  ⟳  Generating {len(presets_to_play)} preset(s)...\n")

    generated = []
    for idx in presets_to_play:
        name = preset_list[idx]
        p = PRESETS[name]
        print(f"  ⟳  [{name:18s}] Speed={p['rate']:6s} Vol={p['volume']:6s} Pitch={p['pitch']:7s}", end="", flush=True)
        filename = f"preset_{name}.mp3"
        filepath = await generate_audio(text, voice, p["rate"], p["volume"], p["pitch"], filename)
        if filepath:
            size_kb = os.path.getsize(filepath) // 1024
            print(f"  ✓ ({size_kb}KB)")
            generated.append((name, p, filepath))
        else:
            print(f"  ✗ FAILED")

    print(f"\n  ✅ Generated {len(generated)} presets. Starting playback...\n")

    for i, (name, p, fp) in enumerate(generated, 1):
        print(f"  ▶ {i}/{len(generated)} — [{name}] {p['desc']}")
        print(f"    Speed={p['rate']:6s}  Vol={p['volume']:6s}  Pitch={p['pitch']:7s}")
        play_audio(fp)
        if i < len(generated):
            cmd = input("  [Enter=next, r=replay, s=save fav, q=stop] ").strip().lower()
            if cmd == "r":
                play_audio(fp)
                input("  Press Enter for next...")
            elif cmd == "s":
                note = input("  ▶ Note: ").strip()
                save_favorite(voice, p["rate"], p["volume"], p["pitch"], note or f"preset:{name}")
            elif cmd == "q":
                break
        else:
            input("  Press Enter to continue...")


# ═══════════════════════════════════════════════════════════════════════════════
#               MODE 6: CLI SWEEP (non-interactive)
# ═══════════════════════════════════════════════════════════════════════════════

async def cli_sweep(voice=None):
    """Non-interactive quick sweep — generates all combos to files."""
    if voice is None:
        voice = "hi-IN-SwaraNeural"

    text = SAMPLE_TEXTS["12"][1]  # Short test text
    combos = list(product(RATE_QUICK, VOLUME_QUICK, PITCH_QUICK))

    print_header("📊 CLI SWEEP — Quick Generation")
    print(f"  Voice:  {voice}")
    print(f"  Text:   {text}")
    print(f"  Combos: {len(combos)} (3×3×3)")
    print()

    for i, (r, v, p) in enumerate(combos, 1):
        label = f"Speed={r:6s}  Vol={v:6s}  Pitch={p:7s}"
        print(f"  ⟳  {i:3d}/{len(combos)}  {label}", end="", flush=True)
        filename = f"sweep_{i:03d}_r{r}_v{v}_p{p}.mp3".replace("+", "p").replace("-", "m").replace("%", "").replace("Hz", "hz")
        filepath = await generate_audio(text, voice, r, v, p, filename)
        if filepath:
            size_kb = os.path.getsize(filepath) // 1024
            print(f"  ✓ ({size_kb}KB)")
        else:
            print(f"  ✗ FAILED")

    print(f"\n  ✅ All files in {OUTPUT_DIR}/")
    print(f"  💡 Play them with: for f in {OUTPUT_DIR}/sweep_*.mp3; do echo $f; mpv $f; done\n")


# ═══════════════════════════════════════════════════════════════════════════════
#            MODE 7: CLI PRESET AUDITION (non-interactive)
# ═══════════════════════════════════════════════════════════════════════════════

async def cli_presets(voice=None):
    """Non-interactive — generates all presets to files."""
    if voice is None:
        voice = "hi-IN-SwaraNeural"

    text = SAMPLE_TEXTS["12"][1]

    print_header("🎧 CLI PRESETS — Generate All Presets")
    print(f"  Voice: {voice}")
    print()

    for name, p in PRESETS.items():
        label = f"[{name:18s}] Speed={p['rate']:6s} Vol={p['volume']:6s} Pitch={p['pitch']:7s} — {p['desc']}"
        print(f"  ⟳  {label}", end="", flush=True)
        filename = f"preset_{name}.mp3"
        filepath = await generate_audio(text, voice, p["rate"], p["volume"], p["pitch"], filename)
        if filepath:
            size_kb = os.path.getsize(filepath) // 1024
            print(f"  ✓ ({size_kb}KB)")
        else:
            print(f"  ✗ FAILED")

    print(f"\n  ✅ All presets in {OUTPUT_DIR}/")
    print(f"  💡 Play them with: for f in {OUTPUT_DIR}/preset_*.mp3; do echo $f; mpv $f; done\n")


# ═══════════════════════════════════════════════════════════════════════════════
#                              MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description="Prosody Lab — Interactive Edge-TTS Prosody Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python Prosody_Lab.py                     # Interactive menu
  python Prosody_Lab.py --sweep             # Quick 3×3×3 sweep (27 combos)
  python Prosody_Lab.py --presets           # Generate all named presets
  python Prosody_Lab.py --ab                # A/B comparison mode
  python Prosody_Lab.py --voice hi-IN-MadhurNeural --sweep
        """
    )
    parser.add_argument("--sweep", action="store_true", help="Run quick 3×3×3 matrix sweep")
    parser.add_argument("--presets", action="store_true", help="Generate all named presets")
    parser.add_argument("--ab", action="store_true", help="Start in A/B comparison mode")
    parser.add_argument("--voice", help="Starting voice (e.g. hi-IN-SwaraNeural)")
    args = parser.parse_args()

    # Detect audio player
    global PLAYER
    PLAYER = get_player_cmd()
    if PLAYER:
        print(f"  🔈 Audio player: {PLAYER}")
    else:
        print("  ⚠  No audio player found. Files will be saved but not auto-played.")
        print("     Install mpv or ffplay: sudo apt install mpv")

    if args.sweep:
        await cli_sweep(args.voice)
    elif args.presets:
        await cli_presets(args.voice)
    elif args.ab:
        voice = args.voice or "hi-IN-SwaraNeural"
        text = SAMPLE_TEXTS["1"][1]
        await ab_compare_mode(voice, text, "+0%", "+0%", "+0Hz")
    else:
        await interactive_mode(args.voice)


if __name__ == "__main__":
    asyncio.run(main())
