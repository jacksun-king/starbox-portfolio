#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""星匣 · 演示数据生成器

全新克隆后执行：

    python seed_demo.py

会生成演示账号（curator / demo123）、3 个作品集、12 张照片、3 篇文章和示例选片。
原图来自 demo/photos/，水印样片与列表缩略图由 Pillow 现场生成；
未安装 Pillow 时自动跳过派生图，站点仍可正常浏览。

已有内容时不会重复写入，需要重建请加 --force（只清理演示账号的数据）。
"""

import argparse
import json
import os
import secrets
import shutil
import sys

import server
import imaging

PHOTO_DIR = os.path.join(server.ROOT, 'demo', 'photos')

DEMO_USER = {
    'username': 'curator',
    'password': 'demo123',
    'email': 'curator@example.com',
    'bio': '摄影 / 旅行 / 偶尔写字',
}

WM_TEXT = '© curator · 仅供预览'

COLLECTIONS = [
    {
        'key': 'wild',
        'title': '山野与远方',
        'desc': '雾、森林、海岸与荒漠 —— 把走在路上的瞬间收在一起。',
        'tags': ['旅行', '风光', '自然'],
        'accent': '#9e624a',
        'story': """## 从雾里走到海边

这一组照片没有固定的目的地。清晨的山雾、森林里拐弯的小路、荒漠公路尽头的海，都是路上遇见的片刻。

> 好的风景不在地图上，在你愿意停下来的地方。
""",
    },
    {
        'key': 'city',
        'title': '城市与建筑',
        'desc': '霓虹、几何与街角咖啡，城市里的秩序和温度。',
        'tags': ['城市', '建筑', '夜景'],
        'accent': '#3e6c9e',
        'story': """## 城市的另一面

霓虹亮起之后，城市开始显露它的秩序：玻璃幕墙的几何、街角咖啡店的热气、天桥下匆匆走过的人。

这组照片想记录的不是地标，而是城市呼吸的节奏。
""",
    },
    {
        'key': 'light',
        'title': '光影收藏',
        'desc': '一束光落下来，静物、书页和夜空都有了故事。',
        'tags': ['静物', '光影', '生活'],
        'accent': '#567bae',
        'story': """## 光落下来的地方

一束光落在桌面上，书页有了温度；夜色足够深的时候，极光才显得安静。

