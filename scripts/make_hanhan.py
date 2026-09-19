"""Build the Hà Nhân sprite pack into mochi/pets/packs/hanhan/ from the two source images in packaging/:
  "hà nhân.jpg"              the whole figure on white   -> body.png (white background cut out, own face blanked) + faces/neutral.png
  "biểu cảm mặt hà nhân.png" a 5x5 sheet of head frames  -> faces/talk_*.png (frames 3911-3929) and faces/laugh_*.png (3930-3935)
  "Hà Nhân chạy xe"          him on a tricycle (and a close-up head)  -> ride.png (background cut, stray "+" mark removed)
  the body again with the arm(s) that are tucked behind his back cut away -> free_left.png, free_right.png, free_both.png, used
  while he draws his own arm (pointing, holding a sign) so that there aren't two arms
Faces become transparent ink overlays (dark strokes; the alpha is the darkness) registered to the body's own face, so any expression
can be laid over the blank head. Run from anywhere:  python scripts/make_hanhan.py  [--preview out.png]"""
import json
import sys
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPolygonF

ROOT = Path(__file__).resolve().parent.parent
SRC_BODY, SRC_SHEET = ROOT / "packaging" / "hà nhân.jpg", ROOT / "packaging" / "biểu cảm mặt hà nhân.png"
SRC_RIDE = ROOT / "packaging" / "Hà Nhân chạy xe"
OUT = ROOT / "mochi" / "pets" / "packs" / "hanhan"

# The arms behind his back are the two rounded bulges at the sides of the coat (in the cropped body image). To free an arm, everything
# beyond the straight line that the coat edge would follow without it is erased, and that line is drawn as the new coat edge.
ARM_CUT = {"left": ((152, 352), (126, 557), (60, 340), (60, 575)), "right": ((332, 345), (350, 562), (460, 335), (460, 580))}
EDGE_INK = QColor(28, 34, 48)
RIDER_X = 470                                       # the tricycle rider is left of this in the sheet, a close-up head is right of it
STRAY_MARK = (225, 227, 8)                          # a small "+" drawn on the rider's face in the source: (x, y, radius) to whiten
# wheels of the tricycle in the source image: centre and radii of the tyre, the orange rim, the hub the spokes turn about, and shapes
# (the rider's shoe) that lie over the rim and must not be painted over
WHEELS = ({"x": 235, "y": 410, "rx": 36, "ry": 41, "rim_x": 232, "rim_y": 411, "rim_rx": 24, "rim_ry": 29, "hub": [236, 413],
           "avoid": [[205, 393], [262, 380], [274, 395], [258, 440], [226, 436], [208, 420]]},
          {"x": 393, "y": 410, "rx": 32, "ry": 38, "rim_x": 397, "rim_y": 410, "rim_rx": 22, "rim_ry": 29, "hub": [405, 410], "avoid": []})
BG_LUM = 232                                        # brighter than this and connected to the border = background
BODY_FACE = (190, 222, 380, 398)                    # search area for the body's own face ink (x0, y0, x1, y1), inside the head outline
TILE_FACE = (14, 50, 70, 108)                       # the same for a sheet tile, after mirroring it (the sheet faces the other way)
XS, YS, TW, TH = (0, 123, 248, 373, 498), (9, 159, 309, 459, 609), 118, 119      # sheet grid
MARGIN = (0.10, 0.30, 0.12)                         # blank left, right and above the neutral face's ink: room for wider expressions
CONTRAST = (28, 1.5)                                # the sheet's faces are soft airbrush: drop the faint halo, deepen the core


def lum(c):
    return (((c >> 16) & 255) * 299 + ((c >> 8) & 255) * 587 + (c & 255) * 114) // 1000


