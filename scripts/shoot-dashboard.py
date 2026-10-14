"""Captura screenshots de las pestañas del dashboard QZero para la landing."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("shots")
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://qzero.thempra.net/"
TABS = ["Overview", "Alerts", "Threats", "Network", "Agents", "Research"]
# slug EN para nombres de archivo (la landing los referenciará)
SLUGS = {"Overview": "overview", "Alerts": "alerts", "Threats": "threats",
         "Network": "network", "Agents": "agents", "Research": "research"}

HIDE_CSS = """
#MainMenu, header[data-testid='stHeader'] {display:none !important}
[data-testid='stAppViewContainer'] {padding-top:0 !important}
footer {display:none !important}
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1.5)
    pg.goto(URL, wait_until="networkidle", timeout=60_000)
    pg.add_style_tag(content=HIDE_CSS)
    pg.wait_for_timeout(3000)
    for tab in TABS:
        btn = pg.get_by_text(tab, exact=True).first
        btn.click()
        pg.wait_for_timeout(4500)  # plots Plotly/st.dataframe render
        # charts lazy: scroll para forzar render de lo de abajo en Overview
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        pg.wait_for_timeout(1200)
        pg.evaluate("window.scrollTo(0, 0)")
        pg.wait_for_timeout(800)
        f = OUT / f"{SLUGS[tab]}.png"
        pg.screenshot(path=str(f))
        print("shot:", f)
    b.close()