这些画面都很轻，但值得被收进同一个盒子里。
""",
    },
]

ITEMS = [
    {'photo': '01-mountain-mist.jpg', 'title': '山野晨雾', 'coll': 'wild',
     'tags': ['风光', '自然', '壁纸'], 'views': 122,
     'exif': {'camera': 'SONY ILCE-7M4', 'lens': 'FE 24-70mm F2.8 GM II', 'focal': '48mm',
              'aperture': 'f/4', 'shutter': '1/250s', 'iso': 'ISO 200', 'taken': '2026-10-04 06:12:00'}},
    {'photo': '04-coastline.jpg', 'title': '海岸线', 'coll': 'wild',
     'tags': ['海洋', '旅行', '壁纸'], 'views': 96,
     'exif': {'camera': 'SONY ILCE-7M4', 'lens': 'FE 24-70mm F2.8 GM II', 'focal': '35mm',
              'aperture': 'f/2.8', 'shutter': '1/800s', 'iso': 'ISO 100', 'taken': '2026-10-05 17:41:00'}},
    {'photo': '06-forest-path.jpg', 'title': '森林小径', 'coll': 'wild',
     'tags': ['森林', '自然', '绿意'], 'views': 74,
     'exif': {'camera': 'SONY ILCE-7M4', 'lens': 'FE 50mm F1.8', 'focal': '50mm',
              'aperture': 'f/1.8', 'shutter': '1/125s', 'iso': 'ISO 400', 'taken': '2026-10-06 09:20:00'}},
    {'photo': '12-desert-road.jpg', 'title': '沙漠公路', 'coll': 'wild',
     'tags': ['沙漠', '公路', '旅行'], 'views': 88,
     'exif': {'camera': 'SONY ILCE-7M4', 'lens': 'FE 70-200mm F4 G', 'focal': '70mm',
              'aperture': 'f/5.6', 'shutter': '1/500s', 'iso': 'ISO 100', 'taken': '2026-10-07 15:08:00'}},
    {'photo': '02-city-night.jpg', 'title': '城市夜色', 'coll': 'city',
     'tags': ['城市', '夜景', '摄影'], 'views': 143,
     'exif': {'camera': 'FUJIFILM X-T5', 'lens': 'XF 35mm F1.4 R', 'focal': '35mm',
              'aperture': 'f/1.8', 'shutter': '1/60s', 'iso': 'ISO 1600', 'taken': '2026-09-18 20:52:00'}},
    {'photo': '05-geometry.jpg', 'title': '建筑几何', 'coll': 'city',
     'tags': ['建筑', '极简', '摄影'], 'views': 61,
     'exif': {'camera': 'FUJIFILM X-T5', 'lens': 'XF 16mm F2.8 R WR', 'focal': '16mm',
              'aperture': 'f/8', 'shutter': '1/320s', 'iso': 'ISO 100', 'taken': '2026-09-19 11:30:00'}},
    {'photo': '07-coffee.jpg', 'title': '咖啡时光', 'coll': 'city',
     'tags': ['生活', '咖啡', '静物'], 'views': 57,
     'exif': {'camera': 'FUJIFILM X-T5', 'lens': 'XF 35mm F1.4 R', 'focal': '35mm',
              'aperture': 'f/2', 'shutter': '1/160s', 'iso': 'ISO 320', 'taken': '2026-09-20 10:12:00'}},
    {'photo': '03-still-light.jpg', 'title': '静物光影', 'coll': 'light',
     'tags': ['静物', '室内', '设计'], 'views': 69,
     'exif': {'camera': 'Canon EOS R6', 'lens': 'RF 90mm F2.8 L Macro', 'focal': '90mm',
              'aperture': 'f/2.8', 'shutter': '1/200s', 'iso': 'ISO 400', 'taken': '2026-11-02 14:05:00'}},
    {'photo': '10-book-light.jpg', 'title': '书与光', 'coll': 'light',
     'tags': ['阅读', '书籍', '生活'], 'views': 52,
     'exif': {'camera': 'Canon EOS R6', 'lens': 'RF 50mm F1.8 STM', 'focal': '50mm',
              'aperture': 'f/2', 'shutter': '1/125s', 'iso': 'ISO 500', 'taken': '2026-11-02 16:22:00'}},
    {'photo': '11-aurora.jpg', 'title': '极光之夜', 'coll': 'light',
     'tags': ['极光', '夜空', '壁纸'], 'views': 210,
     'exif': {'camera': 'Nikon Z6 III', 'lens': 'NIKKOR Z 14-24mm F2.8 S', 'focal': '14mm',
              'aperture': 'f/2.8', 'shutter': '8s', 'iso': 'ISO 1600', 'taken': '2026-03-11 23:40:00'}},
    {'photo': '08-snow-peak.jpg', 'title': '雪山之巅', 'coll': None, 'visibility': 'private',
     'tags': ['雪山', '风光', '壁纸'], 'views': 18,
     'exif': {'camera': 'Nikon Z6 III', 'lens': 'NIKKOR Z 70-200mm F2.8', 'focal': '70mm',
              'aperture': 'f/8', 'shutter': '1/1000s', 'iso': 'ISO 100', 'taken': '2026-01-06 08:15:00'}},
    {'photo': '09-vintage-camera.jpg', 'title': '复古相机', 'coll': None, 'visibility': 'password',
     'password': '1234', 'tags': ['复古', '器物', '摄影'], 'views': 24,
     'exif': {'camera': 'LEICA Q3', 'lens': 'Summicron 28mm F1.7', 'focal': '28mm',
              'aperture': 'f/2.8', 'shutter': '1/160s', 'iso': 'ISO 640', 'taken': '2026-08-22 15:30:00'}},
]

POSTS = [
    {'title': '关于收藏这件事', 'tags': ['随笔', '生活', '收藏'], 'views': 86, 'body': """# 关于收藏

有些东西，看到的第一眼就想留下来。

可能是一张照片里的光，可能是一段话里的分寸感，也可能只是一段安静的旋律。

**收藏不是为了占有**，是为了在某个疲惫的时刻，还能重新遇见当时的自己。

> 星匣存在的意义，大概就是给这些「想留下来的瞬间」一个落脚的地方。

---

## 这里放什么

- 好看的图片，做成图床
- 写过的文字，整理成文章
- 有用的资料，锁进私密柜

公开、私密、密码保护，三档自由切换。
"""},
    {'title': '我的图片调色笔记', 'tags': ['摄影', '调色', '教程'], 'views': 132, 'body': """# 图片调色笔记

整理了常用的几个思路，记在这里。

## 1. 先定基调

不要把每种颜色都调到位，先决定整张图的**情绪**是冷是暖。

## 2. 压高光、提阴影

让画面更通透，细节出来之后再谈风格。

```
高光 -30
阴影 +20
对比 +10
```