def cut_background(im):
    """flood the white from the border inwards: the head, the robe's white stripe etc. stay because outlines enclose them"""
    w, h = im.width(), im.height()
    seen, q = bytearray(w * h), deque([(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)])
    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y * w + x] or lum(im.pixel(x, y)) < BG_LUM: continue
        seen[y * w + x] = 1
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    out = QImage(w, h, QImage.Format_ARGB32); out.fill(0)
    for y in range(h):
        for x in range(w):
            if seen[y * w + x]: continue
            near_bg = any(0 <= x + dx < w and 0 <= y + dy < h and seen[(y + dy) * w + x + dx]
                          for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            c = im.pixel(x, y)
            if near_bg:                                          # a fringe pixel: pale = mostly background, so fade it out
                a = max(0, min(255, int((235 - lum(c)) * 255 / 130)))
                out.setPixel(x, y, (a << 24) | (c & 0xFFFFFF))
            else:
                out.setPixel(x, y, 0xFF000000 | (c & 0xFFFFFF))
    return out


def outline(im, rect, thr=120):
    """pixels of rect that belong to dark shapes running into the rect's border: the head outline, ears, hat. A face lies inside the
    rect, so none of its strokes touch the border, and they are left out of this set"""
    x0, y0, x1, y1 = rect
    dark = {(x, y) for y in range(y0, y1) for x in range(x0, x1) if lum(im.pixel(x, y)) < thr}
    out, todo = set(), deque(p for p in dark if p[0] in (x0, x1 - 1) or p[1] in (y0, y1 - 1))
    while todo:
        p = todo.popleft()
        if p in out or p not in dark: continue
        out.add(p)
        todo.extend((p[0] + dx, p[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    return out


def ink_box(im, rect, thr=120):
    """bounding box of the face's dark strokes inside rect (outline-connected shapes excluded), padded a little for soft edges"""
    skip = outline(im, rect, thr)
    pts = [(x, y) for y in range(rect[1], rect[3]) for x in range(rect[0], rect[2]) if lum(im.pixel(x, y)) < thr and (x, y) not in skip]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs) - 3, min(ys) - 3, max(xs) + 3, max(ys) + 3


def ink(im, rect, size):
    """the pixels of `rect` as a transparent black-ink overlay of `size`: darkness becomes opacity (outline-connected shapes dropped)"""
    im = im.copy()
    for x, y in outline(im, rect, 150): im.setPixel(x, y, 0xFFFFFFFF)
    crop = im.copy(QRect(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]))
    crop = crop.scaled(size[0], size[1], Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    out = QImage(size[0], size[1], QImage.Format_ARGB32); out.fill(0)
    for y in range(size[1]):
        for x in range(size[0]):
            a = max(0, min(255, int(((250 - lum(crop.pixel(x, y))) * 255 / 250 - CONTRAST[0]) * CONTRAST[1])))
            if a > 6: out.setPixel(x, y, a << 24)
    return out


def main():
    QGuiApplication(sys.argv[:1])
    body_src = QImage(str(SRC_BODY)).convertToFormat(QImage.Format_ARGB32)
    sheet = QImage(str(SRC_SHEET)).convertToFormat(QImage.Format_ARGB32)
    bx0, by0, bx1, by1 = ink_box(body_src, BODY_FACE)
    body_ink = (bx0, by0, bx1, by1)
    tile0 = tile(sheet, 3911)
    tx0, ty0, tx1, ty1 = ink_box(tile0, TILE_FACE)
    k = ((bx1 - bx0) / (tx1 - tx0) + (by1 - by0) / (ty1 - ty0)) / 2                  # tile pixels -> body pixels
    print(f"body face ink {body_ink}, tile face ink {(tx0, ty0, tx1, ty1)}, scale {k:.2f}")
    ml, mr = (int((bx1 - bx0) * m) for m in MARGIN[:2])
    mt = int((by1 - by0) * MARGIN[2])                                                # (no margin below: the chin outline is there)
    box = (bx0 - ml, by0 - mt, bx1 - bx0 + ml + mr, by1 - by0 + mt)                  # where faces go, in body pixels
    tbox = (int(tx0 - ml / k), int(ty0 - mt / k), int(tx1 + mr / k), int(ty1))
    size = (box[2], box[3])

    faces = {"neutral": [ink(body_src, (box[0], box[1], box[0] + box[2], box[1] + box[3]), size)]}
    faces["talk"] = [ink(tile(sheet, n), tbox, size) for n in range(3911, 3930)]
    faces["laugh"] = [ink(tile(sheet, n), tbox, size) for n in range(3930, 3936)]

    keep = outline(body_src, (box[0], box[1], box[0] + box[2], box[1] + box[3]), 200)
    for y in range(box[1], box[1] + box[3]):                                         # blank the body's own face (not the outline)
        for x in range(box[0], box[0] + box[2]):
            if lum(body_src.pixel(x, y)) < 250 and (x, y) not in keep: body_src.setPixel(x, y, 0xFFFFFFFF)
    body = cut_background(body_src)
    xs = [x for y in range(body.height()) for x in range(body.width()) if body.pixel(x, y) >> 24]
    ys = [y for y in range(body.height()) for x in range(body.width()) if body.pixel(x, y) >> 24]
    crop = QRect(min(xs) - 1, min(ys) - 1, max(xs) - min(xs) + 3, max(ys) - min(ys) + 3)
    body = body.copy(crop)
    box = (box[0] - crop.x(), box[1] - crop.y(), box[2], box[3])

    (OUT / "faces").mkdir(parents=True, exist_ok=True)
    body.save(str(OUT / "body.png"))
    ride, (ox, oy) = ride_sprite()
    ride.save(str(OUT / "ride.png"))
    wheels = [{**w, "x": w["x"] - ox, "y": w["y"] - oy, "rim_x": w["rim_x"] - ox, "rim_y": w["rim_y"] - oy,
               "hub": [w["hub"][0] - ox, w["hub"][1] - oy], "avoid": [[a - ox, b - oy] for a, b in w["avoid"]]} for w in WHEELS]
    free = {"left": "free_left.png", "right": "free_right.png", "both": "free_both.png"}
    for key, sides in (("left", ("left",)), ("right", ("right",)), ("both", ("left", "right"))):
        free_arms(body, sides).save(str(OUT / free[key]))
    files = {}
    for kind, frames in faces.items():
        files[kind] = []
        for i, f in enumerate(frames):
            name = f"faces/{kind}_{i:02d}.png"
            f.save(str(OUT / name)); files[kind].append(name)
    (OUT / "pack.json").write_text(json.dumps({
        "id": "hanhan", "name": "Hà Nhân", "size": 240, "feet": 232, "height": 200, "walk_speed": 42,
        "body": "body.png", "body_free": free,
        "ride": {"image": "ride.png", "height": 170, "speed": 2.0, "wheels": wheels,
                 "lines": ["Ting ting!", "Tránh ra, tránh ra!", "Vù vù~", "Đừng cản đường tôi!"]},
        "face": {"box": list(box)}, "faces": files, "fps": {"talk": 12, "laugh": 8},
        "behaviors": {"idle": 4, "walk": 4, "sleep": 1, "chase": 1, "rant": 2, "yawn": 1, "point": 2, "wag": 2, "lecture": 1},
        "scold": ["Làm việc đi, đừng có lười!", "Nhìn cái gì mà nhìn!", "Sao còn chưa lưu file hả?", "Bỏ cái điện thoại xuống!",
                  "Ngồi thẳng lưng lên!", "Uống nước đi, nói mãi không nghe!", "Deadline đến nơi rồi kìa!", "Cái mặt đó là sao hả?"],
        "chatter": ["Làm việc đi!", "Sao còn chưa lưu file?", "Nhìn cái gì?", "Uống nước chưa hả?", "Ngồi lì thế, đứng dậy đi!",
                    "Hừm...", "Nghỉ mắt tí đi, đỏ hết rồi kìa"],
        "scream": "Trời ơi!", "drop": "Cái gì đây? {name}", "desktop_remark": "{name}... nằm chình ình ở đó làm gì?",
        "sway": 4, "bob": 5, "work_prop": "sign", "looks": "left", "turn": 0.3}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT, "body", body.width(), "x", body.height(), "box", box)
    if "--preview" in sys.argv:
        preview(body, box, faces, Path(sys.argv[sys.argv.index("--preview") + 1]))


def free_arms(body, sides):
    """a copy of `body` with the arm(s) named in `sides` ("left", "right": as the picture shows them) cut away, leaving a clean edge"""
    out = body.copy()
    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    for side in sides:
        (x0, y0), (x1, y1), (fx, fy), (bx, by) = ARM_CUT[side]
        poly = QPolygonF([QPointF(x0, y0), QPointF(fx, fy), QPointF(bx, by), QPointF(x1, y1)])
        p.setBrush(Qt.black); p.setPen(Qt.NoPen); p.drawPolygon(poly)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(EDGE_INK, 5, Qt.SolidLine, Qt.RoundCap))
    for side in sides:
        (x0, y0), (x1, y1) = ARM_CUT[side][:2]
        p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
    p.end()
    return out


def ride_sprite():
    """the tricycle rider from the sheet: background cut away, the stray mark whitened; returns (image, crop origin)"""
    src = QImage(str(SRC_RIDE)).convertToFormat(QImage.Format_ARGB32)
    cx, cy, cr = STRAY_MARK
    for y in range(cy - cr, cy + cr + 1):
        for x in range(cx - cr, cx + cr + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= cr * cr and lum(src.pixel(x, y)) < 170: src.setPixel(x, y, 0xFFFFFFFF)
    cut = cut_background(src)
    pts = [(x, y) for y in range(cut.height()) for x in range(RIDER_X) if cut.pixel(x, y) >> 24]
    x0, y0 = min(p[0] for p in pts) - 1, min(p[1] for p in pts) - 1
    x1, y1 = max(p[0] for p in pts) + 2, max(p[1] for p in pts) + 2
    return cut.copy(QRect(x0, y0, x1 - x0, y1 - y0)), (x0, y0)


def tile(sheet, n):
    i = n - 3911
    return sheet.copy(QRect(XS[i % 5], YS[i // 5], TW, TH)).flipped(Qt.Horizontal)


def preview(body, box, faces, path):
    """the head with a few expressions laid over it"""
    show = [("neutral", 0), ("talk", 0), ("talk", 9), ("talk", 18), ("laugh", 0), ("laugh", 4)]
    hx, hy, hw, hh = box[0] - 50, box[1] - 170, 340, 360                              # head area of the body image
    cell = QImage(hw, hh, QImage.Format_ARGB32)
    out = QImage(hw * 3, hh * 2, QImage.Format_ARGB32); out.fill(QColor("#e8e0ff"))
    p = QPainter(out); p.setRenderHint(QPainter.SmoothPixmapTransform)
    for i, (kind, n) in enumerate(show):
        cell.fill(0)
        c = QPainter(cell); c.setRenderHint(QPainter.SmoothPixmapTransform); c.drawImage(-hx, -hy, body)
        c.drawImage(QRectF(box[0] - hx, box[1] - hy, box[2], box[3]), faces[kind][n]); c.end()
        p.drawImage((i % 3) * hw, (i // 3) * hh, cell)
    p.end(); out.save(str(path)); print("preview", path)


if __name__ == "__main__":
    main()
