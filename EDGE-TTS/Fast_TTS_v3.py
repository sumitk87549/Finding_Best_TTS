"""
Fast_TTS_v3.py — edge-tts parallel TTS generator
==================================================
KEY FACTS (confirmed from edge-tts source & PyPI docs):
  - Custom SSML was REMOVED in v5.0.0 — Microsoft blocks it server-side
  - <break>, <say-as>, <emphasis>, <lang> etc. DO NOT WORK
  - Only rate, volume, pitch are controllable — passed as constructor args
  - Each chunk gets ONE global prosody setting (rate + volume + pitch)
  - For "emotion" variety: split text into chunks with different prosody args
  - Parallel generation via asyncio still works perfectly
"""

import asyncio
import edge_tts
import os
import subprocess
import time
import sys

OUTPUT_FILE = "final_output.mp3"
MAX_RETRIES = 3
CONCURRENCY = 4   # lower to 2 if you get throttle errors

# ── CHUNK FORMAT ──────────────────────────────────────────────────────────────
# Each entry: (text, voice, rate, volume, pitch)
# rate   : "+0%"  range roughly -50% to +100%
# volume : "+0%"  range roughly -50% to +50%
# pitch  : "+0Hz" range roughly -200Hz to +200Hz
#
# Emotion cheat sheet:
#   Excited  → rate="+35%", pitch="+50Hz", volume="+20%"
#   Sad      → rate="-35%", pitch="-50Hz", volume="-20%"
#   Angry    → rate="+25%", pitch="+35Hz", volume="+30%"
#   Whisper  → rate="-25%", pitch="-35Hz", volume="-40%"
#   Robotic  → rate="-45%", pitch="-90Hz", volume="+15%"
#   Normal   → rate="+0%",  pitch="+0Hz",  volume="+0%"
# ─────────────────────────────────────────────────────────────────────────────

VOICE_F = "hi-IN-SwaraNeural"    # female
VOICE_M = "hi-IN-MadhurNeural"   # male

