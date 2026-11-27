# -*- coding: utf-8 -*-
"""星匣 · 个人内容站（图床 / 博客 / 私密资料柜）
Python 标准库 + SQLite，无第三方依赖。
启动: python server.py  → http://127.0.0.1:8766
"""
import os, re, json, html, time, hashlib, secrets, mimetypes, urllib.parse, cgi, hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime

import imaging

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, 'data', 'site.db')
UPLOAD_DIR = os.path.join(ROOT, 'uploads')
MAX_FILE = 50 * 1024 * 1024
IMAGE_EXT = {'png','jpg','jpeg','gif','webp','svg','bmp','avif'}
FILE_EXT = IMAGE_EXT | {'pdf','doc','docx','xls','xlsx','ppt','pptx','txt','md','zip','rar','7z','mp3','mp4','wav','webm','json','csv','py','js','html','css','xml','yml','yaml','epub','mobi','ttf','woff','woff2'}
SECRET_PATH = os.path.join(ROOT, 'data', 'secret.key')
UNLOCK_TTL = 7 * 24 * 3600
ATTEMPTS = {}

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
CACHE_DIR = os.path.join(ROOT, 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def remove_uploads(names):
    """删除原图及其派生的水印版 / 缩略图。"""
    if isinstance(names, str):
        names = [names]
    for n in names:
        if not n:
            continue
        try:
            os.remove(os.path.join(UPLOAD_DIR, n))
        except OSError:
            pass


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c


import sqlite3


def secret():
    if os.path.isfile(SECRET_PATH):
        with open(SECRET_PATH, 'rb') as f:
            return f.read()
    s = secrets.token_bytes(32)
    with open(SECRET_PATH, 'wb') as f:
        f.write(s)
    return s


def hash_pw(pw):
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt, 200000)
    return salt.hex() + ':' + dk.hex()


def verify_pw(pw, stored):
    try:
        salt, digest = stored.split(':')
        dk = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), bytes.fromhex(salt), 200000)
        return secrets.compare_digest(dk.hex(), digest)
    except Exception:
        return False


def sign(val):
    return hmac.new(secret(), val.encode('utf-8'), hashlib.sha256).hexdigest()


