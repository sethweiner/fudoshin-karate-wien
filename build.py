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
    photos_html = "\n".join(
        f'            <div class="wrapper_image"><img src="{p["thumb"]}" data-full="{p["full"]}" alt="{htmlmod.escape(p["alt"])}"></div>'
        for p in data["photos"]
    )
    caption = data.get("caption_html", "")
    return f"""        <div class="section_wrapper">
          <div class="photo-grid reveal-group">
{photos_html}
          </div>
          <p class="caption" data-i18n-html="caption.photos">{caption}</p>
        </div>"""


# ── SCHEDULE ───────────────────────────────────────────────────
def build_schedule(data):
    rows = []
    for i, g in enumerate(data["groups"], 1):
        days_html = "\n".join(
            f'                <span class="schedule-row__day">{d}</span>'
            for d in g["days"]
        )
        rows.append(f"""
            <div class="schedule-row">
              <div class="schedule-row__group" data-i18n-html="schedule.r{i}.group">{g["name_html"]}</div>
              <div class="schedule-row__age" data-i18n="schedule.r{i}.age">{htmlmod.escape(g["age"])}</div>
              <div class="schedule-row__days">
{days_html}
              </div>
              <div class="schedule-row__location" data-location="{htmlmod.escape(g["location_name"])}" data-address="{htmlmod.escape(g["location_address"])}" data-lat="{g["lat"]}" data-lng="{g["lng"]}">
                <span class="schedule-row__location-pin">⊙</span>
                {htmlmod.escape(g["location_display"])}
              </div>
            </div>""")

    rows_html = "\n".join(rows)
    return f"""        <div class="section_wrapper">
          <h2 class="reveal" data-i18n="schedule.title">Trainingszeiten</h2>
          <div class="schedule reveal">
            <div class="schedule-header">
              <span data-i18n="schedule.h.group">Gruppe</span>
              <span data-i18n="schedule.h.age">Alter / Level</span>
              <span data-i18n="schedule.h.days">Trainingstage</span>
              <span data-i18n="schedule.h.location">Standort</span>
            </div>
{rows_html}
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
        </div>"""


# ── ACTIVITIES ─────────────────────────────────────────────────
def build_activities(data):
    cards = []
    i18n_keys = ["activities.tournaments", "activities.seminars", "activities.camps",
                 "activities.item4", "activities.item5"]
    for i, item in enumerate(data["items"]):
        key = i18n_keys[i] if i < len(i18n_keys) else f"activities.item{i+1}"
        credit = ""
        if item.get("photo_credit"):
            credit = f"<figcaption>{htmlmod.escape(item['photo_credit'])}</figcaption>"
        cards.append(f"""            <div class="aktivitaet-card">
              <figure><img src="{item["image_thumb"]}" data-full="{item["image_full"]}" alt="{htmlmod.escape(item["alt"])}">{credit}</figure>
              <h2 class="heading-4 _2" data-i18n="{key}">{htmlmod.escape(item["title"])}</h2>
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
    <div class="sticker__body">
      <span class="sticker__label" data-i18n="sticker.label">{htmlmod.escape(data["label"])}</span>
      <div class="sticker__headline" data-i18n-html="sticker.headline">{data["headline"]}</div>
      <div class="sticker__detail" data-i18n-html="sticker.detail">{data["detail"]}</div>
      <a href="{data["cta_link"]}" class="sticker__cta" id="sticker-cta" data-i18n="sticker.cta">{htmlmod.escape(data["cta_text"])}</a>
    </div>
    <button class="sticker__tab" id="sticker-tab">
      <span class="sticker__tab-text" data-i18n="sticker.tab">{htmlmod.escape(data["tab_text"])}</span>
      <i class="sticker__chevron">▲</i>
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
        "<!-- ══════════════ LIGHTBOX ══════════════ -->",
        sticker_html + "\n",
    )

    OUTPUT.write_text(src, encoding="utf-8")
    print(f"✓ Built {OUTPUT.name} ({len(src):,} bytes)")


if __name__ == "__main__":
    main()
