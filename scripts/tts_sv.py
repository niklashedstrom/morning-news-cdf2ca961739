#!/usr/bin/env python3
"""Swedish TTS for the morning news, using Microsoft's neural voices via edge-tts.

Usage:
  python3 scripts/tts_sv.py <script.txt> <out.mp3> [voice]

script.txt: one paragraph per line. Each paragraph is synthesized separately
(retried on transient errors), joined with a short pause, loudness-normalized
and encoded to mono MP3. Needs ffmpeg/ffprobe on PATH and `pip install edge-tts`.
"""
import asyncio
import os
import subprocess
import sys
import tempfile

import edge_tts

VOICE = "sv-SE-SofieNeural"
RATE = "+0%"
PAUSE_S = 0.6


async def synth(text, voice, path, tries=4):
    for i in range(tries):
        try:
            await edge_tts.Communicate(text, voice, rate=RATE).save(path)
            if os.path.getsize(path) > 0:
                return
        except Exception as e:  # network hiccups, throttling
            print(f"  retry {i + 1}: {e}", file=sys.stderr)
        await asyncio.sleep(2 * (i + 1))
    raise RuntimeError(f"TTS failed after {tries} tries: {text[:60]}...")


async def main(src, dst, voice):
    with open(src, encoding="utf-8") as f:
        paras = [p.strip() for p in f.read().split("\n") if p.strip()]
    if not paras:
        sys.exit("empty script")
    d = tempfile.mkdtemp()
    silence = os.path.join(d, "silence.mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", str(PAUSE_S), "-b:a", "48k", silence],
                   check=True)
    parts = []
    for n, p in enumerate(paras):
        path = os.path.join(d, f"p{n:03d}.mp3")
        print(f"[{n + 1}/{len(paras)}] {len(p)} chars")
        await synth(p, voice, path)
        parts += [path, silence]
    lst = os.path.join(d, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-af", "highpass=f=60,loudnorm=I=-16:TP=-1.5", "-ac", "1", "-ar", "24000",
                    "-b:a", "96k", dst], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", dst], capture_output=True, text=True).stdout)
    print(f"{dst}: {dur / 60:.1f} min")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else VOICE))