def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE COLLATE NOCASE,
      email TEXT NOT NULL UNIQUE COLLATE NOCASE,
      password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
      bio TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions(
      token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS files(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      original_name TEXT NOT NULL, stored_name TEXT NOT NULL,
      size INTEGER NOT NULL, mime TEXT NOT NULL, ext TEXT NOT NULL,
      uploader_id INTEGER NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(uploader_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS items(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
      tags TEXT NOT NULL DEFAULT '[]', visibility TEXT NOT NULL DEFAULT 'public',
      password TEXT NOT NULL DEFAULT '', file_id INTEGER,
      collection_id INTEGER,
      uploader_id INTEGER NOT NULL, views INTEGER NOT NULL DEFAULT 0,
      downloads INTEGER NOT NULL DEFAULT 0, pinned INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE SET NULL,
      FOREIGN KEY(uploader_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS collections(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
      story TEXT NOT NULL DEFAULT '',
      tags TEXT NOT NULL DEFAULT '[]', visibility TEXT NOT NULL DEFAULT 'public',
      password TEXT NOT NULL DEFAULT '', cover_id INTEGER,
      share_token TEXT, allow_pick INTEGER NOT NULL DEFAULT 1,
      uploader_id INTEGER NOT NULL, views INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(uploader_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS collection_picks(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      collection_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
      visitor_token TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(collection_id, item_id, visitor_token),
      FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE CASCADE,
      FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_items_vis ON items(visibility);
    CREATE INDEX IF NOT EXISTS idx_items_kind ON items(kind);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    ''')
    defaults = {
        'site_name': '星匣', 'site_desc': '把一组照片，变成一本可以发出去的作品集。',
        'owner_name': '星星', 'announcement': '', 'footer': '星匣 · 私人作品集',
        'watermark_text': '仅供预览 · 请勿转用', 'watermark_default': '1',
    }
    for k, v in defaults.items():
        c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', (k, v))
    c.commit()
    # 旧库兼容：先补字段，再建索引
    cols = [r['name'] for r in c.execute('PRAGMA table_info(items)')]
    for name, ddl in (('collection_id', 'INTEGER'), ('exif', "TEXT NOT NULL DEFAULT ''")):
        if name not in cols:
            c.execute('ALTER TABLE items ADD COLUMN %s %s' % (name, ddl))
    c.execute('CREATE INDEX IF NOT EXISTS idx_items_col ON items(collection_id)')
    fcols = [r['name'] for r in c.execute('PRAGMA table_info(files)')]
    for name, ddl in (('wm_name', "TEXT NOT NULL DEFAULT ''"), ('thumb_name', "TEXT NOT NULL DEFAULT ''"),
                      ('width', 'INTEGER NOT NULL DEFAULT 0'), ('height', 'INTEGER NOT NULL DEFAULT 0')):
        if name not in fcols:
            c.execute('ALTER TABLE files ADD COLUMN %s %s' % (name, ddl))
    ccols = [r['name'] for r in c.execute('PRAGMA table_info(collections)')]
    for name, ddl in (
        ('story', "TEXT NOT NULL DEFAULT ''"),
        ('share_token', 'TEXT'),
        ('allow_pick', 'INTEGER NOT NULL DEFAULT 1'),
        ('accent', "TEXT NOT NULL DEFAULT ''"),
    ):
        if name not in ccols:
            c.execute('ALTER TABLE collections ADD COLUMN %s %s' % (name, ddl))
    for r in c.execute("SELECT id FROM collections WHERE share_token IS NULL OR share_token=''"):
        c.execute('UPDATE collections SET share_token=? WHERE id=?', (secrets.token_urlsafe(9), r['id']))
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_collections_share ON collections(share_token)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_picks_col ON collection_picks(collection_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_picks_visitor ON collection_picks(visitor_token)')
    c.commit(); c.close()


# ---------------- Markdown ----------------
def md_inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', lambda m: '<code>' + m.group(1) + '</code>', s)
    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', lambda m: '<img src="%s" alt="%s" loading="lazy">' % (html.escape(m.group(2), quote=True), m.group(1)), s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', lambda m: '<a href="%s" target="_blank" rel="noopener">%s</a>' % (html.escape(m.group(2), quote=True), m.group(1)), s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', s)
    s = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', s)
    return s


def md_render(text):
    if not text:
        return ''
    lines = text.replace('\r\n', '\n').split('\n')
    out, i, in_code, code_buf, in_list = [], 0, False, [], False
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('```'):
            if in_code:
                out.append('<pre><code>' + html.escape('\n'.join(code_buf)) + '</code></pre>')
                code_buf, in_code = [], False
            else:
                if in_list: out.append('</ul>'); in_list = False
                in_code = True
            i += 1; continue
        if in_code:
            code_buf.append(line); i += 1; continue
        st = line.strip()
        if not st:
            if in_list: out.append('</ul>'); in_list = False
            i += 1; continue
        m = re.match(r'^(#{1,6})\s+(.*)$', st)
        if m:
            if in_list: out.append('</ul>'); in_list = False
            lv = len(m.group(1)); out.append('<h%d>%s</h%d>' % (lv, md_inline(m.group(2)), lv))
            i += 1; continue
        if re.match(r'^[-*]\s+', st):
            if not in_list: out.append('<ul>'); in_list = True
            out.append('<li>' + md_inline(re.sub(r'^[-*]\s+', '', st)) + '</li>')
            i += 1; continue
        if in_list: out.append('</ul>'); in_list = False
        if st.startswith('>'):
            out.append('<blockquote>' + md_inline(st.lstrip('> ')) + '</blockquote>')
            i += 1; continue
        if re.match(r'^(-{3,}|\*{3,})$', st):
            out.append('<hr>'); i += 1; continue
        para = [st]
        while i + 1 < len(lines) and lines[i+1].strip() and not re.match(r'^(#{1,6})\s|^[-*]\s|^>|^-{3,}$|^\s*```', lines[i+1].strip()):
            i += 1; para.append(lines[i].strip())
        out.append('<p>' + md_inline(' '.join(para)) + '</p>')
        i += 1
    if in_code: out.append('<pre><code>' + html.escape('\n'.join(code_buf)) + '</code></pre>')
    if in_list: out.append('</ul>')
    return '\n'.join(out)


class Handler(BaseHTTPRequestHandler):
    server_version = 'Xingxia/1.0'

    def log_message(self, fmt, *args):
        pass

    def send_json(self, code, obj, headers=None):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers(); self.wfile.write(data)

    def body_json(self):
        try:
            n = int(self.headers.get('Content-Length', '0'))
            return json.loads(self.rfile.read(n).decode('utf-8') or '{}')
        except Exception:
            return {}

    def cookie(self, name):
        for part in self.headers.get('Cookie', '').split(';'):
            if part.strip().startswith(name + '='):
                return part.strip().split('=', 1)[1]
        return ''

    def current_user(self):
        token = self.cookie('xx_token')
        if not token: return None
        c = db()
        try:
            return c.execute('''SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                                WHERE s.token=?''', (token,)).fetchone()
        finally:
            c.close()

    def require_user(self):
        u = self.current_user()
        if not u: self.send_json(401, {'error': '请先登录'})
        return u

    def require_admin(self):
        u = self.current_user()
        if not u: self.send_json(401, {'error': '请先登录'})
        elif u['role'] != 'admin': self.send_json(403, {'error': '需要管理员权限'})
        return u if u and u['role'] == 'admin' else None

    def unlocked(self, iid):
        return secrets.compare_digest(self.cookie('unlock_%d' % iid), sign('unlock:%d' % iid))

    def can_view(self, row, c):
        u = self.current_user()
        if u and (u['role'] == 'admin' or u['id'] == row['uploader_id']): return True
        if row['visibility'] == 'public': return True
        if row['visibility'] == 'password': return self.unlocked(row['id'])
        return False

    def item_out(self, row, c, detail=False):
        d = dict(row)
        d['tags'] = json.loads(d.get('tags') or '[]')
        d.pop('password', None)
        owner = c.execute('SELECT username FROM users WHERE id=?', (row['uploader_id'],)).fetchone()
        d['owner'] = owner['username'] if owner else ''
        f = None
        if row['file_id']:
            f = c.execute('SELECT * FROM files WHERE id=?', (row['file_id'],)).fetchone()
        d['filename'] = f['original_name'] if f else ''
        d['ext'] = f['ext'] if f else ''
        d['size'] = f['size'] if f else 0
        d['media_url'] = '/api/media?id=%d' % row['file_id'] if row['file_id'] else ''
        d['thumb_url'] = (('/api/media?id=%d&size=s' % row['file_id']) if (f and f['thumb_name']) else d['media_url'])
        d['has_file'] = bool(row['file_id'])
        d['width'] = (f['width'] if f else 0) or 0
        d['height'] = (f['height'] if f else 0) or 0
        d['watermarked'] = bool(f and f['wm_name'])
        try:
            d['exif'] = json.loads(row['exif'] or '{}')
        except Exception:
            d['exif'] = {}
        if detail:
            u = self.current_user()
            priv = bool(u and (u['role'] == 'admin' or u['id'] == row['uploader_id']))
            d['can_raw'] = priv
            d['raw_url'] = ('/api/media?id=%d&raw=1' % row['file_id']) if (priv and row['file_id']) else ''
        d['locked'] = row['visibility'] == 'password'
        if row['kind'] == 'post' and detail:
            d['html'] = md_render(row['body'])
        if not detail:
            # 列表保留正文摘要（用于文章卡片预览），控制长度
            d['body'] = (row['body'] or '')[:160] if row['kind']=='post' else ''
        return d

    def visitor_token(self):
        tok = self.cookie('xx_visitor')
        return tok if tok and re.fullmatch(r'[A-Za-z0-9_-]{16,64}', tok) else ''

    def collection_out(self, row, c):
        d = dict(row)
        d.pop('password', None)
        d['tags'] = json.loads(d.get('tags') or '[]')
        d['story'] = row['story'] or ''
        d['allow_pick'] = bool(row['allow_pick'])
        owner = c.execute('SELECT username FROM users WHERE id=?', (row['uploader_id'],)).fetchone()
        d['owner'] = owner['username'] if owner else ''
        all_items = c.execute('SELECT * FROM items WHERE collection_id=? ORDER BY id', (row['id'],)).fetchall()
        visible = [i for i in all_items if self.can_view(i, c)]
        d['count'] = len(visible)
        cover = None
        if row['cover_id']:
            picked = c.execute('SELECT i.*,f.stored_name,f.thumb_name FROM items i LEFT JOIN files f ON f.id=i.file_id WHERE i.id=?', (row['cover_id'],)).fetchone()
            if picked and self.can_view(picked, c) and picked['stored_name']:
                cover = picked
        if not cover:
            for i in all_items:
                if i['kind'] != 'image' or not i['file_id'] or not self.can_view(i, c):
                    continue
                f = c.execute('SELECT stored_name, thumb_name FROM files WHERE id=?', (i['file_id'],)).fetchone()
                if f and f['stored_name']:
                    cover = {'file_id': i['file_id'], 'thumb_name': f['thumb_name']}
                    break
        d['cover_url'] = '/api/media?id=%d' % cover['file_id'] if cover else ''
        d['cover_thumb_url'] = (('/api/media?id=%d&size=s' % cover['file_id'])
                                if (cover and cover['thumb_name']) else d['cover_url'])
        d['locked'] = row['visibility'] == 'password'
        try:
            d['accent'] = row['accent'] or '#d4af7a'
        except Exception:
            d['accent'] = '#d4af7a'
        u = self.current_user()
        can_edit = bool(u and (u['role'] == 'admin' or u['id'] == row['uploader_id']))
        d['can_edit'] = can_edit
        if not can_edit:
            d.pop('share_token', None)
            d['share_url'] = ''
        else:
            d['share_url'] = '/s/%s' % row['share_token'] if row['share_token'] else ''
        visible_ids = {i['id'] for i in visible}
        pick_rows = c.execute('SELECT item_id, COUNT(*) n FROM collection_picks WHERE collection_id=? GROUP BY item_id', (row['id'],)).fetchall()
        d['picks'] = sum(r['n'] for r in pick_rows if r['item_id'] in visible_ids)
        return d

    def collection_detail_out(self, row, c):
        d = self.collection_out(row, c)
        d['story_html'] = md_render(row['story'] or '')
        items = c.execute('SELECT * FROM items WHERE collection_id=? ORDER BY id', (row['id'],)).fetchall()
        counts = {r['item_id']: r['n'] for r in c.execute(
            'SELECT item_id, COUNT(*) n FROM collection_picks WHERE collection_id=? GROUP BY item_id', (row['id'],))}
        vt = self.visitor_token()
        mine = set()
        if vt:
            mine = {r['item_id'] for r in c.execute(
                'SELECT item_id FROM collection_picks WHERE collection_id=? AND visitor_token=?', (row['id'], vt))}
        out = []
        for i in items:
            if not self.can_view(i, c):
                continue
            x = self.item_out(i, c)
            x['picks'] = counts.get(i['id'], 0)
            x['picked'] = i['id'] in mine
            out.append(x)
        d['items'] = out
        d['pick_total'] = sum(x['picks'] for x in out)
        d['my_pick_total'] = sum(1 for x in out if x['picked'])
        return d

    def can_view_collection(self, row, c):
        u = self.current_user()
        if u and (u['role'] == 'admin' or u['id'] == row['uploader_id']): return True
        if row['visibility'] == 'public': return True
        if row['visibility'] == 'password':
            return secrets.compare_digest(self.cookie('unlock_c%d' % row['id']), sign('unlock:c%d' % row['id']))
        return False

    def serve_static(self, path):
        rel = path.lstrip('/') or 'index.html'
        full = os.path.normpath(os.path.join(ROOT, rel))
        if not full.startswith(ROOT): return self.send_json(403, {'error': '禁止访问'})
        if not os.path.isfile(full): return self.send_json(404, {'error': '页面不存在'})
        mime = mimetypes.guess_type(full)[0] or 'application/octet-stream'
        if mime.startswith('text/') or mime in ('application/javascript', 'application/json'):
            mime += '; charset=utf-8'
        with open(full, 'rb') as f: data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers(); self.wfile.write(data)

    # ---------- GET ----------
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path
        c = db()
        try:
            if p == '/api/config':
                settings = {r['key']: r['value'] for r in c.execute('SELECT * FROM settings')}
                user = self.current_user()
                settings['me'] = self.item_out_me(user) if user else None
                settings['stats'] = {
                    'items': c.execute('SELECT COUNT(*) n FROM items').fetchone()['n'],
                    'images': c.execute("SELECT COUNT(*) n FROM items WHERE kind='image'").fetchone()['n'],
                    'posts': c.execute("SELECT COUNT(*) n FROM items WHERE kind='post'").fetchone()['n'],
                    'files': c.execute("SELECT COUNT(*) n FROM items WHERE kind='file'").fetchone()['n'],
                    'collections': c.execute('SELECT COUNT(*) n FROM collections').fetchone()['n'],
                    'picks': c.execute('SELECT COUNT(*) n FROM collection_picks').fetchone()['n'],
                }
                feat = c.execute("SELECT share_token FROM collections WHERE visibility='public' AND share_token IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
                settings['featured_share'] = '/s/%s' % feat['share_token'] if feat else ''
                return self.send_json(200, settings)
            if p == '/api/collections':
                me = self.current_user()
                sql = 'SELECT * FROM collections WHERE 1=1'; args = []
                scope = q.get('scope', ['public'])[0]
                if scope == 'mine':
                    if not me: return self.send_json(401, {'error': '请先登录'})
                    sql += ' AND uploader_id=?'; args.append(me['id'])
                elif not (me and me['role']=='admin'):
                    sql += " AND visibility='public'"
                sql += ' ORDER BY id DESC'
                rows = c.execute(sql, args).fetchall()
                return self.send_json(200, {'collections':[self.collection_out(r,c) for r in rows]})
            if p.startswith('/api/share/'):
                token = p.split('/')[-1]
                row = c.execute('SELECT * FROM collections WHERE share_token=?', (token,)).fetchone()
                if not row: return self.send_json(404, {'error': '分享链接不存在或已失效'})
                if not self.can_view_collection(row, c):
                    return self.send_json(401, {'error': ' locked', 'id': row['id']} if row['visibility']=='password' else {'error': '无权访问'})
                c.execute('UPDATE collections SET views=views+1 WHERE id=?', (row['id'],)); c.commit()
                d = self.collection_detail_out(row, c)
                d['share_mode'] = True
                return self.send_json(200, {'collection': d})
            if re.match(r'^/api/collections/\d+/poster$', p):
                cid = p.split('/')[-2]
                row = c.execute('SELECT * FROM collections WHERE id=?', (cid,)).fetchone()
                if not row: return self.send_json(404, {'error': '作品集不存在'})
                if not self.can_view_collection(row, c):
                    return self.send_json(401, {'error': '无权访问'})
                me = self.current_user()
                if not me or (me['role'] != 'admin' and me['id'] != row['uploader_id']):
                    return self.send_json(403, {'error': '只有作者可以生成长图'})
                shots = [i for i in c.execute(
                    "SELECT * FROM items WHERE collection_id=? AND kind='image' ORDER BY id", (cid,)).fetchall()
                    if self.can_view(i, c)]
                if not shots: return self.send_json(400, {'error': '这个作品集还没有图片'})
                fmap = {}
                for i in shots:
                    if i['file_id']:
                        fr = c.execute('SELECT stored_name FROM files WHERE id=?', (i['file_id'],)).fetchone()
                        if fr: fmap[i['id']] = os.path.join(UPLOAD_DIR, fr['stored_name'])
                if not fmap: return self.send_json(400, {'error': '图片文件缺失'})
                cover_path = fmap.get(row['cover_id']) or list(fmap.values())[0]
                hkey = hashlib.md5(('%s|%s|%s|%s' % (row['updated_at'], row['title'], row['story'], len(fmap))).encode()).hexdigest()[:12]
                out = os.path.join(CACHE_DIR, 'poster_%s_%s.jpg' % (cid, hkey))
                if not os.path.isfile(out):
                    cfg = {r['key']: r['value'] for r in c.execute('SELECT key,value FROM settings')}
                    story_txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', md_render(row['story'] or ''))).strip()
                    tags = json.loads(row['tags'] or '[]')
                    subtitle = ' · '.join(tags[:3] + ['%d 张' % len(fmap)])
                    host = (self.headers.get('Host') or '127.0.0.1:8766').strip()
                    footer = '%s  ·  %s/s/%s' % (cfg.get('site_name') or '星匣', host, row['share_token'] or '')
                    if not imaging.build_poster(out, cover_path, row['title'], subtitle, story_txt[:180],
                                                list(fmap.values())[:9], row['accent'] or '#d4af7a', footer):
                        return self.send_json(500, {'error': '长图生成失败'})
                with open(out, 'rb') as fp: data = fp.read()
                fn = urllib.parse.quote('%s-作品集.jpg' % (row['title'] or 'poster'))
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Content-Disposition', "attachment; filename*=UTF-8''%s" % fn)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers(); self.wfile.write(data)
                return
            if re.match(r'^/api/collections/\d+/picks\.csv$', p):
                cid = p.split('/')[-2]
                row = c.execute('SELECT * FROM collections WHERE id=?', (cid,)).fetchone()
                if not row: return self.send_json(404, {'error': '作品集不存在'})
                me = self.current_user()
                if not me or (me['role'] != 'admin' and me['id'] != row['uploader_id']):
                    return self.send_json(403, {'error': '只有作者可以导出选片清单'})
                rows = c.execute('''SELECT i.id, i.title, f.original_name, COUNT(p.id) n
                                    FROM items i LEFT JOIN files f ON f.id=i.file_id
                                    LEFT JOIN collection_picks p ON p.item_id=i.id AND p.collection_id=?
                                    WHERE i.collection_id=? GROUP BY i.id ORDER BY n DESC, i.id''', (cid, cid)).fetchall()
                def cell(v):
                    return '"%s"' % str(v or '').replace('"', '""')
                buf = '\ufeff序号,标题,文件名,被选次数,访问地址\n'
                for idx, r in enumerate(rows, 1):
                    buf += ','.join([str(idx), cell(r['title']), cell(r['original_name']), str(r['n']),
                                     cell('item.html?id=%d' % r['id'])]) + '\n'
                data = buf.encode('utf-8')
                fn = urllib.parse.quote('%s-选片清单.csv' % (row['title'] or 'picks'))
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Content-Disposition', "attachment; filename*=UTF-8''%s" % fn)
                self.end_headers(); self.wfile.write(data)
                return
            if p.startswith('/api/collections/'):
                cid = p.split('/')[-1]
                row = c.execute('SELECT * FROM collections WHERE id=?', (cid,)).fetchone()
                if not row: return self.send_json(404, {'error': '作品集不存在'})
                if not self.can_view_collection(row, c):
                    return self.send_json(401, {'error': ' locked'} if row['visibility']=='password' else {'error': '无权访问'})
                c.execute('UPDATE collections SET views=views+1 WHERE id=?', (cid,)); c.commit()
                d = self.collection_detail_out(row, c)
                return self.send_json(200, {'collection': d})
            if p == '/api/items':
                kind = q.get('kind', [''])[0]
                tag = q.get('tag', [''])[0]
                kw = q.get('q', [''])[0].strip()
                scope = q.get('scope', ['public'])[0]
                me = self.current_user()
                sql, args = 'SELECT * FROM items WHERE 1=1', []
                if scope == 'mine':
                    if not me: return self.send_json(401, {'error': '请先登录'})
                    sql += ' AND uploader_id=?'; args.append(me['id'])
                elif scope == 'all':
                    if not me or me['role'] != 'admin': return self.send_json(403, {'error': '需要管理员权限'})
                else:
                    if not (me and me['role'] == 'admin'):
                        sql += " AND visibility='public'"
                if kind: sql += ' AND kind=?'; args.append(kind)
                col = q.get('collection',[''])[0]
                if col: sql += ' AND collection_id=?'; args.append(col)
                if tag:
                    sql += ' AND tags LIKE ?'; args.append('%' + tag + '%')
                if kw:
                    sql += ' AND (title LIKE ? OR body LIKE ? OR tags LIKE ?)'
                    args += ['%' + kw + '%'] * 3
                sql += ' ORDER BY pinned DESC, id DESC'
                rows = c.execute(sql, args).fetchall()
                out = [self.item_out(r, c) for r in rows]
                return self.send_json(200, {'items': out})
            if p == '/api/tags':
                tags = {}
                for r in c.execute("SELECT tags FROM items WHERE visibility='public'"):
                    for t in json.loads(r['tags'] or '[]'):
                        tags[t] = tags.get(t, 0) + 1
                return self.send_json(200, {'tags': [{'name': k, 'count': v} for k, v in sorted(tags.items(), key=lambda x: -x[1])]})
            if p.startswith('/api/items/'):
                iid = p.split('/')[-1]
                row = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
                if not row: return self.send_json(404, {'error': '内容不存在'})
                if not self.can_view(row, c):
                    return self.send_json(401, {'error': ' locked'} if row['visibility'] == 'password' else {'error': '需要登录或权限不足'})
                c.execute('UPDATE items SET views=views+1 WHERE id=?', (iid,)); c.commit()
                d = self.item_out(row, c, detail=True)
                d['can_edit'] = bool(self.current_user() and (self.current_user()['role'] == 'admin' or self.current_user()['id'] == row['uploader_id']))
                return self.send_json(200, {'item': d})
            if p == '/api/media':
                fid = q.get('id', [''])[0]
                f = c.execute('SELECT * FROM files WHERE id=?', (fid,)).fetchone()
                if not f: return self.send_json(404, {'error': '文件不存在'})
                row = c.execute('SELECT * FROM items WHERE file_id=? LIMIT 1', (fid,)).fetchone()
                if row and not self.can_view(row, c):
                    return self.send_json(403, {'error': '无权访问'})
                u = self.current_user()
                priv = bool(u and (u['role'] == 'admin' or u['id'] == f['uploader_id']))
                if not row and not priv:
                    return self.send_json(403, {'error': '无权访问'})
                # 访客/其他用户拿到的是带水印的样片，作者与管理员可加 raw=1 取原图
                want_raw = q.get('raw', [''])[0] == '1'
                use_wm = (not priv or not want_raw) and bool(f['wm_name'])
                fname = f['wm_name'] if use_wm else f['stored_name']
                ctype = 'image/jpeg' if use_wm else f['mime']
                # 列表用小缩略图：加载快，也不会整页都是水印显得脏
                if q.get('size', [''])[0] == 's' and f['thumb_name']:
                    fname = f['thumb_name']; ctype = 'image/jpeg'; use_wm = False
                path = os.path.join(UPLOAD_DIR, fname)
                if not os.path.isfile(path): return self.send_json(404, {'error': '文件已丢失'})
                with open(path, 'rb') as fp: data = fp.read()
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'private, max-age=300')
                self.send_header('X-Watermark', '1' if use_wm else '0')
                self.end_headers(); self.wfile.write(data)
                return
            if p == '/api/download':
                user = self.require_user()
                if not user: return
                iid = q.get('id', [''])[0]
                row = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
                if not row or not row['file_id']: return self.send_json(404, {'error': '没有可下载文件'})
                if not self.can_view(row, c): return self.send_json(403, {'error': '无权访问'})
                f = c.execute('SELECT * FROM files WHERE id=?', (row['file_id'],)).fetchone()
                priv = (user['role'] == 'admin' or user['id'] == f['uploader_id'])
                src_name, dl_name, ctype = f['stored_name'], f['original_name'], f['mime']
                # 图片：非作者下载到的是水印样片，原图只归作者
                if row['kind'] == 'image' and not priv and f['wm_name']:
                    src_name = f['wm_name']; ctype = 'image/jpeg'
                    dl_name = os.path.splitext(f['original_name'])[0] + '-样片.jpg'
                path = os.path.join(UPLOAD_DIR, src_name)
                if not os.path.isfile(path): return self.send_json(404, {'error': '文件已丢失'})
                c.execute('UPDATE items SET downloads=downloads+1 WHERE id=?', (iid,)); c.commit()
                with open(path, 'rb') as fp: data = fp.read()
                name = urllib.parse.quote(dl_name)
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Disposition', "attachment; filename*=UTF-8''%s" % name)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers(); self.wfile.write(data)
                return
            if p == '/api/users':
                admin = self.require_admin()
                if not admin: return
                rows = c.execute('''SELECT u.id,u.username,u.email,u.role,u.bio,u.created_at,
                    (SELECT COUNT(*) FROM items i WHERE i.uploader_id=u.id) items
                    FROM users u ORDER BY u.id''').fetchall()
                return self.send_json(200, {'users': [dict(r) for r in rows]})
            if p.startswith('/api/users/'):
                if not self.current_user(): return self.send_json(401, {'error': '请先登录'})
                name = p.split('/')[-1]
                r = c.execute('SELECT id,username,role,bio,created_at FROM users WHERE username=? OR id=?', (name, name)).fetchone()
                if not r: return self.send_json(404, {'error': '用户不存在'})
                d = dict(r)
                d['items'] = c.execute("SELECT COUNT(*) n FROM items WHERE uploader_id=? AND visibility='public'", (r['id'],)).fetchone()['n']
                return self.send_json(200, {'user': d})
            if p.startswith('/s/') and len(p) > 3:
                return self.serve_static('/collection.html')
            return self.serve_static(p)
        finally:
            c.close()

    def item_out_me(self, u):
        return {'id': u['id'], 'username': u['username'], 'email': u['email'], 'role': u['role'], 'bio': u['bio']}

    # ---------- POST ----------
    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        c = db()
        try:
            if p == '/api/register':
                d = self.body_json()
                username = (d.get('username') or '').strip(); email = (d.get('email') or '').strip()
                password = d.get('password') or ''
                if not re.fullmatch(r'[\w\u4e00-\u9fa5-]{2,24}', username):
                    return self.send_json(400, {'error': '用户名需 2-24 位（字母数字中文下划线）'})
                if '@' not in email: return self.send_json(400, {'error': '邮箱格式不正确'})
                if len(password) < 6: return self.send_json(400, {'error': '密码至少 6 位'})
                if c.execute('SELECT 1 FROM users WHERE username=? OR email=?', (username, email)).fetchone():
                    return self.send_json(400, {'error': '用户名或邮箱已注册'})
                role = 'admin' if c.execute('SELECT COUNT(*) n FROM users').fetchone()['n'] == 0 else 'user'
                c.execute('INSERT INTO users(username,email,password,role,created_at) VALUES(?,?,?,?,?)',
                          (username, email, hash_pw(password), role, now()))
                uid = c.execute('SELECT last_insert_rowid() id').fetchone()['id']
                token = secrets.token_urlsafe(32)
                c.execute('INSERT INTO sessions VALUES(?,?,?)', (token, uid, now()))
                c.commit()
                return self.send_json(200, {'ok': True, 'user': {'id': uid, 'username': username, 'role': role},
                                            'first_admin': role == 'admin'},
                                       {'Set-Cookie': 'xx_token=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d' % (token, 30*86400)})
            if p == '/api/login':
                d = self.body_json(); account = (d.get('account') or '').strip(); password = d.get('password') or ''
                r = c.execute('SELECT * FROM users WHERE username=? OR email=?', (account, account)).fetchone()
                if not r or not verify_pw(password, r['password']): return self.send_json(401, {'error': '账号或密码错误'})
                token = secrets.token_urlsafe(32)
                c.execute('INSERT INTO sessions VALUES(?,?,?)', (token, r['id'], now())); c.commit()
                return self.send_json(200, {'ok': True, 'user': self.item_out_me(r)},
                                       {'Set-Cookie': 'xx_token=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d' % (token, 30*86400)})
            if p == '/api/logout':
                token = self.cookie('xx_token')
                if token: c.execute('DELETE FROM sessions WHERE token=?', (token,)); c.commit()
                return self.send_json(200, {'ok': True},
                                       {'Set-Cookie': 'xx_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax'})
            if p == '/api/unlock':
                _d = self.body_json()
                iid = (_d.get('id') or '')
                password = (_d.get('password') or '')
                target = _d.get('type')
                ip = self.client_address[0]
                bucket = [t for t in ATTEMPTS.get(ip, []) if time.time() - t < 600]
                if len(bucket) >= 8: return self.send_json(429, {'error': '尝试次数过多，请 10 分钟后再试'})
                ATTEMPTS[ip] = bucket + [time.time()]
                is_col = target == 'collection'
                row = None
                if target == 'collection':
                    row = c.execute('SELECT * FROM collections WHERE id=?', (iid,)).fetchone()
                elif target == 'item':
                    row = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
                else:
                    row = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
                    if not row:
                        row = c.execute('SELECT * FROM collections WHERE id=?', (iid,)).fetchone()
                        is_col = bool(row)
                if not row: return self.send_json(404, {'error': '内容不存在'})
                if row['visibility'] != 'password': return self.send_json(400, {'error': '该内容不需要密码'})
                if not verify_pw(password, row['password']): return self.send_json(401, {'error': '密码错误'})
                prefix = 'c' if is_col else ''
                token = sign('unlock:%s%s' % (prefix, row['id']))
                return self.send_json(200, {'ok': True},
                                       {'Set-Cookie': 'unlock_%s%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d' % (prefix, row['id'], token, UNLOCK_TTL)})
            if p == '/api/collections':
                user = self.require_user()
                if not user: return
                d = self.body_json()
                title = (d.get('title') or '').strip()
                vis = d.get('visibility') or 'public'
                if not title: return self.send_json(400, {'error': '请填写作品集名称'})
                if vis not in ('public','private','password'): return self.send_json(400, {'error': '可见性无效'})
                pw = (d.get('password') or '').strip()
                if vis=='password' and len(pw)<4: return self.send_json(400, {'error': '访问密码至少 4 位'})
                raw_tags = d.get('tags')
                if isinstance(raw_tags, str):
                    raw_tags = [x.strip() for x in raw_tags.split(',') if x.strip()]
                elif not isinstance(raw_tags, list):
                    raw_tags = []
                tags = [str(x).strip() for x in raw_tags if str(x).strip()][:8]
                ts = now(); share_token = secrets.token_urlsafe(9)
                c.execute('''INSERT INTO collections(title,description,story,tags,visibility,password,share_token,allow_pick,uploader_id,created_at,updated_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                          (title[:160], (d.get('description') or '')[:500], (d.get('story') or '')[:20000],
                           json.dumps(tags,ensure_ascii=False), vis,
                           hash_pw(pw) if vis=='password' else '', share_token, 1 if d.get('allow_pick', True) else 0,
                           user['id'], ts, ts))
                c.commit()
                cid = c.execute('SELECT last_insert_rowid() id').fetchone()['id']
                return self.send_json(200, {'ok':True, 'id':cid, 'share_url':'/s/%s' % share_token})
            if p.startswith('/api/collections/') and p.endswith('/pick'):
                parts = p.split('/')
                cid = parts[-2]
                row = c.execute('SELECT * FROM collections WHERE id=?', (cid,)).fetchone()
                if not row: return self.send_json(404, {'error': '作品集不存在'})
                if not self.can_view_collection(row, c):
                    return self.send_json(401, {'error': ' locked'} if row['visibility']=='password' else {'error': '无权访问'})
                if not row['allow_pick']: return self.send_json(403, {'error': '作者未开放选片'})
                d = self.body_json()
                try: item_id = int(d.get('item_id'))
                except (TypeError, ValueError): return self.send_json(400, {'error': '参数无效'})
                item = c.execute('SELECT * FROM items WHERE id=? AND collection_id=?', (item_id, cid)).fetchone()
                if not item or not self.can_view(item, c): return self.send_json(404, {'error': '内容不在作品集中'})
                vt = self.visitor_token(); headers = None
                if not vt:
                    vt = secrets.token_urlsafe(18)
                    headers = {'Set-Cookie': 'xx_visitor=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d' % (vt, 365*86400)}
                old = c.execute('SELECT id FROM collection_picks WHERE collection_id=? AND item_id=? AND visitor_token=?',
                                (cid, item_id, vt)).fetchone()
                if old:
                    c.execute('DELETE FROM collection_picks WHERE id=?', (old['id'],)); picked = False
                else:
                    c.execute('INSERT INTO collection_picks(collection_id,item_id,visitor_token,created_at) VALUES(?,?,?,?)',
                              (cid, item_id, vt, now())); picked = True
                c.commit()
                item_picks = c.execute('SELECT COUNT(*) n FROM collection_picks WHERE collection_id=? AND item_id=?',
                                       (cid, item_id)).fetchone()['n']
                total = c.execute('SELECT COUNT(*) n FROM collection_picks WHERE collection_id=?', (cid,)).fetchone()['n']
                return self.send_json(200, {'ok': True, 'picked': picked, 'item_picks': item_picks, 'total': total}, headers)
            if p == '/api/post':
                user = self.require_user()
                if not user: return
                d = self.body_json()
                title = (d.get('title') or '').strip(); body = d.get('body') or ''
                vis = d.get('visibility') or 'public'
                if vis not in ('public', 'private', 'password'): return self.send_json(400, {'error': '可见性无效'})
                if not title: return self.send_json(400, {'error': '请填写标题'})
                pw = (d.get('password') or '').strip()
                if vis == 'password' and len(pw) < 4: return self.send_json(400, {'error': '访问密码至少 4 位'})
                tags = [str(x).strip() for x in (d.get('tags') if isinstance(d.get('tags'), list) else []) if str(x).strip()][:8]
                ts = now()
                c.execute('''INSERT INTO items(kind,title,body,tags,visibility,password,uploader_id,created_at,updated_at)
                             VALUES('post',?,?,?,?,?,?,?,?)''',
                          (title[:160], body, json.dumps(tags, ensure_ascii=False), vis,
                           hash_pw(pw) if vis == 'password' else '', user['id'], ts, ts))
                c.commit()
                return self.send_json(200, {'ok': True, 'id': c.execute('SELECT last_insert_rowid() id').fetchone()['id']})
            if p == '/api/upload':
                user = self.require_user()
                if not user: return
                ctype = self.headers.get('Content-Type', '')
                if 'multipart/form-data' not in ctype: return self.send_json(400, {'error': '请使用表单上传'})
                fs = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                      environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': ctype,
                                               'CONTENT_LENGTH': self.headers.get('Content-Length', '0')})
                def val(k):
                    v = fs.getfirst(k, '')
                    return v if isinstance(v, str) else ''
                title = val('title').strip()
                kind = val('kind')
                vis = val('visibility') or 'public'
                if kind not in ('image', 'file'): return self.send_json(400, {'error': '类型无效'})
                if vis not in ('public', 'private', 'password'): return self.send_json(400, {'error': '可见性无效'})
                pw = val('password').strip()
                if vis == 'password' and len(pw) < 4: return self.send_json(400, {'error': '访问密码至少 4 位'})
                # 多文件：同名字段重复出现。cgi.FieldStorage 的 getlist 会返回原始 bytes，
                # 需要用 fs['file'] 才能拿到 FieldStorage（含 filename）。
                raw_files = fs['file'] if 'file' in fs else []
                files = raw_files if isinstance(raw_files, list) else [raw_files]
                files = [f for f in files if getattr(f, 'filename', None)]
                if not files: return self.send_json(400, {'error': '请选择文件'})
                if len(files) > 60: return self.send_json(400, {'error': '一次最多上传 60 个文件'})

                # 作品集处理：优先用已有 collection_id，否则按 new_collection 新建
                col_id = val('collection_id').strip()
                new_col = val('new_collection').strip()
                if new_col:
                    ts0 = now()
                    ctags = [x.strip() for x in val('collection_tags').split(',') if x.strip()][:8]
                    c.execute('''INSERT INTO collections(title,description,story,tags,visibility,password,share_token,allow_pick,uploader_id,created_at,updated_at)
                                 VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                              (new_col[:160], val('collection_desc')[:500], val('collection_story')[:20000],
                               json.dumps(ctags,ensure_ascii=False), vis,
                               hash_pw(pw) if vis=='password' else '', secrets.token_urlsafe(9), 1,
                               user['id'], ts0, ts0))
                    col_id = str(c.execute('SELECT last_insert_rowid() id').fetchone()['id'])
                if col_id:
                    cr = c.execute('SELECT * FROM collections WHERE id=?', (col_id,)).fetchone()
                    if not cr or cr['uploader_id']!=user['id'] and user['role']!='admin':
                        return self.send_json(400, {'error': '作品集不存在或无权使用'})

                tags = [x.strip() for x in val('tags').split(',') if x.strip()][:8]
                allowed = IMAGE_EXT if kind == 'image' else FILE_EXT
                cfg = {r['key']: r['value'] for r in c.execute('SELECT key,value FROM settings')}
                wm_on = str(val('watermark') or '1').lower() not in ('0', 'false', 'off', 'no')
                wm_text = ''
                if wm_on and kind == 'image':
                    wm_text = (val('watermark_text').strip() or cfg.get('watermark_text') or '').strip()[:40]
                ids, first_file_id = [], None
                for idx, item in enumerate(files):
                    filename = os.path.basename(str(item.filename))
                    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                    if ext not in allowed: continue
                    data = item.file.read(MAX_FILE + 1)
                    if len(data) > MAX_FILE: continue
                    stored = secrets.token_hex(16) + '.' + ext
                    src_path = os.path.join(UPLOAD_DIR, stored)
                    with open(src_path, 'wb') as f: f.write(data)
                    mime = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                    wm_name, thumb_name, dw, dh, exif_json = '', '', 0, 0, ''
                    if ext in ('jpg', 'jpeg', 'png', 'webp', 'bmp', 'avif'):
                        dw, dh = imaging.dimension(src_path)
                        real = imaging.read_exif(src_path)
                        if real:
                            exif_json = json.dumps(real, ensure_ascii=False)
                        tp = os.path.splitext(stored)[0] + '_s.jpg'
                        imaging.make_preview(src_path, os.path.join(UPLOAD_DIR, tp), 720, '')
                        if os.path.isfile(os.path.join(UPLOAD_DIR, tp)):
                            thumb_name = tp
                        if wm_text:
                            prev = os.path.splitext(stored)[0] + '_wm.jpg'
                            _pw, _ph, applied = imaging.make_preview(src_path, os.path.join(UPLOAD_DIR, prev), 1680, wm_text)
                            if applied:
                                wm_name = prev
                    c.execute('''INSERT INTO files(original_name,stored_name,size,mime,ext,uploader_id,created_at,wm_name,thumb_name,width,height)
                                 VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                              (filename, stored, len(data), mime, ext, user['id'], now(), wm_name, thumb_name, dw, dh))
                    fid = c.execute('SELECT last_insert_rowid() id').fetchone()['id']
                    if first_file_id is None: first_file_id = fid
                    # 多文件时标题用文件名，单文件用自定义标题
                    t = title if len(files)==1 and title else filename.rsplit('.',1)[0][:160]
                    ts = now()
                    c.execute('''INSERT INTO items(kind,title,body,tags,visibility,password,file_id,collection_id,exif,uploader_id,created_at,updated_at)
                                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                              (kind, t[:160], val('description'), json.dumps(tags,ensure_ascii=False), vis,
                               hash_pw(pw) if vis=='password' else '', fid, int(col_id) if col_id else None,
                               exif_json, user['id'], ts, ts))
                    ids.append(c.execute('SELECT last_insert_rowid() id').fetchone()['id'])
                if not ids: return self.send_json(400, {'error': '没有可用文件（类型不支持或超过 50MB）'})
                # 设置作品集封面与主题色（取自封面主色）
                if col_id and first_file_id is not None:
                    cid = int(col_id)
                    if new_col:
                        cover = c.execute('SELECT id FROM items WHERE file_id=?', (first_file_id,)).fetchone()
                        if cover: c.execute('UPDATE collections SET cover_id=? WHERE id=?', (cover['id'], cid))
                    cr = c.execute('SELECT accent, cover_id FROM collections WHERE id=?', (cid,)).fetchone()
                    if cr is not None and not cr['accent']:
                        sf = None
                        if cr['cover_id']:
                            sf = c.execute('SELECT f.stored_name FROM items i JOIN files f ON f.id=i.file_id WHERE i.id=?', (cr['cover_id'],)).fetchone()
                        if not sf:
                            sf = c.execute('SELECT stored_name FROM files WHERE id=?', (first_file_id,)).fetchone()
                        acc = imaging.dominant_color(os.path.join(UPLOAD_DIR, sf['stored_name'])) if sf else ''
                        if acc: c.execute('UPDATE collections SET accent=? WHERE id=?', (acc, cid))
                c.commit()
                return self.send_json(200, {'ok': True, 'ids': ids, 'count': len(ids), 'collection_id': int(col_id) if col_id else None,
                                            'id': ids[0]})
            if p == '/api/me/password':
                user = self.require_user()
                if not user: return
                d = self.body_json()
                if not verify_pw(d.get('old') or '', user['password']): return self.send_json(400, {'error': '原密码不正确'})
                new = d.get('new') or ''
                if len(new) < 6: return self.send_json(400, {'error': '新密码至少 6 位'})
                c.execute('UPDATE users SET password=? WHERE id=?', (hash_pw(new), user['id'])); c.commit()
                return self.send_json(200, {'ok': True})
            if p == '/api/me/profile':
                user = self.require_user()
                if not user: return
                d = self.body_json()
                c.execute('UPDATE users SET bio=? WHERE id=?', ((d.get('bio') or '')[:500], user['id'])); c.commit()
                return self.send_json(200, {'ok': True})
            if p == '/api/settings':
                admin = self.require_admin()
                if not admin: return
                d = self.body_json()
                for k in ('site_name', 'site_desc', 'owner_name', 'announcement', 'footer', 'watermark_text'):
                    if k in d:
                        c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', (k, str(d[k])[:1000]))
                c.commit()
                return self.send_json(200, {'ok': True})
            return self.send_json(404, {'error': '接口不存在'})
        finally:
            c.close()

    # ---------- PATCH ----------
    def do_PATCH(self):
        p = urllib.parse.urlparse(self.path).path
        c = db()
        try:
            me = self.require_user()
            if not me: return
            admin = me['role'] == 'admin'
            d = self.body_json()
            if p.startswith('/api/items/'):
                iid = p.split('/')[-1]
                row = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
                if not row: return self.send_json(404, {'error': '内容不存在'})
                if not admin and row['uploader_id'] != me['id']: return self.send_json(403, {'error': '只能编辑自己的内容'})
                vis = d.get('visibility', row['visibility'])
                if vis not in ('public', 'private', 'password'): return self.send_json(400, {'error': '可见性无效'})
                pw = (d.get('password') or '').strip()
                if vis == 'password' and not pw and row['visibility'] != 'password':
                    return self.send_json(400, {'error': '请设置访问密码'})
                if vis == 'password' and pw and len(pw) < 4: return self.send_json(400, {'error': '密码至少 4 位'})
                col_val = row['collection_id']
                if 'collection_id' in d:
                    raw_col = d.get('collection_id')
                    col_val = int(raw_col) if raw_col not in (None, '', 0, '0') else None
                    if col_val is not None:
                        cr = c.execute('SELECT * FROM collections WHERE id=?', (col_val,)).fetchone()
                        if not cr or (cr['uploader_id'] != me['id'] and not admin):
                            return self.send_json(400, {'error': '作品集不存在或无权使用'})
                c.execute('''UPDATE items SET title=?,body=?,tags=?,visibility=?,password=?,pinned=?,collection_id=?,updated_at=?
                             WHERE id=?''',
                          ((d.get('title') or row['title'])[:160], d.get('body', row['body']),
                           json.dumps(d['tags'], ensure_ascii=False) if isinstance(d.get('tags'), list) else row['tags'],
                           vis, hash_pw(pw) if vis == 'password' and pw else (row['password'] if vis == 'password' else ''),
                           1 if d.get('pinned') else 0, col_val, now(), iid))
                c.commit()
                return self.send_json(200, {'ok': True})
            if p.startswith('/api/collections/'):
                cid = p.split('/')[-1]
                row = c.execute('SELECT * FROM collections WHERE id=?', (cid,)).fetchone()
                if not row: return self.send_json(404, {'error': '作品集不存在'})
                if not admin and row['uploader_id'] != me['id']: return self.send_json(403, {'error': '只能编辑自己的作品集'})
                vis = d.get('visibility', row['visibility'])
                if vis not in ('public','private','password'): return self.send_json(400, {'error': '可见性无效'})
                pw = (d.get('password') or '').strip()
                newpw = hash_pw(pw) if vis=='password' and pw else (row['password'] if vis=='password' else '')
                share_token = secrets.token_urlsafe(9) if d.get('regenerate_share') else row['share_token']
                allow_pick = 1 if d.get('allow_pick', row['allow_pick']) else 0
                c.execute('''UPDATE collections SET title=?,description=?,story=?,tags=?,visibility=?,password=?,cover_id=?,share_token=?,allow_pick=?,updated_at=? WHERE id=?''',
                          ((d.get('title') or row['title'])[:160], d.get('description', row['description']),
                           (d.get('story') if 'story' in d else row['story'])[:20000],
                           json.dumps(d['tags'],ensure_ascii=False) if isinstance(d.get('tags'),list) else row['tags'],
                           vis, newpw, d.get('cover_id') or row['cover_id'], share_token, allow_pick, now(), cid))
                if 'visibility' in d:
                    c.execute('UPDATE items SET visibility=?,password=? WHERE collection_id=?', (vis, newpw, cid))
                c.commit()
                return self.send_json(200, {'ok': True, 'share_url':'/s/%s' % share_token})
            if p.startswith('/api/users/'):
                if not admin: return self.send_json(403, {'error': '需要管理员权限'})
                uid = p.split('/')[-1]
                role = d.get('role')
                if role not in ('user', 'admin'): return self.send_json(400, {'error': '角色无效'})
                if int(uid) == me['id'] and role != 'admin': return self.send_json(400, {'error': '不能取消自己的管理员身份'})
                c.execute('UPDATE users SET role=? WHERE id=?', (role, uid)); c.commit()
                return self.send_json(200, {'ok': True})
            return self.send_json(404, {'error': '接口不存在'})
        finally:
            c.close()

    do_PUT = do_PATCH

    # ---------- DELETE ----------
    def do_DELETE(self):
        p = urllib.parse.urlparse(self.path).path
        c = db()
        try:
            me = self.current_user()
            if not me: return self.send_json(401, {'error': '请先登录'})
            admin = me['role'] == 'admin'
            if p == '/api/me':
                names = []
                for r in c.execute('SELECT stored_name, wm_name, thumb_name FROM files WHERE uploader_id=?', (me['id'],)):
                    names += [r['stored_name'], r['wm_name'], r['thumb_name']]
                c.execute('DELETE FROM users WHERE id=?', (me['id'],)); c.commit()
                remove_uploads(names)
                return self.send_json(200, {'ok': True},
                                       {'Set-Cookie': 'xx_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax'})
            if p.startswith('/api/items/'):
                iid = p.split('/')[-1]
                row = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
                if not row: return self.send_json(404, {'error': '内容不存在'})
                if not admin and row['uploader_id'] != me['id']: return self.send_json(403, {'error': '只能删除自己的内容'})
                fid = row['file_id']
                c.execute('DELETE FROM items WHERE id=?', (iid,))
                if fid:
                    f = c.execute('SELECT * FROM files WHERE id=?', (fid,)).fetchone()
                    c.execute('DELETE FROM files WHERE id=?', (fid,))
                c.commit()
                if fid and f:
                    remove_uploads([f['stored_name'], f['wm_name'], f['thumb_name']])
                return self.send_json(200, {'ok': True})
            if p.startswith('/api/collections/'):
                cid = p.split('/')[-1]
                row = c.execute('SELECT * FROM collections WHERE id=?', (cid,)).fetchone()
                if not row: return self.send_json(404, {'error': '作品集不存在'})
                if not admin and row['uploader_id'] != me['id']: return self.send_json(403, {'error': '只能删除自己的作品集'})
                c.execute('UPDATE items SET collection_id=NULL WHERE collection_id=?', (cid,))
                c.execute('DELETE FROM collections WHERE id=?', (cid,)); c.commit()
                return self.send_json(200, {'ok': True, 'message': '作品集已删除，内容已保留'})
            if p.startswith('/api/users/'):
                if not admin: return self.send_json(403, {'error': '需要管理员权限'})
                uid = p.split('/')[-1]
                if int(uid) == me['id']: return self.send_json(400, {'error': '请从设置中注销自己'})
                names = []
                for r in c.execute('SELECT stored_name, wm_name, thumb_name FROM files WHERE uploader_id=?', (uid,)):
                    names += [r['stored_name'], r['wm_name'], r['thumb_name']]
                c.execute('DELETE FROM users WHERE id=?', (uid,)); c.commit()
                remove_uploads(names)
                return self.send_json(200, {'ok': True})
            return self.send_json(404, {'error': '接口不存在'})
        finally:
            c.close()


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', '8766'))
    print('星匣服务已启动: http://127.0.0.1:%d' % port)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