## 3. 克制饱和度

宁可淡一点，也别让颜色跳出来抢戏。
"""},
    {'title': '作品集是怎么做出来的', 'tags': ['指南', '作品集'], 'views': 245, 'body': """# 作品集是怎么做出来的

四步，从一堆原片到一个能发出去的链接。

## 1. 批量上传

进入「创作」，一次选好整组照片（最多 60 张）。同一次上传可以直接归入一个作品集。

上传时可以打开**样片水印**，访客看到的永远是带水印的预览图，原图只有作者能下载。

## 2. 写成作品集

封面、标题、描述、Markdown 故事、标签。封面会自动提取主色，整页配色跟着变。

## 3. 发链接

每个作品集都有 `/s/<token>` 短链，可以复制、可以重置。设了密码的作品集，访客要先输入密码。

访客不需要注册，打开就能看，还能点选喜欢的照片。

## 4. 交付

- 导出选片清单 CSV（含每张被选次数），直接给后期
- 生成 1080 宽竖版长图，发小红书、朋友圈、微博
"""},
]

PICKS = {
    'wild': {'山野晨雾': 3, '海岸线': 2, '沙漠公路': 1},
    'city': {'城市夜色': 4, '建筑几何': 1, '咖啡时光': 2},
    'light': {'极光之夜': 3, '静物光影': 2},
}

IMAGE_EXT = {'jpg', 'jpeg', 'png', 'webp', 'bmp', 'avif'}


def ensure_user(c):
    row = c.execute('SELECT * FROM users WHERE username=?', (DEMO_USER['username'],)).fetchone()
    if row:
        return row['id'], False
    first = c.execute('SELECT COUNT(*) n FROM users').fetchone()['n'] == 0
    c.execute('INSERT INTO users(username,email,password,role,bio,created_at) VALUES(?,?,?,?,?,?)',
              (DEMO_USER['username'], DEMO_USER['email'], server.hash_pw(DEMO_USER['password']),
               'admin' if first else 'user', DEMO_USER['bio'], server.now()))
    return c.execute('SELECT last_insert_rowid() id').fetchone()['id'], True


def clear_demo(c, uid):
    rows = c.execute('SELECT id, file_id FROM items WHERE uploader_id=?', (uid,)).fetchall()
    for r in rows:
        if r['file_id']:
            f = c.execute('SELECT stored_name,wm_name,thumb_name FROM files WHERE id=?', (r['file_id'],)).fetchone()
            if f:
                server.remove_uploads([f['stored_name'], f['wm_name'], f['thumb_name']])
            c.execute('DELETE FROM files WHERE id=?', (r['file_id'],))
    c.execute('DELETE FROM collection_picks WHERE collection_id IN (SELECT id FROM collections WHERE uploader_id=?)', (uid,))
    c.execute('DELETE FROM collections WHERE uploader_id=?', (uid,))
    c.execute('DELETE FROM items WHERE uploader_id=?', (uid,))
    c.commit()


def add_photo(c, uid, spec, coll_id):
    src = os.path.join(PHOTO_DIR, spec['photo'])
    if not os.path.isfile(src):
        print('  跳过（缺少文件）：%s' % spec['photo'])
        return None
    ext = spec['photo'].rsplit('.', 1)[-1].lower()
    stored = secrets.token_hex(16) + '.' + ext
    dst = os.path.join(server.UPLOAD_DIR, stored)
    shutil.copyfile(src, dst)
    size = os.path.getsize(dst)
    w, h = imaging.dimension(dst) if ext in IMAGE_EXT else (0, 0)
    wm_name = thumb_name = ''
    if ext in IMAGE_EXT:
        tp = os.path.splitext(stored)[0] + '_s.jpg'
        imaging.make_preview(dst, os.path.join(server.UPLOAD_DIR, tp), 720, '')
        if os.path.isfile(os.path.join(server.UPLOAD_DIR, tp)):
            thumb_name = tp
        prev = os.path.splitext(stored)[0] + '_wm.jpg'
        _w, _h, applied = imaging.make_preview(dst, os.path.join(server.UPLOAD_DIR, prev), 1680, WM_TEXT)
        if applied:
            wm_name = prev
    ts = server.now()
    c.execute('''INSERT INTO files(original_name,stored_name,size,mime,ext,uploader_id,created_at,
                                   wm_name,thumb_name,width,height)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
              (spec['photo'], stored, size, 'image/jpeg', ext, uid, ts, wm_name, thumb_name, w, h))
    fid = c.execute('SELECT last_insert_rowid() id').fetchone()['id']
    vis = spec.get('visibility', 'public')
    c.execute('''INSERT INTO items(kind,title,body,tags,visibility,password,file_id,collection_id,
                                   exif,uploader_id,views,created_at,updated_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              ('image', spec['title'], '', json.dumps(spec['tags'], ensure_ascii=False), vis,
               server.hash_pw(spec['password']) if vis == 'password' and spec.get('password') else '',
               fid, coll_id, json.dumps(spec.get('exif') or {}, ensure_ascii=False), uid,
               spec.get('views', 0), ts, ts))
    return c.execute('SELECT last_insert_rowid() id').fetchone()['id']


def main():
    ap = argparse.ArgumentParser(description='生成星匣演示数据')
    ap.add_argument('--force', action='store_true', help='清理演示账号的现有内容后重建')
    args = ap.parse_args()

    if not os.path.isdir(PHOTO_DIR):
        print('找不到演示照片目录：%s' % PHOTO_DIR)
        return 1

    server.init_db()
    c = server.db()
    uid, created = ensure_user(c)
    c.commit()

    n = c.execute('SELECT COUNT(*) n FROM items WHERE uploader_id=?', (uid,)).fetchone()['n']
    if n and not args.force:
        print('演示数据已存在（%d 条），未做改动。重建请执行：python seed_demo.py --force' % n)
        return 0
    if n:
        print('清理旧的演示数据…')
        clear_demo(c, uid)

    print('生成演示内容…')
    col_ids = {}
    for spec in COLLECTIONS:
        ts = server.now()
        c.execute('''INSERT INTO collections(title,description,tags,visibility,password,uploader_id,
                                             views,created_at,updated_at,story,share_token,allow_pick,accent)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (spec['title'], spec['desc'], json.dumps(spec['tags'], ensure_ascii=False),
                   'public', '', uid, 0, ts, ts, spec['story'], secrets.token_urlsafe(9), 1, spec['accent']))
        col_ids[spec['key']] = c.execute('SELECT last_insert_rowid() id').fetchone()['id']

    item_ids = {}
    for spec in ITEMS:
        cid = col_ids.get(spec['coll']) if spec.get('coll') else None
        iid = add_photo(c, uid, spec, cid)
        if iid:
            item_ids[spec['title']] = iid

    for key, picks in PICKS.items():
        cid = col_ids.get(key)
        for title, times in picks.items():
            iid = item_ids.get(title)
            if not cid or not iid:
                continue
            for _ in range(times):
                c.execute('INSERT INTO collection_picks(collection_id,item_id,visitor_token,created_at) VALUES(?,?,?,?)',
                          (cid, iid, secrets.token_urlsafe(12), server.now()))

    for coll_key, spec in ((k, s) for k, s in col_ids.items()):
        first = c.execute('SELECT id FROM items WHERE collection_id=? ORDER BY id LIMIT 1', (spec,)).fetchone()
        if first:
            c.execute('UPDATE collections SET cover_id=? WHERE id=?', (first['id'], spec))

    # 作品集封面主色：有 Pillow 时按真实封面重算，否则沿用预设色
    for spec in COLLECTIONS:
        cid = col_ids[spec['key']]
        row = c.execute('''SELECT f.stored_name FROM collections co
                           JOIN items i ON i.id=co.cover_id
                           JOIN files f ON f.id=i.file_id WHERE co.id=?''', (cid,)).fetchone()
        if row and row['stored_name'] and imaging.PIL_OK:
            accent = imaging.dominant_color(os.path.join(server.UPLOAD_DIR, row['stored_name']), spec['accent'])
            c.execute('UPDATE collections SET accent=? WHERE id=?', (accent, cid))

    for spec in POSTS:
        ts = server.now()
        c.execute('''INSERT INTO items(kind,title,body,tags,visibility,password,uploader_id,views,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?)''',
                  ('post', spec['title'], spec['body'], json.dumps(spec['tags'], ensure_ascii=False),
                   'public', '', uid, spec.get('views', 0), ts, ts))

    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('watermark_text',?)", (WM_TEXT,))
    c.commit()

    cols = c.execute('SELECT id,title,share_token FROM collections WHERE uploader_id=? ORDER BY id', (uid,)).fetchall()
    print('完成：%d 张照片 / %d 个作品集 / %d 篇文章' % (len(item_ids), len(cols), len(POSTS)))
    print('演示账号：%s / %s' % (DEMO_USER['username'], DEMO_USER['password']))
    for r in cols:
        print('  作品集 #%d %s  →  /s/%s' % (r['id'], r['title'], r['share_token']))
    c.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
