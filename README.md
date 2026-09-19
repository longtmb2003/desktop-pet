# desktop-pet

**Mochi** — một pet desktop nhỏ, nhẹ, vẽ hoàn toàn bằng vector (không cần sprite), dành cho KDE Plasma.

![Mochi: 5 màu, 6 tư thế](docs/preview.png)

*Ảnh trên do chính bộ vẽ của Mochi render ra (không phải ảnh chụp màn hình). GIF quay từ màn hình thật: chưa có.*

## Tính năng

- Đi lại, ngồi, ngủ (có Zzz), chớp mắt, mắt nhìn theo con trỏ chuột
- Tự chọn ngẫu nhiên các động tác: ngáp, vươn vai, liếm chân, và chạy đuổi theo con trỏ
- Kéo thả để nhấc lên, thả ra thì rơi; bấm vào thì nhảy lên và bay trái tim
- Đứng và đi trên đỉnh các cửa sổ (đi theo khi bạn kéo cửa sổ), thỉnh thoảng nhảy lên cửa sổ gần đó; không đứng trên cửa sổ đang bị cửa sổ khác che
- Click xuyên qua phần trong suốt quanh pet
- 5 màu (Kem, Cam, Xám, Bạc hà, Hồng), được nhớ cho lần chạy sau
- Chuột phải: Màu / Ngủ / Gọi về / Tạm dừng / Tự chạy khi đăng nhập / Thoát

## Nền tảng hỗ trợ

| Môi trường | Trạng thái |
|---|---|
| KDE Plasma 6, Wayland (qua XWayland) | Đầy đủ: đi trên cửa sổ. Đã thử trên Fedora 44, Plasma 6.7, 2 màn hình (scale 1) |
| Linux khác (X11, GNOME…) | Chạy ở chế độ "floor-only": chỉ đi trên sàn màn hình. Chưa kiểm tra trên máy thật |
| Windows / macOS | Chưa hỗ trợ và chưa thử |

Chưa kiểm tra: fractional scaling và nhiều màn hình có scale khác nhau. Qt/XWayland xử lý toạ độ ở các trường hợp này khác nhau, nên pet có thể lệch vị trí so với cửa sổ.

## Cài đặt

Cần Python ≥ 3.10 và Linux. Chưa có bản phát hành dựng sẵn, nên hiện tại bạn tự build (một lệnh, khoảng 15 giây, cần mạng lần đầu):

```sh
git clone https://github.com/longtmb2003/desktop-pet
cd desktop-pet
scripts/build.sh                 # tạo dist/mochi/ (~160 MB, chạy được không cần cài Python)
scripts/install.sh --autostart   # cài cho riêng bạn vào ~/.local; bỏ --autostart nếu không muốn tự chạy khi đăng nhập
```

`install.sh` không cần quyền root. Nó chép ứng dụng vào `~/.local/opt/mochi`, tạo lệnh `mochi`, mục trong menu ứng dụng (không mở terminal) và icon. Nếu bạn từng tạo `~/.config/autostart/mochi-pet.desktop` theo cách chạy `pet.py` cũ, script sẽ đổi tên nó thành `.disabled` để khỏi chạy hai bản.

Tiến trình chạy nền có tên `mochi`, hiện đúng tên đó trong System Monitor (`pgrep -x mochi`). Mochi chỉ chạy một bản: chạy lần hai sẽ báo `already running` và thoát.

## Tự chạy khi đăng nhập

Bật/tắt bằng menu chuột phải ("Tự chạy khi đăng nhập") hoặc dòng lệnh:

```sh
mochi autostart on       # tạo ~/.config/autostart/mochi.desktop
mochi autostart off
mochi autostart status
```

## Gỡ cài đặt

```sh
scripts/uninstall.sh             # gỡ ứng dụng, lệnh, menu, icon và autostart
scripts/uninstall.sh --purge     # như trên, và xoá luôn cài đặt đã lưu (màu…)
```

Hoặc chỉ dừng Mochi mà giữ lại: chuột phải → Thoát (hoặc `pkill -x mochi`).

