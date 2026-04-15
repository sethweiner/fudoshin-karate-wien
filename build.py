#!/usr/bin/env python3
"""
Build script: reads YAML data from content/ and injects it into index_template.html
to produce index.html. Runs on Netlify deploy or locally.
"""
import re, yaml, html as htmlmod
from pathlib import Path

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "index_template.html"
OUTPUT = ROOT / "index.html"
CONTENT = ROOT / "content"


def load(name):
    with open(CONTENT / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def replace_section(src, section_id, new_inner):
    """Replace the innerHTML of <section ... id="section_id"> ... </section>."""
    pattern = re.compile(
        rf'(<section\s[^>]*id="{section_id}"[^>]*>)(.*?)(</section>)',
        re.DOTALL,
    )
    return pattern.sub(rf'\1\n{new_inner}\n      \3', src, count=1)


def replace_block(src, start_marker, end_marker, new_content):
    """Replace content between two HTML comment markers."""
    pattern = re.compile(
        rf'({re.escape(start_marker)})(.*?)({re.escape(end_marker)})',
        re.DOTALL,
    )
    return pattern.sub(rf'\1\n{new_content}\n  \3', src, count=1)


# ── GALLERY ────────────────────────────────────────────────────
def build_gallery(data):
    lines = []
    for p in data["photos"]:
        hidden = " wrapper_image--hidden" if p.get("hidden") else ""
        lines.append(f'            <div class="wrapper_image{hidden}"><img src="{p["thumb"]}" data-full="{p["full"]}" alt="{htmlmod.escape(p["alt"])}"></div>')
    photos_html = "\n".join(lines)
    caption = data.get("caption_html", "")
    caption_html = f'\n          <p class="caption" data-i18n-html="caption.photos">{caption}</p>' if caption else ""
    return f"""        <div class="section_wrapper">
          <div class="photo-grid reveal-group">
{photos_html}
          </div>{caption_html}
          <div class="photo-grid__link"><a href="galerie.html" data-i18n="gallery.link">Alle Fotos ansehen →</a></div>
        </div>"""


# ── SCHEDULE ───────────────────────────────────────────────────
def build_schedule(data):
    cards = []
    for i, d in enumerate(data["days"], 1):
        slots_html = "\n".join(
            f'                <div class="schedule-slot">'
            f'<span class="schedule-slot__time" data-i18n="schedule.d{i}.s{j}.time">{htmlmod.escape(s["time"])}</span>'
            f'<span class="schedule-slot__group" data-i18n="schedule.d{i}.s{j}.group">{htmlmod.escape(s["group"])}</span>'
            f'</div>'
            for j, s in enumerate(d["slots"], 1)
        )
        cards.append(f"""
            <div class="schedule-card">
              <div class="schedule-card__header">
                <span class="schedule-card__day" data-i18n="schedule.d{i}.day">{htmlmod.escape(d["day"])}</span>
                <span class="schedule-card__location" data-location="{htmlmod.escape(d["location_name"])}" data-address="{htmlmod.escape(d["location_address"])}" data-lat="{d["lat"]}" data-lng="{d["lng"]}">
                  <span class="schedule-row__location-pin">⊙</span>
                  <span data-i18n="schedule.d{i}.location">{htmlmod.escape(d["location_display"])}</span>
                </span>
              </div>
              <div class="schedule-card__slots">
{slots_html}
              </div>
            </div>""")

    cards_html = "\n".join(cards)
    return f"""        <div class="section_wrapper">
          <h2 class="reveal" data-i18n="schedule.title">Trainingszeiten</h2>
          <div class="schedule schedule--days reveal">
{cards_html}
          </div>
        </div>"""


# ── PRICING ────────────────────────────────────────────────────
def build_pricing(data):
    cards = []
    prefixes = ["s", "a", "f", "d", "e"]  # up to 5 cards
    for i, card in enumerate(data["cards"]):
        p = prefixes[i] if i < len(prefixes) else f"x{i}"
        hl = " preise-card--highlight" if card.get("highlighted") else ""
        features = "\n".join(
            f'                <li data-i18n="pricing.{p}.f{j+1}">{htmlmod.escape(f)}</li>'
            for j, f in enumerate(card["features"])
        )
        cards.append(f"""            <div class="preise-card{hl}">
              <span class="preise-card__label" data-i18n="pricing.{p}.label">{htmlmod.escape(card["label"])}</span>
              <div class="preise-card__price">{htmlmod.escape(card["price"])}</div>
              <p class="preise-card__unit" data-i18n="pricing.{p}.unit">{htmlmod.escape(card["unit"])}</p>
              <ul class="preise-card__features">
{features}
              </ul>
            </div>""")

    cards_html = "\n".join(cards)
    note = htmlmod.escape(data.get("note", ""))
    return f"""        <div class="section_wrapper">
          <h2 class="reveal" data-i18n="pricing.title">Preise</h2>
          <div class="preise-grid reveal-group">
{cards_html}
          </div>
          <p class="preise-note" data-i18n="pricing.note">{note}</p>
          <div class="preise-cta">
            <button class="preise-cta__btn" data-open-modal="member" data-i18n="pricing.cta">Jetzt anmelden →</button>
          </div>
        </div>"""


# ── ACTIVITIES ─────────────────────────────────────────────────
def build_activities(data):
    cards = []
    i18n_keys = ["activities.tournaments", "activities.selfdefense", "activities.camps",
                 "activities.item4", "activities.item5"]
    desc_keys = ["activities.tournaments.desc", "activities.selfdefense.desc", "activities.camps.desc",
                 "activities.item4.desc", "activities.item5.desc"]
    for i, item in enumerate(data["items"]):
        key = i18n_keys[i] if i < len(i18n_keys) else f"activities.item{i+1}"
        dkey = desc_keys[i] if i < len(desc_keys) else f"activities.item{i+1}.desc"
        desc = item.get("description", "")
        desc_html = ""
        if desc:
            desc_html = f"""
              <div class="aktivitaet-card__desc" data-i18n="{dkey}">{htmlmod.escape(desc)}</div>"""
        cards.append(f"""            <div class="aktivitaet-card">
              <figure><img src="{item["image_thumb"]}" data-full="{item["image_full"]}" alt="{htmlmod.escape(item["alt"])}"></figure>
              <h2 class="heading-4 _2" data-i18n="{key}">{htmlmod.escape(item["title"])}</h2>{desc_html}
            </div>""")

    cards_html = "\n".join(cards)
    return f"""        <div class="section_wrapper">
          <h2 class="reveal" data-i18n-html="activities.title">Projekte &amp; Aktivitäten</h2>
          <div class="aktivitaeten-grid reveal-group">
{cards_html}
          </div>
        </div>"""


# ── STICKER ────────────────────────────────────────────────────
def build_sticker(data):
    if not data.get("visible", True):
        return ""
    return f"""  <div class="sticker" id="the-sticker" data-shape="sharp" data-align="left" data-tooltip="{htmlmod.escape(data["tab_text"])}">
    <button class="sticker__close" id="sticker-close" aria-label="Schließen">✕</button>
    <div class="sticker__body">
      <span class="sticker__label" data-i18n="sticker.label">{htmlmod.escape(data["label"])}</span>
      <div class="sticker__headline" data-i18n-html="sticker.headline">{data["headline"]}</div>
      <div class="sticker__detail" data-i18n-html="sticker.detail">{data["detail"]}</div>
      <a href="{data["cta_link"]}" class="sticker__cta" id="sticker-cta" data-i18n="sticker.cta">{htmlmod.escape(data["cta_text"])}</a>
    </div>
    <button class="sticker__tab" id="sticker-tab">
      <span class="sticker__tab-text" data-i18n="sticker.tab">{htmlmod.escape(data["tab_text"])}</span>
      <i class="sticker__chevron">☀</i>
    </button>
  </div>"""


# ── MAIN ───────────────────────────────────────────────────────
def main():
    src = TEMPLATE.read_text(encoding="utf-8")

    gallery = load("gallery.yml")
    schedule = load("schedule.yml")
    pricing = load("pricing.yml")
    activities = load("activities.yml")
    sticker = load("sticker.yml")

    # Replace sections by id
    src = replace_section(src, "fotos", build_gallery(gallery))
    src = replace_section(src, "training", build_schedule(schedule))
    src = replace_section(src, "preise", build_pricing(pricing))
    src = replace_section(src, "aktivitaeten", build_activities(activities))

    # Replace sticker block (between markers)
    sticker_html = build_sticker(sticker)
    src = replace_block(
        src,
        "<!-- ══════════════ STICKER ══════════════ -->",
        "<!-- ══════════════ /STICKER ══════════════ -->",
        sticker_html + "\n",
    )

    OUTPUT.write_text(src, encoding="utf-8")
    print(f"✓ Built {OUTPUT.name} ({len(src):,} bytes)")

    # ── SHARED CSS — extract for gallery page ──
    tmpl_src = TEMPLATE.read_text(encoding="utf-8")
    style_start = tmpl_src.index("<style>") + len("<style>")
    style_end = tmpl_src.index("</style>")
    shared_css = tmpl_src[style_start:style_end]
    css_file = ROOT / "styles.css"
    css_file.write_text(shared_css, encoding="utf-8")

    # ── GALLERY PAGE — copy template (uses <link> to styles.css) ──
    galerie_tmpl = ROOT / "galerie_template.html"
    galerie_out = ROOT / "galerie.html"
    if galerie_tmpl.exists():
        galerie_src = galerie_tmpl.read_text(encoding="utf-8")
        galerie_out.write_text(galerie_src, encoding="utf-8")
        print(f"✓ Built {galerie_out.name} ({len(galerie_src):,} bytes)")


if __name__ == "__main__":
    main()
