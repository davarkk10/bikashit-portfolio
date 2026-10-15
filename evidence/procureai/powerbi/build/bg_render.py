"""Render ProcureAI report backgrounds (1280x720 canvas at 2x = 2560x1440).

- sidebar(active): the left menu with 12 entries (00-08 + Model results 09-11)
- new pages 09-11: full backgrounds in the same style as the existing ones
- existing pages: original background with only the sidebar column replaced
"""
import os
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
FONTS = Path(os.environ.get('PROCUREAI_FONTS', HERE / 'fonts'))  # Manrope + JetBrains Mono TTFs
MANROPE = FONTS / 'gfonts/ofl/manrope/Manrope[wght].ttf'
JBM = FONTS / 'JetBrainsMono/fonts/ttf'

NAV = [('00', 'Briefing'), ('01', 'Executive cockpit'), ('02', 'Spend & category'), ('03', 'Supplier 360'),
       ('04', 'Invoice exceptions'), ('05', 'Contract intelligence'), ('06', 'Cash & approvals'), ('07', 'Data quality'),
       ('08', 'Record drill-through'), ('09', 'Invoice risk model'), ('10', 'Late-delivery model'), ('11', 'Contract assistant')]
# vertical centre of each menu item, in canvas units (1280x720)
STEP = 37
NAV_Y = [131 + i * STEP for i in range(9)] + [131 + 9 * STEP + 26 + i * STEP for i in range(3)]
GROUP_LABEL_Y = 131 + 8 * STEP + 34

import base64
def _uri(p): return 'data:font/ttf;base64,' + base64.b64encode(Path(p).read_bytes()).decode()
_FF = (f"@font-face {{ font-family: Manrope; src: url('{_uri(MANROPE)}'); font-weight: 200 800; }}\n"
       f"@font-face {{ font-family: JBM; src: url('{_uri(JBM / 'JetBrainsMono-Regular.ttf')}'); font-weight: 400; }}\n"
       f"@font-face {{ font-family: JBM; src: url('{_uri(JBM / 'JetBrainsMono-Medium.ttf')}'); font-weight: 500; }}\n"
       f"@font-face {{ font-family: JBM; src: url('{_uri(JBM / 'JetBrainsMono-Bold.ttf')}'); font-weight: 700; }}\n")
CSS = _FF + f"""
:root {{ --side:#0a1120; --sideline:#1c283f; --ink:#f5f7fb; --soft:#c6cfdb; --muted:#7f8ba0; --lime:#9cff1e;
        --panel:#0f1a2c; --panelline:#1d2a42; --teal:#45e4ce; --amber:#ffc857; --red:#ff5b6e; --blue:#5b9bff; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: 1280px; height: 720px; overflow: hidden; background: transparent; }}
body {{ font-family: Manrope, sans-serif; color: var(--ink); -webkit-font-smoothing: antialiased; }}
.mono {{ font-family: JBM, monospace; }}
.side {{ position: absolute; left: 0; top: 0; width: 192px; height: 720px; background: var(--side); border-right: 1px solid var(--sideline); }}
.logo {{ position: absolute; left: 22px; top: 26px; width: 11px; height: 11px; border-radius: 3px; background: var(--lime);
         box-shadow: 0 0 10px 2px rgba(156,255,30,.35); }}
.brand {{ position: absolute; left: 44px; top: 23px; font-weight: 800; font-size: 19.5px; letter-spacing: -.3px; }}
.tag {{ position: absolute; left: 44px; top: 53px; font-size: 8.8px; font-weight: 500; color: #8d99ad; letter-spacing: .5px; }}
.item {{ position: absolute; left: 12px; width: 168px; height: 32px; display: flex; align-items: center; border-radius: 9px; }}
.item .n {{ width: 32px; padding-left: 10px; font-family: JBM; font-weight: 700; font-size: 8.8px; color: #8590a4; }}
.item .t {{ font-weight: 600; font-size: 12.9px; letter-spacing: -.1px; color: #dfe5ef; white-space: nowrap; }}
.item.on {{ background: #13203a; border-left: 3px solid var(--lime); }}
.item.on .n {{ color: var(--lime); padding-left: 7px; }}
.item.on .t {{ color: #ffffff; }}
.group {{ position: absolute; left: 22px; font-family: JBM; font-weight: 700; font-size: 7.6px; letter-spacing: 1.4px; color: var(--teal); }}
.group::after {{ content: ''; position: absolute; left: 0; right: -128px; top: -9px; border-top: 1px solid var(--sideline); }}
.badge {{ position: absolute; left: 22px; top: 621px; padding: 3px 9px; border: 1px solid #6b5520; border-radius: 99px;
          background: #2a2210; color: var(--amber); font-family: JBM; font-weight: 700; font-size: 7.8px; letter-spacing: 1px; }}
.seed {{ position: absolute; left: 22px; top: 646px; width: 150px; font-size: 9.4px; line-height: 1.38; color: #7f8ba0; }}
.by {{ position: absolute; left: 22px; top: 688px; font-family: JBM; font-weight: 700; font-size: 9.2px; letter-spacing: .3px; color: #e6ebf3; }}
.main {{ position: absolute; left: 192px; top: 0; width: 1088px; height: 720px;
         background: radial-gradient(900px 420px at 92% -10%, #1b2c58 0%, rgba(14,24,48,.6) 38%, rgba(8,13,25,0) 70%),
                     radial-gradient(500px 300px at 0% 105%, rgba(28,66,40,.55) 0%, rgba(8,13,25,0) 70%), #080d19; }}
.eyebrow {{ position: absolute; left: 20px; top: 21px; font-family: JBM; font-weight: 700; font-size: 10.4px; letter-spacing: 2.3px; color: var(--teal); }}
.title {{ position: absolute; left: 20px; top: 34px; font-weight: 800; font-size: 28px; letter-spacing: -.9px; }}
.sub {{ position: absolute; left: 20px; top: 76px; font-size: 12px; color: #c6cfdb; }}
.frame {{ position: absolute; background: rgba(15,26,44,.72); border: 1px solid var(--panelline); border-radius: 12px; }}
.kpi .lab {{ position: absolute; left: 0; right: 0; top: 13px; text-align: center; font-family: JBM; font-weight: 500; font-size: 8.4px; letter-spacing: 2px; color: #aab4c5; }}
.kpi .cap {{ position: absolute; left: 0; right: 0; bottom: 10px; text-align: center; font-size: 9.6px; color: #9aa6b8; }}
.kpi .bar {{ position: absolute; left: -1px; top: 10px; bottom: 10px; width: 3px; border-radius: 3px; }}
.ptitle {{ position: absolute; left: 16px; top: 14px; font-weight: 700; font-size: 14px; letter-spacing: -.2px; }}
.psub {{ position: absolute; left: 16px; top: 34px; font-family: JBM; font-size: 8.4px; color: #7f8ba0; letter-spacing: .3px; }}
.note {{ position: absolute; font-size: 11px; line-height: 1.5; color: #c6cfdb; }}
.note b {{ color: #fff; font-weight: 700; }}
.ins {{ position: absolute; left: 18px; top: 14px; font-family: JBM; font-weight: 700; font-size: 8.4px; letter-spacing: 2px; }}
.ins::before {{ content: '●  '; }}
.ihead {{ position: absolute; left: 18px; top: 32px; font-weight: 700; font-size: 13.5px; }}
.accent {{ position: absolute; left: -1px; top: 12px; bottom: 12px; width: 3px; border-radius: 3px; }}
.big {{ position: absolute; right: 18px; font-weight: 800; font-size: 30px; letter-spacing: -1px; text-align: right; }}
.bigcap {{ position: absolute; right: 18px; font-family: JBM; font-size: 7.6px; letter-spacing: 1.8px; color: #aab4c5; text-align: right; }}
"""