CHUNKS = [
    # ── Section 1: Plain baseline (normal settings) ───────────────────────
    (
        "Yeh ek simple sentence hai, bina kisi prosody ke. "
        "Iska matlab hai ki TTS engine apne default tone mein bolega. "
        "Yaar, ghar pe sab theek hai? Aaj khaana kya bana? "
        "Main office se thaka hua aaya hoon, aur neend aa rahi hai.",
        VOICE_F, "+0%", "+0%", "+0Hz"
    ),

    # ── Section 2: Numbers, dates, phone ─────────────────────────────────
    (
        "Aaj ki date hai gyaarah march do hazaar chhabbis. "
        "Independence day aata hai pandrah august ko. "
        "Phone number hai: nau aath saat chhe panch chaar teen do ek shunya. "
        "OTP hai: chaar aath do nau panch ek. "
        "Price hai ek lakh unachaas hazaar nau sau ninyaanave rupaye. "
        "Dollar mein price hai: chaar hazaar nau sau ninyaanave dollar.",
        VOICE_F, "+0%", "+0%", "+0Hz"
    ),

    # ── Section 3: Excited / Happy ────────────────────────────────────────
    (
        "Bhai bhai bhai! Sun tune yeh suna?! "
        "Lottery lag gayi humari! Ek crore rupaye! EK CRORE! "
        "Main toh danga kar dunga aaj! "
        "Chal celebrate karte hain, abhi ke abhi!",
        VOICE_F, "+35%", "+20%", "+50Hz"
    ),

    # ── Section 4: Sad / Grief ────────────────────────────────────────────
    (
        "Yaar... woh chale gaye. "
        "Kuch samajh nahi aa raha mujhe. "
        "Itna khali khali lag raha hai. "
        "Kaash... woh abhi bhi yahaan hote.",
        VOICE_F, "-35%", "-20%", "-50Hz"
    ),

    # ── Section 5: Angry / Frustrated ────────────────────────────────────
    (
        "Maine tumhe kitni baar bola tha! KITNI BAAR! "
        "Yeh kaam kal tak ho jaana chahiye tha! "
        "Aur ab tum mujhe bol rahe ho ki nahi hua?! "
        "Yeh bilkul acceptable nahi hai!",
        VOICE_F, "+25%", "+30%", "+35Hz"
    ),

    # ── Section 6: Fear / Nervousness ────────────────────────────────────
    (
        "Main... main nahi jaana chahta wahan. "
        "Kuch toh hai us ghar mein, main feel kar sakta hoon. "
        "Woh awaaz... kahan se aa rahi hai? "
        "Koi hai wahan.",
        VOICE_F, "+20%", "-10%", "+25Hz"
    ),

    # ── Section 7: Sarcasm / Dry flat ────────────────────────────────────
    (
        "Haan bilkul. Bahut shandar kaam kiya tumne. "
        "Sirf teen ghante late aaye, deadline miss ki, "
        "file galat folder mein save ki. "
        "Truly. Outstanding.",
        VOICE_F, "-20%", "+0%", "-20Hz"
    ),

    # ── Section 8: Whisper / Secret ───────────────────────────────────────
    (
        "Shhh. Yahan koi nahi hai na? "
        "Kal bade sahab resign kar rahe hain. "
        "Kisi ko mat batana. Bilkul kisi ko nahi.",
        VOICE_F, "-25%", "-40%", "-35Hz"
    ),

    # ── Section 9: Robotic / Announcement ────────────────────────────────
    (
        "Attention please. "
        "Train number ek do teen shunya ek "
        "Howrah Rajdhani Express "
        "is arriving on platform number chaar. "
        "Passengers are requested to stand behind the yellow line. "
        "Dhanyavad.",
        VOICE_F, "-45%", "+15%", "-90Hz"
    ),

    # ── Section 10: Storytelling — calm narrator ──────────────────────────
    (
        "Ek baar ki baat hai. "
        "Ek chhota sa gaon tha, pahadon ke peechhe. "
        "Wahan ek budhiya rehti thi. "
        "Roz subah woh uthti, nadiyan ke paas jaati. "
        "Woh sirf ek bachcha tha. Apna khoya hua pota.",
        VOICE_F, "-15%", "-5%", "-10Hz"
    ),

    # ── Section 11: Storytelling — sudden fright ──────────────────────────
    (
        "Ek din achanak... ek awaaz aayi! "
        "Budhiya tera waqt aa gaya hai. "
        "Woh bhaagi! Jitna tej ho sakta tha!",
        VOICE_F, "+40%", "+10%", "+45Hz"
    ),

    # ── Section 12: Rate extreme — very slow ─────────────────────────────
    (
        "Yeh bahut dheere bol rahi hoon. "
        "Har ek shabd sunaai de raha hai? "
        "Ab thoda tez, lekin phir bhi dheera.",
        VOICE_F, "-45%", "+0%", "+0Hz"
    ),

    # ── Section 13: Rate extreme — very fast ─────────────────────────────
    (
        "Ab tez bol rahi hoon jaise rush mein ho koi. "
        "Yeh sabse tez hai bilkul auctioneer ki tarah sun sakte ho kya mujhe "
        "ya main bahut tez bol rahi hoon?",
        VOICE_F, "+60%", "+0%", "+0Hz"
    ),

    # ── Section 14: Pitch extreme — very low ─────────────────────────────
    (
        "Yeh sabse neechi awaaz hai. Bilkul deep aur bhaari. "
        "Kya yeh ek villain ki awaaz lagti hai?",
        VOICE_F, "+0%", "+0%", "-180Hz"
    ),

    # ── Section 15: Pitch extreme — very high ────────────────────────────
    (
        "Yeh sabse oonchi pitch hai! "
        "Bilkul cartoon jaisi! "
        "Kya yeh funny lag rahi hai aapko?",
        VOICE_F, "+0%", "+0%", "+180Hz"
    ),

    # ── Section 16: Male voice — normal ──────────────────────────────────
    (
        "Yeh male voice hai. Hi-IN Madhur Neural. "
        "Kya fark hai female voice se? "
        "Dono mein se kaun zyada natural lagta hai Hinglish ke liye?",
        VOICE_M, "+0%", "+0%", "+0Hz"
    ),

    # ── Section 17: Male voice — excited ─────────────────────────────────
    (
        "Bhai yeh toh kamaal ho gaya! "
        "Seriously yaar, I cannot believe this! "
        "Aaj ka din toh ekdum mast raha!",
        VOICE_M, "+30%", "+20%", "+40Hz"
    ),

    # ── Section 18: Hinglish heavy mix ───────────────────────────────────
    (
        "Yaar mera laptop ekdum slow ho gaya hai. "
        "Aaj presentation ke liye slides banana hai. "
        "Meeting mein boss ne bola ki performance improvement plan follow karo. "
        "Toh ab main seriously sochna chahta hoon ki kya job switch karna chahiye.",
        VOICE_F, "+0%", "+0%", "+0Hz"
    ),

    # ── Section 19: Final stress test ────────────────────────────────────
    (
        "Yaar main tumhe ek baat batata hoon. "
        "Aaj date thi gyaarah march do hazaar chhabbis. "
        "Aur usne kya kiya? Bill aaya do sau bees dollar! "
        "Maine socha yeh galat tha. "
        "Toh main seedha gaya manager ke paas aur bola ki yeh unacceptable hai "
        "aur mujhe paisa wapas chahiye! "
        "Aur jaante ho kya hua? Unhone maan liya. "
        "Yeh tha humara TTS test. Dhanyavad!",
        VOICE_F, "+0%", "+0%", "+0Hz"
    ),
]


