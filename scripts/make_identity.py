"""Build the AZ terminal card. Uses only the Python standard library."""

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SVG_START = '''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="410" viewBox="0 0 1000 410" role="img" aria-labelledby="title desc">
<title id="title">Abdulaziz — Improve your tech with me.</title>
<desc id="desc">An AZ ASCII logo types itself beside a terminal card. Abdulaziz is based in Saudi Arabia and works with Python, SQL, data, dashboards and connected devices.</desc>
<defs>
  <linearGradient id="accent"><stop stop-color="#38bdf8"/><stop offset="1" stop-color="#34d399"/></linearGradient>
  <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#1b2c40" stroke-opacity=".32"/></pattern>
</defs>
<style>
  text { font-family: Consolas, "Liberation Mono", monospace; }
  @media (prefers-reduced-motion: reduce) { .cursor { display: none; } }
</style>
<rect x="1" y="1" width="998" height="408" rx="18" fill="#0b1220" stroke="#25384c"/>
<rect x="1" y="48" width="998" height="360" rx="18" fill="url(#grid)"/>
<path d="M1 48H999" stroke="#25384c"/>
<circle cx="26" cy="25" r="5" fill="#38bdf8"/>
<circle cx="45" cy="25" r="5" fill="#34d399"/>
<circle cx="64" cy="25" r="5" fill="#334155"/>
<text x="500" y="30" fill="#a7b6ca" font-size="13" text-anchor="middle">codebyabdulaziz / profile</text>
<text x="34" y="87" fill="#34d399" font-size="16">abdulaziz@github<tspan fill="#cbd5e1">:~$ whoami</tspan></text>
<rect x="34" y="111" width="280" height="226" rx="12" fill="#0d1929" stroke="#20364b"/>
<path d="M340 119V330" stroke="#25384c"/>
'''


def build() -> str:
    parts = [SVG_START]
    letter_a = ["   ###   ", "  ## ##  ", " ##   ## ", "#########", "##     ##", "##     ##", "##     ##"]
    letter_z = ["#########", "      ## ", "     ##  ", "   ##    ", "  ##     ", " ##      ", "#########"]
    for row, (a, z) in enumerate(zip(letter_a, letter_z)):
        duration = 0.55 + row * 0.13
        parts.append(f'<defs><clipPath id="row{row}"><rect x="50" y="{137 + row * 22}" width="252" height="23"><animate attributeName="width" from="0" to="252" dur="{duration:.2f}s" fill="freeze"/></rect></clipPath></defs>')
        parts.append(f'<text x="58" y="{155 + row * 22}" xml:space="preserve" font-size="18" font-weight="700" clip-path="url(#row{row})"><tspan fill="#38bdf8">{a}</tspan><tspan fill="#34d399">  {z}</tspan></text>')
    parts.append('<text x="174" y="317" font-size="12" fill="#a7b6ca" text-anchor="middle" letter-spacing="2">BUILD / LEARN / IMPROVE</text>')
    parts.append('<text x="371" y="147" fill="#f1f5f9" font-size="34" font-weight="700">Abdulaziz</text>')
    parts.append('<path d="M372 163H948" stroke="#25384c" stroke-dasharray="4 5"/>')
    details = [
        ("Based in", "Saudi Arabia"),
        ("Focus", "Data analysis + useful tools"),
        ("Tools", "Python / SQL / pandas"),
        ("Projects", "Dashboards / APIs / IoT"),
        ("Learning", "Machine learning"),
    ]
    for row, (label, value) in enumerate(details):
        duration = 0.8 + row * 0.14
        animation = f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;0.55;1" dur="{duration:.2f}s" fill="freeze"/>'
        parts.append(f'<text x="372" y="{192 + row * 31}" font-size="17" fill="#38bdf8">{escape(label)}{animation}</text>')
        parts.append(f'<text x="485" y="{192 + row * 31}" font-size="17" fill="#cbd5e1">{escape(value)}{animation}</text>')
    parts.append('''<rect x="34" y="358" width="932" height="1" fill="url(#accent)" opacity=".6"/>
<text x="34" y="385" fill="#f1f5f9" font-size="19">Improve your tech with me.</text>
<text x="966" y="384" fill="#94a3b8" font-size="13" text-anchor="end">codebyabdulaziz.github.io</text>
<rect class="cursor" x="335" y="371" width="8" height="17" fill="#34d399"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.49;.5;1" dur="1.4s" repeatCount="indefinite"/></rect>
</svg>''')
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    destination = ROOT / "assets" / "identity.svg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build(), encoding="utf-8")
    print("Updated assets/identity.svg")
