"""Build the blog from posts.json.

  python build.py

Each post is a self-contained page in <slug>/ (index.html, og.jpg, fonts/), exported by the
project that writes it. This script:

  * generates the home page, the post index and the 404 page (posts/ holds the index);
  * enhances every exported post in place: heading ids, a table of contents, figure
    anchors, a reading time, Article JSON-LD, a footer and a back-to-contents link;
  * writes feed.xml, sitemap.xml and robots.txt.

Enhancement is idempotent: a post that already carries the marker comment is left alone.

site.json holds the public base URL, used for absolute og: links, the feed and the sitemap.
"""
import datetime
import html
import json
import os
import re
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = json.load(open(os.path.join(HERE, "site.json"), encoding="utf-8"))
BASE_PATH = urlparse(SITE["base"]).path or "/"
AUTHOR = "Veolyn Research"
# back matter stays out of the table of contents
SKIP_TOC = {"acknowledgements", "acknowledgments", "citation", "references"}
POSTS = sorted(json.load(open(os.path.join(HERE, "posts.json"), encoding="utf-8")), key=lambda p: p["date"], reverse=True)
MINUTES = {}  # slug -> reading time, filled while each post is enhanced

MARK = ('<svg viewBox="0 0 32 32" class="mark"><rect width="32" height="32" rx="8" fill="#1b1730"/>'
        '<rect x="6" y="6" width="20" height="20" rx="4.5" fill="none" stroke="#F6F4FF" stroke-width="2"/>'
        '<rect x="15.2" y="9" width="8" height="8" rx="1.5" fill="#C6E85A"/></svg>')
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='8' fill='%235747C1'/%3E%3Crect x='6' y='6' width='20' height='20' "
           "rx='4.5' fill='none' stroke='%23F6F4FF' stroke-width='2'/%3E%3Crect x='15.2' y='9' width='8' height='8' "
           "rx='1.5' fill='%23C6E85A'/%3E%3C/svg%3E")
ORBS = ('<div class="orb" style="width:520px;height:520px;right:-140px;top:-160px;background:#7b6be0;opacity:.55"></div>'
        '<div class="orb" style="width:380px;height:380px;left:-120px;bottom:-200px;background:#c6e85a;opacity:.16"></div>')

FEED_LINK = '<link rel="alternate" type="application/atom+xml" title="{name}" href="{href}">'
SKIP = '<a class="skip" href="#main">Skip to content</a>'

FOOTER_NAV = ('<nav><a href="{rel}">Home</a><a href="{rel}posts/">All posts</a>'
              '<a href="{rel}feed.xml">RSS</a></nav>')

POST_CSS = """<style>
/* build.py additions: skip link, contents, figure links, footer, print */
.skip { position: absolute; left: -9999px; top: 0; z-index: 99; background: #1b1730; color: #fff; padding: 10px 16px; border-radius: 0 0 10px 0; }
.skip:focus { left: 0; }
:focus-visible { outline: 2px solid var(--purple); outline-offset: 3px; border-radius: 4px; }
nav.toc { margin: 0 0 38px; padding: 22px 26px 18px; border: 1px solid rgba(87,71,193,.16); border-radius: 18px; background: #fff; box-shadow: 0 2px 10px rgba(40,26,120,.04); }
nav.toc .toc-h { margin: 0 0 10px; font: 600 10.5px/1 var(--mono); letter-spacing: .16em; text-transform: uppercase; color: var(--muted-ink); }
nav.toc ol { margin: 0; padding: 0; list-style: none; }
nav.toc li { margin: 0; }
nav.toc li.l2 + li.l2 { margin-top: 8px; }
nav.toc a { display: grid; grid-template-columns: 2.7em 1fr; align-items: baseline; gap: 0 6px; padding: 6px 9px; margin: 0 -9px; border-bottom: 0; border-radius: 9px; color: var(--ink); text-decoration: none; font-size: 15.5px; line-height: 1.35; }
nav.toc a:hover { background: rgba(87,71,193,.07); }
nav.toc .n { font: 600 11px/1 var(--mono); letter-spacing: .07em; color: var(--purple); }
nav.toc li.l3 a { font-size: 14px; color: var(--muted-ink); padding-left: 20px; }
nav.toc li.l3 a:hover { color: var(--ink); }
nav.toc + h2 { margin-top: 16px; }
@media (max-width: 640px) {
  nav.toc { padding: 18px 16px 14px; border-radius: 14px; }
  nav.toc a { grid-template-columns: 2.3em 1fr; font-size: 14.5px; padding: 5px 7px; margin: 0 -7px; }
  nav.toc li.l3 a { font-size: 13.5px; padding-left: 14px; }
}
a.figref { color: var(--purple); text-decoration: none; white-space: nowrap; border-bottom: 1px solid rgba(87,71,193,.3); }
a.figref:hover { background: rgba(87,71,193,.08); }
figure[id] { scroll-margin-top: 24px; }
h2[id], h3[id] { scroll-margin-top: 24px; }
p.totop { margin: 44px 0 0; text-align: center; }
p.totop a { font: 600 12.5px var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--purple); text-decoration: none; border-bottom: 0; }
p.totop a:hover { text-decoration: underline; }
footer nav { display: flex; gap: 18px; }
footer nav a { color: inherit; text-decoration: none; border-bottom: 0; }
footer nav a:hover { color: var(--white); }
@media print {
  header.hero, footer, nav.toc, p.totop, .skip { display: none !important; }
  main { max-width: none; padding: 0; }
  figure.wide { width: 100% !important; }
  body { font-size: 11pt; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
"""


