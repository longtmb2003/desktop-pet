"""What kind of program the user is working in, from the window class KWin reports (never the window title: that would carry file
names and page titles). Used for a remark that fits what they are doing."""
import random

CATEGORIES = {                                   # substring of the (lower-case) window class -> kind of work
    "terminal": ("konsole", "ghostty", "alacritty", "kitty", "xterm", "wezterm", "foot", "terminal", "tilix", "yakuake"),
    "editor": ("code", "codium", "jetbrains", "pycharm", "idea", "clion", "kate", "kwrite", "gedit", "sublime", "emacs", "vim", "zed",
               "cursor", "neovide", "geany", "gnome-builder"),
    "browser": ("firefox", "chrome", "chromium", "brave", "vivaldi", "opera", "zen", "epiphany", "falkon", "librewolf", "edge"),
    "chat": ("telegram", "discord", "slack", "zalo", "signal", "element", "teams", "whatsapp", "skype", "thunderbird", "kmail",
             "evolution"),
    "office": ("libreoffice", "soffice", "onlyoffice", "wps", "okular", "evince", "calligra", "zathura", "xournal", "obsidian", "notion"),
    "media": ("vlc", "mpv", "spotify", "celluloid", "elisa", "haruna", "totem", "youtube", "amberol"),
    "files": ("dolphin", "nautilus", "thunar", "nemo", "pcmanfm", "krusader", "files"),
    "design": ("gimp", "krita", "inkscape", "blender", "figma", "darktable", "kdenlive", "shotcut", "aseprite"),
}
REMARKS = {
    "terminal": ("Gõ lệnh gì mà nhìn ghê thế?", "Cẩn thận với rm -rf đó nha!", "Đen thui thế này, chạy được chưa?"),
    "editor": ("Code chạy được chưa đó?", "Nhớ lưu file nha!", "Bug đâu, ra đây!"),
    "browser": ("Mở bao nhiêu tab rồi?", "Lướt web hay làm việc thế?", "Tab nào cũng thấy hay hả?"),
    "chat": ("Nhắn tin hoài, nhớ uống nước!", "Trả lời xong chưa?", "Ai nhắn mà bạn cười thế?"),
    "office": ("Lưu file chưa?", "Văn bản dài quá, nghỉ tí đi!", "Chữ nhiều thế, đọc nổi không?"),
    "media": ("Cho tôi xem với!", "Bật lớn tiếng lên xem nào!", "Nghe gì thế?"),
    "files": ("Lục file gì đó?", "Nhiều file quá, dọn đi!", "Kéo thả nhẹ tay thôi!"),
    "design": ("Vẽ đẹp ghê!", "Cho tôi tô một nét được không?", "Màu này hợp đó!"),
    "": ("Đang làm gì vậy?", "Cho tôi xem với!", "Làm việc chăm quá!"),
}
MAX_CLASS = 80


def category(window_class):
    """"terminal", "editor", "browser", "chat", "office", "media", "files", "design" or "" (unknown) for a window class"""
    c = str(window_class).lower()[:MAX_CLASS]
    return next((kind for kind, keys in CATEGORIES.items() if any(k in c for k in keys)), "")


def remark(window_class, own=None, rng=random):
    """something to say about the program: from `own` ({kind: (lines...)}, a character's own words) if it has some, else the defaults"""
    kind = category(window_class)
    lines = (own or {}).get(kind) or REMARKS[kind]
    return rng.choice(lines)