def sidebar_html(active):
    items = ''.join(f'<div class="item{" on" if i == active else ""}" style="top:{NAV_Y[i] - 16}px"><span class="n">{n}</span>'
                    f'<span class="t">{t.replace("&", "&amp;")}</span></div>' for i, (n, t) in enumerate(NAV))
    return (f'<div class="side"><div class="logo"></div><div class="brand">ProcureAI</div>'
            f'<div class="tag mono">FMCG · source-to-pay</div>{items}'
            f'<div class="group" style="top:{GROUP_LABEL_Y - 4}px">MODEL RESULTS · OCT 2026</div>'
            f'<div class="badge">SYNTHETIC DATA</div>'
            f'<div class="seed">Seed 20260927 · scores rank what to investigate, they are not fraud findings.</div>'
            f'<div class="by">Bikashit Baruah</div></div>')


def kpi(x, y, w, h, label, cap, color):
    return (f'<div class="frame kpi" style="left:{x - 192}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<div class="bar" style="background:{color}"></div><div class="lab">{label}</div><div class="cap">{cap}</div></div>')


def panel(x, y, w, h, title, sub=''):
    return (f'<div class="frame" style="left:{x - 192}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<div class="ptitle">{title}</div><div class="psub">{sub}</div></div>')


def insight(x, y, w, h, color, kicker, head, body_html, big=None, bigcap=None):
    s = (f'<div class="frame" style="left:{x - 192}px;top:{y}px;width:{w}px;height:{h}px">'
         f'<div class="accent" style="background:{color}"></div><div class="ins" style="color:{color}">{kicker}</div>'
         f'<div class="ihead">{head}</div><div class="note" style="left:18px;top:54px;width:{w - (210 if big else 36)}px">{body_html}</div>')
    if big:
        s += f'<div class="big" style="top:{h / 2 - 30}px;color:{color}">{big}</div><div class="bigcap" style="top:{h / 2 + 10}px">{bigcap}</div>'
    return s + '</div>'


def page_html(active, main=''):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{sidebar_html(active)}{main}</body></html>'


def render(html, out, browser, clip=None):
    page = browser.new_page(viewport={'width': 1280, 'height': 720}, device_scale_factor=2)
    page.set_content(html)
    page.wait_for_timeout(300)
    page.evaluate('document.fonts.ready')
    page.screenshot(path=str(out), clip=clip, omit_background=True)
    page.close()


if __name__ == '__main__':
    with sync_playwright() as p:
        b = p.chromium.launch()
        render(page_html(4, '<div class="main"></div>'), HERE / 'test_side.png', b, clip={'x': 0, 'y': 0, 'width': 210, 'height': 720})
        b.close()