## Phát triển

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python -m mochi                  # chạy từ mã nguồn (`python3 pet.py` cũ vẫn chạy, nhưng chỉ là lối tắt)
ruff check . && mypy mochi && pytest
```

Test chạy không cần màn hình (`QT_QPA_PLATFORM=offscreen`). CI (GitHub Actions) chạy ruff, mypy, pytest và một smoke test khởi động trên Python 3.10 và 3.13.

```
mochi/
├── app.py        điểm vào, dòng lệnh (`mochi autostart …`)
├── pet.py        widget: hành vi, vòng lặp vật lý theo thời gian thực, chuột, menu
├── state.py      Motion × Expression × Action, thời lượng và quy tắc chuyển trạng thái
├── physics.py    hình học thuần (chọn bề mặt, cửa sổ bị che, nhảy), không phụ thuộc Qt
├── renderer.py   vẽ vector, màu, vùng click
├── settings.py   lưu cài đặt (QSettings)
├── autostart.py  mục autostart XDG
└── platform/     nguồn thông tin cửa sổ: base (chỉ sàn) và kde (KWin qua DBus, kwin.js)
```

Build lại icon / ảnh xem trước: `python scripts/make_icon.py`, `python scripts/make_preview.py`.

## Cách hoạt động và quyền truy cập thông tin cửa sổ

- Trên Wayland, app thường không được tự đặt vị trí cửa sổ, nên Mochi ép Qt chạy qua XWayland (`QT_QPA_PLATFORM=xcb`), và chỉ làm vậy khi có `WAYLAND_DISPLAY`.
- Để biết vị trí các cửa sổ khác, Mochi nạp `kwin.js` vào KWin qua DBus. Script này chạy **bên trong KWin**, nên có quyền đọc mọi cửa sổ, nhưng nó chỉ gửi cho Mochi **id nội bộ và toạ độ/kích thước** của các cửa sổ thường đang hiển thị (không gửi tiêu đề, nội dung hay tên ứng dụng), theo thứ tự xếp chồng, và chỉ khi có thay đổi.
- Dữ liệu đi qua session bus tại dịch vụ `org.mochi.Pet`. Bất kỳ tiến trình nào trong phiên của bạn cũng gọi được dịch vụ này, nên Mochi kiểm tra từng bản tin (bỏ mục sai, từ chối bản tin không phải danh sách, giới hạn log) và không bao giờ bị crash vì dữ liệu xấu.
- Khi thoát bình thường, Mochi gỡ script khỏi KWin. Nếu bị crash, script còn sót sẽ được gỡ ở lần chạy sau.
- Giới hạn của KWin API: chỉ các cửa sổ `normalWindow` được xét; popup, panel, tooltip không tính. Cửa sổ rộng dưới 80 px không dùng làm chỗ đứng.
- Ngoài KDE hoặc khi KWin/DBus không có, pet vẫn chạy và chỉ đi trên sàn màn hình.

## Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| `mochi: already running` | Đã có một bản đang chạy. Dừng nó: `pkill -x mochi` |
| Pet không đứng lên cửa sổ | Kiểm tra script đã nạp: `gdbus call --session --dest org.kde.KWin --object-path /Scripting --method org.kde.kwin.Scripting.isScriptLoaded mochi` phải in `(true,)`. Chạy `mochi` từ terminal để xem log |
| `Could not load the Qt platform plugin "xcb"` | Thiếu thư viện hệ thống: Fedora `sudo dnf install xcb-util-cursor`, Debian/Ubuntu `sudo apt install libxcb-cursor0` |
| Pet kẹt ngoài màn hình | Chuột phải → "Gọi về". Nếu không chạm được vào pet: `pkill -x mochi` rồi chạy lại. Khi rút màn hình, pet tự về màn hình chính |
| Không có KDE | Bình thường: chế độ floor-only, chỉ đi trên sàn |

## Lộ trình

- **v0.2 (bản này):** ổn định, tách kiến trúc, đóng gói.
- **v0.3:** ném pet bằng chuột (quán tính), va chạm cạnh màn hình, chóng mặt, lắc, double-click lộn vòng, hoảng sợ khi cửa sổ biến mất.
- **v0.4:** bong bóng thoại, Pomodoro, phản ứng theo giờ/CPU, API DBus thông báo, cửa sổ Settings và Quiet Mode.
- **v0.5:** nhiều pet / linh thú với hành vi và hình dạng riêng.

## License

MIT
