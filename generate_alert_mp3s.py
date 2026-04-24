import re
from pathlib import Path

from gtts import gTTS


base = Path(".")
txt_path = base / "all_errorcode_quickfix_tools.txt"
alerts_dir = base / "alerts"
alerts_dir.mkdir(exist_ok=True)

lines = txt_path.read_text(encoding="utf-8").splitlines()

entries = []
current_code = None
current_fix = None
tools = []

for line in lines:
    if line.startswith("Error Code:"):
        if current_code:
            entries.append((current_code, current_fix or "", tools))
        current_code = line.split(":", 1)[1].strip()
        current_fix = ""
        tools = []
    elif line.startswith("Quick Fix:"):
        current_fix = line.split(":", 1)[1].strip()
    elif line.startswith("- ") and " | Location:" in line:
        tool = line[2:].split(" | Location:", 1)[0].strip()
        loc = line.split(" | Location:", 1)[1].strip()
        tools.append((tool, loc))

if current_code:
    entries.append((current_code, current_fix or "", tools))


def clean_filename(code: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", code)


for code, quick_fix, common_tools in entries:
    tool_text = "; ".join([f"{t} at {l}" for t, l in common_tools])
    speech = (
        f"Alert for error code {code}. "
        f"Quick fix steps: {quick_fix}. "
        f"Common tools and locations: {tool_text}."
    )
    out_file = alerts_dir / f"{clean_filename(code)}.mp3"
    tts = gTTS(text=speech, lang="en", tld="co.in")
    tts.save(str(out_file))
    print(f"Generated: {out_file}")

print(f"Total mp3 files: {len(entries)}")
