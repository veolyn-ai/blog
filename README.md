<div align="center">

<img src="./assets/avatar.png" alt="Veolyn AI" width="104" />

# Veolyn AI — Research Blog

**What we learn while building specialized models, with the numbers behind every claim.**

The public research blog of Veolyn AI. A home page and a post index in plain static
HTML and CSS: no framework, no runtime dependency, no build step at serve time.
GitHub Pages publishes the repository root of `main` as is.

[Read the blog →](https://veolyn-ai.github.io/blog/)

</div>

---

## What this is

This repository *is* the blog — not an application that renders one. Every post is a
self-contained folder, `<slug>/`, exported by the project that produced it; the
home page, the post index and the 404 page are generated from `posts.json` by
`build.py`. Nothing is fetched at runtime: no font CDN, no analytics, no JavaScript
bundle, no hydration step.

That constraint is deliberate. A post is a single HTML file with its figures inlined
as SVG and its fonts subsetted alongside it, so it renders identically years later,
offline, and from any mirror.

## Layout

| Path | Role |
|---|---|
| `build.py` | Generates `index.html`, `posts/index.html` and `404.html` from `posts.json`. |
| `posts.json` | Single source of truth for the index: `slug`, `title`, `date`, `tag`, `summary`. |
| `site.json` | Blog name and canonical base URL, used for absolute `og:` tags. |
| `<slug>/` | One post, self-contained — see below. Served at `/<slug>/`. |
| `posts/` | Generated: the index listing every post. |
| `assets/` | Shared stylesheet, Geist fonts (SIL OFL 1.1), avatar. |
| `.nojekyll` | Tells Pages to publish the build untouched. |

Generated pages are committed, so Pages needs no CI step to deploy. Edit the
generator and the data, never the generated HTML.

## Post anatomy

| File | Purpose |
|---|---|
| `index.html` | The post itself: prose, figures as inline SVG, styles scoped to the page. |
| `og.jpg` | 1200×630 share card, also the index thumbnail. |
| `fonts/` | Subsetted Geist, referenced relatively; `OFL.txt` travels with them. |

## Writing a post

```bash
# 1. export the post into <slug>/       (index.html, og.jpg, fonts/)
# 2. add its entry to posts.json        (slug, title, date, tag, summary)
python build.py
git add -A && git commit -m "Add post: <slug>" && git push
```

`build.py` asserts that every slug in `posts.json` has a matching
`<slug>/index.html`, so a missing export fails before any file is written.

The date is rendered as `Nov 7, 2026`; the summary is the line shown under the title
on the index and in link previews.

## Local preview

```bash
python3 -m http.server -d . 8000
```

Open <http://127.0.0.1:8000/>. Everything is static; no install step, no watcher.

## Publishing

GitHub Pages, source `main` / root, rebuilt on every push to `main`. The absolute URLs
in `og:url` and `og:image` come from `base` in `site.json` — if the blog moves to
another host, update that value and rebuild, or link previews will point at the wrong
domain.

## License

| What | License | Terms |
|---|---|---|
| Code — `build.py`, `assets/site.css` | MIT | [`LICENSE`](LICENSE) |
| Posts, copy, images | CC BY 4.0 | [`LICENSE-CONTENT`](LICENSE-CONTENT) |
| Geist fonts | SIL OFL 1.1 | `OFL.txt` in each `fonts/` directory |