def esc(s):
    return html.escape(s, quote=True)


def nice_date(d):
    day = datetime.date.fromisoformat(d)
    return f"{day:%b} {day.day}, {day:%Y}"


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "section"


def reading_minutes(body):
    """Words in the article itself: chrome, contents and footers are not reading."""
    text = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", body, flags=re.S)
    text = re.sub(r'<nav class="toc".*?</nav>', " ", text, flags=re.S)
    text = re.sub(r'<p class="totop">.*?</p>', " ", text, flags=re.S)
    text = re.sub(r"<footer.*?</footer>", " ", text, flags=re.S)
    text = re.sub(r'<div class="byline">.*?</div>', " ", text, flags=re.S)
    text = re.sub(r'<a class="skip".*?</a>', " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    words = len(text.split())
    return max(1, round(words / 220))


def page(rel, path, title, desc, tab, hero, body, image=None):
    url = SITE["base"] + path
    image = image or SITE["base"] + "assets/avatar.png"
    on = ' class="on"'
    tabs = "".join(f'<a href="{rel}{href}"{on if name == tab else ""}>{name}</a>'
                   for name, href in (("Home", ""), ("Blog", "posts/")))
    slash = ("<script>if(!location.pathname.endsWith('/'))"
             "location.replace(location.pathname+'/'+location.search+location.hash)</script>\n" if path.endswith("/") or not path else "")
    feed = FEED_LINK.format(name=esc(SITE["name"]), href=rel + "feed.xml")
    footer = FOOTER_NAV.format(rel=rel)
    return f"""<!doctype html>
<html lang="en">
<head>
{slash}<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE['name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{image}">
<meta name="twitter:card" content="{'summary_large_image' if 'og.jpg' in image else 'summary'}">
{feed}
<link rel="icon" href="{FAVICON}">
<link rel="apple-touch-icon" href="{rel}assets/avatar.png">
<link rel="stylesheet" href="{rel}assets/site.css">
</head>
<body>
{SKIP}
<header class="hero{'' if tab == 'Home' else ' short'}">
{ORBS}
<div class="hero-in">
<nav class="top"><a class="brand" href="{rel}">{MARK}<span class="word">VEOLYN</span></a><div class="tabs">{tabs}</div></nav>
{hero}
</div>
</header>
<main id="main">
{body}
</main>
<footer><div><span>© {datetime.date.today().year} {esc(SITE['name'])}</span>{footer}</div></footer>
</body>
</html>
"""


def post_meta(p):
    date = nice_date(p["date"])
    minutes = MINUTES.get(p["slug"])
    return f"{date} · {minutes} min read" if minutes else date


def cards(rel):
    out = []
    for p in POSTS:
        href = f"{rel}{p['slug']}/"
        out.append(f"""<a class="post" href="{href}">
<img src="{href}og.jpg" alt="" loading="lazy">
<div><div class="meta"><span class="tag">{esc(p['tag'])}</span><span>{post_meta(p)}</span></div>
<h2>{esc(p['title'])}</h2>
<p>{esc(p['summary'])}</p>
<span class="more">Read the post →</span></div>
</a>""")
    return '<div class="posts">\n' + "\n".join(out) + "\n</div>"


def home():
    hero = f"""<div class="kicker"><span class="n">{esc(SITE['name'])}</span></div>
<h1>Specialized intelligence <span class="hl">for the enterprise.</span></h1>
<p class="lead">General models know a little about everything. We build models that know your business: adapted to your data and tasks, measured on the checks that matter to you, and served where you need them.</p>
<div class="cta"><a class="btn lime" href="posts/">Read our research →</a></div>"""
    body = """<p class="label">Research</p>
<p class="intro">Part of our work is research on what happens inside models, and how to change it directly.</p>
""" + cards("")
    return page("", "", SITE["name"], "Specialized intelligence for the enterprise.", "Home", hero, body)


def index():
    hero = """<div class="kicker"><span class="n">Blog</span>Veolyn AI research</div>
<h1>Research from <span class="hl">Veolyn.</span></h1>
<p class="lead">What we learn while building specialized models: how to train them, how to measure them, how to serve them, and what happens inside them. Every post comes with the numbers behind its claims.</p>"""
    return page("../", "posts/", f"Blog · {SITE['name']}", "Research notes from Veolyn AI on building, measuring and understanding specialized models.",
                "Blog", hero, cards("../"))


def not_found():
    hero = """<div class="kicker"><span class="n">404</span>Not found</div>
<h1>This page doesn't exist.</h1>"""
    body = '<p class="label">Try the blog</p>\n' + cards(BASE_PATH)
    return page(BASE_PATH, "404.html", f"Not found · {SITE['name']}", "Page not found.", "", hero, body)


def enhance_post(text, post):
    """Add ids, contents, figure anchors, reading time, JSON-LD and a footer to an export."""
    if "build:enhanced" in text:
        return text

    url = SITE["base"] + post["slug"] + "/"
    heading_count = len(re.findall(r"<h[23][^>]*>", text))
    minutes = reading_minutes(text)

    # 0. posts live one level below the site root, so nav written for the old
    #    blog/<slug>/ layout points one directory too high. Normalise it here so a
    #    fresh export is fixed on the next build.
    text = text.replace('class="brand" href="../../"', 'class="brand" href="../"')
    text = text.replace('<a href="../../">Home</a>', '<a href="../">Home</a>')
    text = text.replace('<a class="on" href="../">Blog</a>', '<a class="on" href="../posts/">Blog</a>')

    # 1. heading ids, collecting the contents on the way
    entries = []

    def head(m):
        lvl, attrs, inner = m.group(1), m.group(2), m.group(3)
        plain = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        num = ""
        mm = re.match(r"^(\d{2})\s*(.+)$", plain)
        if mm:
            num, plain = mm.group(1), mm.group(2)
        if "id=" in attrs:
            hid = re.search(r'id="([^"]+)"', attrs).group(1)
        else:
            hid = "sec-" + slugify(plain)
            attrs = f' id="{hid}"' + attrs
        entries.append((lvl, hid, num, plain))
        return f"<h{lvl}{attrs}>{inner}</h{lvl}>"

    text = re.sub(r"<h([23])([^>]*)>(.*?)</h\1>", head, text, flags=re.S)

    # 2. table of contents, right after the article opens
    if len(entries) >= 3 and 'nav class="toc"' not in text:
        has_intro = 'id="sec-introduction"' in text
        rows = ([] if has_intro else [("l2", "intro", "00", "Introduction")]) + [
            (f"l{lvl}", hid, num, label)
            for lvl, hid, num, label in entries
            if label.strip().lower() not in SKIP_TOC]
        items = "\n".join(
            f'<li class="{cls}"><a href="#{hid}"><span class="n">{num}</span>'
            f'<span class="t">{esc(label)}</span></a></li>'
            for cls, hid, num, label in rows)
        toc = ('<nav class="toc" id="toc" aria-label="Contents">\n'
               '<p class="toc-h">Contents</p>\n<ol>\n' + items + "\n</ol>\n</nav>\n")
        if not has_intro:
            toc += '<span id="intro"></span>\n'
        text = text.replace('<article class="col">', '<article class="col">\n' + toc, 1)

    # 3. figure anchors
    def figure(m):
        attrs, body = m.group(1), m.group(2)
        if "id=" in attrs:
            return m.group(0)
        n = re.search(r"Figure\s+(\d+)", body)
        if not n:
            return m.group(0)
        return f'<figure id="figure-{n.group(1)}"{attrs}>{body}</figure>'

    text = re.sub(r"<figure([^>]*)>(.*?)</figure>", figure, text, flags=re.S)

    # 4. in-text "Figure N" becomes a jump link
    def para(m):
        block = m.group(0)
        if "figref" in block:
            return block
        return re.sub(r"Figure (\d+)",
                      r'<a class="figref" href="#figure-\1">Figure \1</a>',
                      block)

    text = re.sub(r"<p(?: [^>]*)?>.*?</p>", para, text, flags=re.S)

    # 5. reading time, back to contents
    text = re.sub(r'(<div class="byline">.*?)(</div>)',
                  lambda m: f"{m.group(1)} · {minutes} min read{m.group(2)}",
                  text, count=1, flags=re.S)
    if 'class="totop"' not in text and "</article>" in text:
        text = text.replace("</article>",
                            '<p class="totop"><a href="#toc">↑ Back to contents</a></p>\n</article>', 1)

    # 6. footer with somewhere to go
    text = re.sub(
        r"<footer><div><span>.*?</span><span>.*?</span></div></footer>",
        '<footer><div><span>{name}</span>{nav}</div></footer>'.format(
            name=esc(AUTHOR), nav=FOOTER_NAV.format(rel="../")),
        text, count=1, flags=re.S)

    # 7. skip link
    if 'class="skip"' not in text:
        text = text.replace("<body>", "<body>\n" + SKIP, 1)
        text = re.sub(r"<main>", '<main id="main">', text, count=1)

    # 8. head additions: feed discovery, Article JSON-LD, styles
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["title"],
        "description": post["summary"],
        "datePublished": post["date"],
        "url": url,
        "image": url + "og.jpg",
        "author": {"@type": "Organization", "name": AUTHOR},
        "publisher": {"@type": "Organization", "name": AUTHOR},
    }
    head_add = (
        FEED_LINK.format(name=esc(SITE["name"]), href="../feed.xml") + "\n"
        + ("" if 'rel="canonical"' in text else '<link rel="canonical" href="' + url + '">\n')
        + '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>\n"
        + POST_CSS
    )
    text = text.replace("</head>", head_add + "</head>", 1)
    text = text.rstrip() + "\n<!-- build:enhanced -->\n"
    return text


