import asyncio
import edge_tts
import os
import subprocess
import time
import sys

VOICE = "hi-IN-SwaraNeural"
OUTPUT_FILE = "final_output.mp3"
MAX_RETRIES = 3          # retry each chunk up to 3 times on network hiccup
CONCURRENCY  = 4         # parallel requests; lower to 2-3 if you get errors

# ── Split your long SSML into independent chunks ──────────────────────────────
# Each chunk is a COMPLETE valid SSML document.
# Tip: Split at natural section boundaries so pauses still make sense.

CHUNKS = [
    # Chunk 1 — Plain baseline + Dates
    """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">
      <voice name="hi-IN-SwaraNeural">
        Yeh ek simple sentence hai, bina kisi prosody ke.
        Iska matlab hai ki TTS engine apne default tone mein bolega.
        Yaar, ghar pe sab theek hai? Aaj khaana kya bana?
        Main office se thaka hua aaya hoon, aur neend aa rahi hai.
        <break time="600ms"/>
        Aaj ki date hai <say-as interpret-as="date" format="dmy">11-03-2026</say-as>.
        Independence day aata hai <say-as interpret-as="date" format="dm">15-08</say-as> ko.
        Mera birthday hai <say-as interpret-as="date" format="mdy">07/04/1995</say-as>.
      </voice>
    </speak>""",

    # Chunk 2 — Numbers, digits, currency, symbols
    """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">
      <voice name="hi-IN-SwaraNeural">
        Ab numbers aur symbols test karte hain.
        <break time="300ms"/>
        Yeh ek cardinal number hai: <say-as interpret-as="cardinal">4523</say-as>.
        Phone number: <say-as interpret-as="digits">9876543210</say-as>.
        OTP hai: <say-as interpret-as="digits">482951</say-as>.
        Rupees mein price: <say-as interpret-as="currency">₹1,49,999</say-as>.
        Dollar mein: <say-as interpret-as="currency">$4999.99</say-as>.
        Mere Instagram handle: @hinditech_yaar.
      </voice>
    </speak>""",

    # Chunk 3 — Abbreviations + Time
    """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">
      <voice name="hi-IN-SwaraNeural">
        Meri company ka naam hai <say-as interpret-as="characters">IBM</say-as>.
        WiFi password hai: <say-as interpret-as="characters">AB12XY</say-as>.
        Yeh <say-as interpret-as="characters">HTML</say-as> aur
        <say-as interpret-as="characters">CSS</say-as> web ke liye hote hain.
        <break time="400ms"/>
        Meeting hai <say-as interpret-as="time" format="hms12">3:30pm</say-as> pe.
        Train <say-as interpret-as="time" format="hms24">22:45:00</say-as> pe chhootegi.
      </voice>
    </speak>""",

    # Chunk 4 — Excited + Sad emotions
    """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">
      <voice name="hi-IN-SwaraNeural">
        <prosody rate="fast" pitch="x-high" volume="loud">
          Bhai bhai bhai! Sun tune yeh suna?!
          Lottery lag gayi humari! Ek crore rupaye!
          Chal celebrate karte hain, abhi ke abhi!
        </prosody>
        <break time="700ms"/>
        <prosody rate="x-slow" pitch="x-low" volume="soft">
          Yaar... woh chale gaye.
          <break time="700ms"/>
          Kuch samajh nahi aa raha mujhe.
          Kaash... woh abhi bhi yahaan hote.
        </prosody>
      </voice>
    </speak>""",

    # Chunk 5 — Anger + Fear + Sarcasm
    """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">
      <voice name="hi-IN-SwaraNeural">
        <prosody rate="fast" pitch="high" volume="x-loud">
          Maine tumhe <emphasis level="strong">kitni</emphasis> baar bola tha!
          Yeh bilkul <emphasis level="strong">acceptable</emphasis> nahi hai!
        </prosody>
        <break time="600ms"/>
        <prosody rate="fast" pitch="high" volume="soft">
          Main nahi jaana chahta wahan.
          Woh awaaz... kahan se aa rahi hai?
          <emphasis level="strong">Koi hai wahan.</emphasis>
        </prosody>
        <break time="600ms"/>
        <prosody rate="slow" pitch="low" volume="medium">
          Haan bilkul. Bahut <emphasis level="moderate">shandar</emphasis> kaam kiya tumne.
          Sirf teen ghante late, deadline miss, file galat folder mein.
          Truly. <emphasis level="strong">Outstanding.</emphasis>
        </prosody>
      </voice>
    </speak>""",

    # Chunk 6 — Whisper + Announcement + Storytelling
    """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">
      <voice name="hi-IN-SwaraNeural">
        <prosody volume="x-soft" rate="slow" pitch="low">
          Shhh. Yahan koi nahi hai na?
          Kal bade sahab resign kar rahe hain. Bilkul kisi ko nahi batana.
        </prosody>
        <break time="600ms"/>
        <prosody rate="slow" pitch="x-low" volume="loud">
          Attention please.
          <break time="400ms"/>
          Train number <say-as interpret-as="digits">12301</say-as>
          is arriving on platform number <say-as interpret-as="cardinal">4</say-as>.
          Passengers please stand behind the yellow line.
        </prosody>
        <break time="600ms"/>
        <prosody rate="slow" pitch="low">Ek baar ki baat hai.</prosody>
        <break time="300ms"/>
        <prosody rate="fast" pitch="high">Ek din achanak... ek awaaz aayi!</prosody>
        <break time="400ms"/>
        <prosody rate="x-slow" pitch="x-low" volume="soft">"Budhiya... tera waqt aa gaya hai."</prosody>
        <break time="400ms"/>
        <prosody rate="slow" pitch="medium">Woh sirf ek bachcha tha. Apna khoya hua pota.</prosody>
      </voice>
    </speak>""",

    # Chunk 7 — Rate extremes
    """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">
      <voice name="hi-IN-SwaraNeural">
        <prosody rate="x-slow">Yeh bahut dheere bol rahi hoon. Har shabd sunaai de raha hai?</prosody>
        <break time="300ms"/>
        <prosody rate="slow">Ab thoda tez, lekin phir bhi dheera.</prosody>
        <break time="300ms"/>
        <prosody rate="medium">Yeh normal speed hai, jaise hum baat karte hain.</prosody>
        <break time="300ms"/>
        <prosody rate="fast">Ab tez bol rahi hoon, jaise rush mein ho koi.</prosody>
        <break time="300ms"/>
        <prosody rate="x-fast">Yeh sabse tez hai, bilkul auctioneer ki tarah, sun sakte ho kya mujhe?</prosody>
      </voice>
    </speak>""",

    # Chunk 8 — Pitch + Volume extremes + Final stress test
    """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="hi-IN">
      <voice name="hi-IN-SwaraNeural">
        <prosody pitch="x-low">Yeh sabse neechi awaaz hai. Bilkul deep.</prosody>
        <break time="200ms"/>
        <prosody pitch="medium">Yeh normal pitch hai.</prosody>
        <break time="200ms"/>
        <prosody pitch="x-high">Yeh sabse oonchi pitch hai! Bilkul cartoon jaisi!</prosody>
        <break time="400ms"/>
        <prosody volume="x-soft">Yeh bahut dheeme bol rahi hoon.</prosody>
        <break time="200ms"/>
        <prosody volume="x-loud">YEH SABSE LOUD HAI! SUNAAYI DE RAHA HAI NA?!</prosody>
        <break time="600ms"/>
        <prosody rate="slow" pitch="medium" volume="soft">
          Yeh tha humara <say-as interpret-as="characters">TTS</say-as> test.
          Ummeed hai ki aapko yeh
          <lang xml:lang="en-US">audio</lang> pasand aayi.
          <break time="300ms"/>
          Dhanyavad!
        </prosody>
      </voice>
    </speak>""",
]


