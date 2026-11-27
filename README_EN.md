# StarBox · Private Portfolio

English | [中文](README.md)

> Turn a set of photos into a portfolio you can actually send out.

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-built--in-003B57?logo=sqlite&logoColor=white)
![No build](https://img.shields.io/badge/frontend-no%20build-c9a227)
![License](https://img.shields.io/badge/license-MIT-c9a227)

---

## Why StarBox

- **Not cloud storage**: send a link to a friend or client — no sign-up, no app, it just opens.
- **Not a plain album**: cover, title, story, tags and password make a set of photos a finished piece of work.
- **Not public social**: public / private / password / revocable share link — only the right people see it.
- **Built to deliver**: proofs are watermarked automatically, originals stay with the author; clients pick favourites, you export the list and generate a poster for social.

The flow: **bulk upload → build a portfolio → share the link → export the delivery**.

## Features

- **Bulk upload**: up to 60 files at once, auto-grouped into one portfolio, 50MB per file
- **Watermarked proofs**: toggle per upload, custom watermark text; visitors only ever get the watermarked preview, originals are downloadable by the author and admins
- **Cover accent colour**: extracted from the cover automatically, the whole page adapts to each portfolio
- **Portfolio**: cover, description, Markdown story, tags, visibility, access password
- **Share link**: `/s/<token>` short link, copy and regenerate; password portfolios ask for the code
- **Guest picking**: visitors pick favourites without an account; the author sees how many times each photo was picked
- **Picks export**: one-click CSV with pick counts, ready for retouching
- **Vertical poster**: generate a 1080-wide portfolio poster for Instagram / Xiaohongshu / WeChat Moments
- **EXIF**: camera, lens, focal length, aperture, shutter, ISO are read and displayed automatically
- **Three visibility levels**: public / private (author and admins) / password
- **File cabinet**: PDFs, documents, archives, audio and video, download after login
- **Articles**: Markdown editing with headings, lists, code, quotes and images
- **Tags and search**: filter by type and tag, full-text search over title, body and tags
- **Accounts**: registration, first user becomes admin, password change, account deletion, public profile
- **Admin console**: content and visibility, users, site name / announcement / description / watermark text
- **Security**: PBKDF2 password hashing, HttpOnly sessions, media authorisation, upload allow-list, unlock rate limiting; portfolio detail never leaks private items

## Stack

Python 3.8+ standard library `http.server` + SQLite, vanilla HTML/CSS/JS on the front end. No build step, no web framework.

Image features (watermark, thumbnails, accent colour, EXIF, poster) use **Pillow**. Without it the app degrades to serving originals and everything else keeps working.

```bash
pip install Pillow
```

## Run

```bash
git clone https://github.com/jacksun-king/starbox-portfolio.git
cd starbox-portfolio
python server.py
```

Open `http://127.0.0.1:8766/`. Change the port with `PORT=9000 python server.py`.

**The first account registered becomes the admin.**

## Demo data

A fresh clone starts empty. To see the whole thing populated:

```bash
python seed_demo.py
```

It creates 3 portfolios, 12 photos (including private and password-protected examples), 3 articles and 18 sample picks. Demo account: **`curator / demo123`**.
Originals live in `demo/photos/`; watermarked proofs and thumbnails are generated on the spot by Pillow. Running it again changes nothing — use `python seed_demo.py --force` to rebuild.

## Pages

| Page | URL | Notes |
| --- | --- | --- |
| Home | `/index.html` | Portfolio-first feed, search, four-step intro |
| Portfolio | `/collection.html?id=<id>` | Cover, story, full set, picking, sharing, poster |
| Share page | `/s/<token>` | The short link you send out, no sign-up needed |
| Detail | `/item.html?id=<id>` | Content, EXIF, unlock, copy image URL, assign to portfolio |
| Studio | `/studio.html` | Bulk upload, watermark options, new portfolio, articles |
| Auth | `/auth.html` | The first registered user becomes admin |
| Profile | `/profile.html?user=<name>` | Public profile and content |
| Settings | `/settings.html` | Profile, password, delete account |
| Admin | `/admin.html` | Admins only |

## Project layout

```text
starbox-portfolio/
├─ server.py            # single-file backend: routing, auth, upload, portfolios, share, export
├─ imaging.py           # Pillow work: watermark, thumbnails, accent colour, EXIF, poster
├─ seed_demo.py         # demo data generator
├─ demo/photos/         # 12 demo originals
├─ index.html           # home
├─ collection.html      # portfolio / share page
├─ item.html            # item detail
├─ studio.html          # studio
├─ auth.html profile.html settings.html admin.html
├─ css/style.css        # dark gold visual system
├─ js/common.js         # icons, cards, request helpers
├─ data/                # created at runtime: SQLite, secret key, poster cache (git-ignored)
└─ uploads/             # created at runtime: originals, proofs, thumbnails (git-ignored)
```

## Data

- `data/site.db` — SQLite database (users, items, portfolios, picks, files, settings)
- `data/secret.key` — signing key for unlock cookies (**deleting it invalidates all unlocks**)
- `data/cache/` — generated portfolio posters
- `uploads/` — originals, `*_wm.jpg` watermarked proofs, `*_s.jpg` list thumbnails
- The database stores password hashes and is excluded by `.gitignore` — never commit it to a public repo

## API

Public: `GET /api/config`, `/api/items`, `/api/collections`, `/api/tags`, `/api/users/<name>`, `/api/share/<token>`, `/api/media?id=&size=s`; `POST /api/register`, `/api/login`, `/api/logout`, `/api/unlock`, `/api/collections/<id>/pick`

Signed in: `GET /api/items?scope=mine`, `/api/collections?scope=mine`, `/api/me`, `/api/download?id=`, `/api/media?id=&raw=1` (author only), `/api/collections/<id>/poster`, `/api/collections/<id>/picks.csv`; `POST /api/upload` (repeated `file` fields plus `collection_id` / `new_collection` / `watermark` / `watermark_text`), `/api/collections`, `/api/post`, `/api/me/password`, `/api/me/profile`; `PATCH /api/items/<id>` (incl. `collection_id`), `/api/collections/<id>` (incl. `story` / `allow_pick` / `regenerate_share`); `DELETE /api/items/<id>`, `/api/collections/<id>`, `/api/me`

Admin: `GET /api/items?scope=all`, `/api/users`; `POST /api/settings` (incl. `watermark_text`); `PATCH /api/users/<id>`; `DELETE /api/users/<id>`

## Deployment

Expose the local server over HTTPS with Cloudflare Tunnel — no public IP needed:

```bash
cloudflared tunnel --url http://127.0.0.1:8766
```

Register the admin account **first** once it is public. For long-term use, bind a named tunnel to your own domain.

## License

MIT