def feed():
    updated = POSTS[0]["date"] + "T00:00:00Z" if POSTS else "2026-01-01T00:00:00Z"
    entries = []
    for p in POSTS:
        url = SITE["base"] + p["slug"] + "/"
        entries.append(f"""  <entry>
    <title>{esc(p['title'])}</title>
    <link href="{url}"/>
    <id>{url}</id>
    <updated>{p['date']}T00:00:00Z</updated>
    <summary>{esc(p['summary'])}</summary>
  </entry>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{esc(SITE['name'])}</title>
  <link rel="alternate" type="text/html" href="{SITE['base']}"/>
  <link rel="self" type="application/atom+xml" href="{SITE['base']}feed.xml"/>
  <id>{SITE['base']}</id>
  <updated>{updated}</updated>
  <author><name>{esc(AUTHOR)}</name></author>
{chr(10).join(entries)}
</feed>
"""


def sitemap():
    urls = [SITE["base"], SITE["base"] + "posts/"]
    urls += [SITE["base"] + p["slug"] + "/" for p in POSTS]
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}\n</urlset>\n")


def robots():
    return ("User-agent: *\nAllow: /\n\n"
            f"Sitemap: {SITE['base']}sitemap.xml\n")


def write(path, text):
    full = os.path.join(HERE, path)
    os.makedirs(os.path.dirname(full) or HERE, exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    for p in POSTS:
        page_path = os.path.join(HERE, p["slug"], "index.html")
        assert os.path.exists(page_path), f"missing post {p['slug']}"
        original = open(page_path, encoding="utf-8").read()
        updated = enhance_post(original, p)
        minutes = reading_minutes(updated)
        updated = re.sub(r"·\s*\d+\s*min read", f"· {minutes} min read", updated, count=1)
        MINUTES[p["slug"]] = minutes
        if updated != original:
            with open(page_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(updated)
            print(f"enhanced {p['slug']} ({minutes} min)")
    write("index.html", home())
    write("posts/index.html", index())
    write("404.html", not_found())
    write("feed.xml", feed())
    write("sitemap.xml", sitemap())
    write("robots.txt", robots())
    write(".nojekyll", "")
    print(f"built {len(POSTS)} post(s) for {SITE['base']}")


if __name__ == "__main__":
    main()