async def generate_chunk(index: int, ssml: str, semaphore: asyncio.Semaphore):
    """Generate one audio chunk with concurrency control and auto-retry."""
    filename = f"chunk_{index:02d}.mp3"
    async with semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"  ⟳  Chunk {index+1:02d}/{len(CHUNKS)} starting..."
                      + (f" (retry {attempt})" if attempt > 1 else ""))
                start = time.time()

                # ✅ THE FIX: ssml=True tells edge-tts to parse XML tags
                #    Without this, it reads "<break time=" literally as text!
                communicate = edge_tts.Communicate(ssml, VOICE, ssml=True)
                await communicate.save(filename)

                elapsed = time.time() - start
                print(f"  ✓  Chunk {index+1:02d}/{len(CHUNKS)} done in {elapsed:.1f}s → {filename}")
                return filename

            except Exception as e:
                print(f"  ✗  Chunk {index+1:02d} attempt {attempt} failed: {e}")
                if attempt == MAX_RETRIES:
                    print(f"  ✗  Chunk {index+1:02d} GIVING UP after {MAX_RETRIES} attempts!")
                    raise
                await asyncio.sleep(2 * attempt)   # back-off: 2s, 4s

    return filename


async def main():
    print(f"\n🚀  Generating {len(CHUNKS)} chunks in parallel (max {CONCURRENCY} at a time)...\n")
    total_start = time.time()

    semaphore = asyncio.Semaphore(CONCURRENCY)

    tasks = [
        generate_chunk(i, ssml, semaphore)
        for i, ssml in enumerate(CHUNKS)
    ]

    try:
        chunk_files = await asyncio.gather(*tasks)
    except Exception as e:
        print(f"\n💥  Fatal error during generation: {e}")
        sys.exit(1)

    print(f"\n🔗  Merging {len(chunk_files)} chunks with ffmpeg...")

    # Build ffmpeg concat list
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

    # Cleanup temp files
    for fname in chunk_files:
        if os.path.exists(fname):
            os.remove(fname)
    os.remove("concat_list.txt")

    total_time = time.time() - total_start
    size_kb = os.path.getsize(OUTPUT_FILE) // 1024
    print(f"\n✅  Done! → {OUTPUT_FILE}  ({size_kb} KB,  total time: {total_time:.1f}s)\n")


if __name__ == "__main__":
    asyncio.run(main())