async def generate_chunk(index: int, chunk: tuple, semaphore: asyncio.Semaphore):
    """Generate one audio chunk with concurrency control and auto-retry."""
    text, voice, rate, volume, pitch = chunk
    filename = f"chunk_{index:02d}.mp3"

    async with semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                label = f"[r={rate} v={volume} p={pitch}]"
                print(f"  ⟳  Chunk {index+1:02d}/{len(CHUNKS)} {label}"
                      + (f" retry {attempt}" if attempt > 1 else ""))
                start = time.time()

                communicate = edge_tts.Communicate(
                    text,
                    voice,
                    rate=rate,
                    volume=volume,
                    pitch=pitch,
                )
                await communicate.save(filename)

                elapsed = time.time() - start
                size = os.path.getsize(filename) // 1024
                print(f"  ✓  Chunk {index+1:02d}/{len(CHUNKS)} "
                      f"done in {elapsed:.1f}s → {filename} ({size}KB)")
                return filename

            except Exception as e:
                print(f"  ✗  Chunk {index+1:02d} attempt {attempt} failed: {e}")
                if attempt == MAX_RETRIES:
                    print(f"  ✗  Chunk {index+1:02d} GIVING UP after {MAX_RETRIES} attempts!")
                    raise
                await asyncio.sleep(2 * attempt)

    return filename


async def main():
    print(f"\n🚀  Generating {len(CHUNKS)} chunks in parallel (max {CONCURRENCY} at a time)...")
    print(f"    Voices: {VOICE_F}  |  {VOICE_M}\n")
    total_start = time.time()

    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [generate_chunk(i, chunk, semaphore) for i, chunk in enumerate(CHUNKS)]

    try:
        chunk_files = await asyncio.gather(*tasks)
    except Exception as e:
        print(f"\n💥  Fatal error during generation: {e}")
        sys.exit(1)

    print(f"\n🔗  Merging {len(chunk_files)} chunks with ffmpeg...")

    with open("concat_list.txt", "w") as f:
        for fname in chunk_files:
            f.write(f"file '{fname}'\n")

    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "concat_list.txt",
        "-acodec", "copy",
        OUTPUT_FILE
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ✗  ffmpeg error:\n{result.stderr}")
        sys.exit(1)

    for fname in chunk_files:
        if os.path.exists(fname):
            os.remove(fname)
    os.remove("concat_list.txt")

    total_time = time.time() - total_start
    size_kb = os.path.getsize(OUTPUT_FILE) // 1024
    print(f"\n✅  Done! → {OUTPUT_FILE}  ({size_kb} KB,  total time: {total_time:.1f}s)\n")


if __name__ == "__main__":
    asyncio.run(main())
