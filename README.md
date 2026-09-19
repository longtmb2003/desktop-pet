# desktop-pet

**Mochi** — một pet desktop nhỏ, nhẹ, vẽ hoàn toàn bằng vector (không cần sprite), dành cho KDE Plasma.

![Mochi: 5 màu, 7 tư thế](docs/preview.png)

![Các tư thế khác: hoảng sợ, làm việc, đẩy tường, lộn vòng, mệt, vui](docs/poses.png)

*Hai ảnh trên do chính bộ vẽ của Mochi render ra (không phải ảnh chụp màn hình). GIF quay từ màn hình thật: chưa có.*

## Tính năng

- Đi lại, ngồi, ngủ (có Zzz), chớp mắt, mắt nhìn theo con trỏ chuột
- Tự chọn ngẫu nhiên các động tác: ngáp, vươn vai, liếm chân, và chạy đuổi theo con trỏ
- Kéo thả để nhấc lên, thả ra thì rơi
- Ném được: hất chuột nhanh rồi thả, pet bay theo vận tốc, nảy khỏi cạnh màn hình/trần/sàn và mất dần năng lượng. Va rất mạnh thì chóng mặt (mắt chữ X, sao quay quanh đầu) và đi loạng choạng vài giây
- Đứng và đi trên đỉnh các cửa sổ (đi theo khi bạn kéo cửa sổ), thỉnh thoảng nhảy lên cửa sổ gần đó; không đứng trên cửa sổ đang bị cửa sổ khác che
- Bấm một lần: pet nhảy lên và bay trái tim (chờ 0,25 giây xem có bấm lần hai không). Bấm đúp: pet lộn một vòng 360° trên không
- Lắc mạnh pet khi đang giữ: pet chóng mặt ngay trong tay bạn
- Cửa sổ đang đứng biến mất (đóng, thu nhỏ, sang màn hình ảo khác): pet hoảng sợ (mắt tròn to, đạp chân, giọt mồ hôi) và rơi ngay
- Đi tới mép cửa sổ/màn hình, đôi khi pet nhắm mắt tì hai chân trước đẩy vào "bức tường" một lúc rồi quay lại hoặc ngồi xuống
- Click xuyên qua phần trong suốt quanh pet
- 5 màu (Kem, Cam, Xám, Bạc hà, Hồng), được nhớ cho lần chạy sau
- Bong bóng thoại: "Á!" khi hoảng sợ, thỉnh thoảng nói vu vơ, báo Pomodoro và thông báo từ chương trình khác. Có hàng đợi (tối đa 5), tự tắt sau vài giây, click xuyên qua, tự chọn bên trái/phải để không tràn màn hình
- Pomodoro: chuột phải → Pomodoro → Bắt đầu. Khi tập trung, Mochi ngồi gõ laptop nhỏ; hết giờ thì có bong bóng, tiếng chuông và chuyển sang giờ nghỉ (tự đặt độ dài trong Cài đặt)
- Theo giờ trong ngày (giờ địa phương): từ 00:00 đến 06:00 dễ ngủ hơn, từ 22:00 bớt chạy đuổi. Không ép ngủ khi bạn vừa chơi với nó
- Máy bận: nếu cài `psutil`, CPU trên 80% thì Mochi toát mồ hôi, đi chậm lại và giảm tốc độ vẽ; xuống dưới 65% mới hết (khoảng giữa hai ngưỡng để không nhấp nháy). Đọc CPU 8 giây một lần
- Chế độ yên lặng: không nói vu vơ, không âm thanh, giảm tốc độ vẽ khi đứng yên. Tự bật khi có ứng dụng toàn màn hình (KDE), tắt được trong Cài đặt
- Chuột phải: Màu / Pomodoro / Chế độ yên lặng / Cài đặt / Ngủ / Gọi về / Tạm dừng / Tự chạy khi đăng nhập / Thoát

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

## Cài đặt

Chuột phải → **Cài đặt...** mở cửa sổ chỉnh: màu, tốc độ đi, tần suất hành vi, chạy đuổi, nói vu vơ, theo giờ trong ngày, âm thanh, theo dõi CPU, chế độ yên lặng (và tự bật khi toàn màn hình), tự chạy khi đăng nhập, độ dài Pomodoro, gọi Mochi về. Thay đổi có hiệu lực ngay và được nhớ (QSettings, `~/.config/mochi-pet/mochi.conf`). Giá trị hỏng trong file được thay bằng mặc định. Chưa có: đổi kích thước pet.

Theo dõi CPU cần `psutil` (bản build sẵn có kèm; chạy từ mã nguồn thì `pip install psutil` hoặc `pip install ".[monitor]"`). Không có psutil thì mọi thứ khác vẫn chạy bình thường.

## API DBus cho chương trình khác

Mochi lắng nghe trên session bus, dịch vụ `org.mochi.Pet`, đường dẫn `/pet`, giao diện `org.mochi.Pet`:

| Phương thức | Việc làm |
|---|---|
| `showMessage(s)` | hiện bong bóng (bỏ ký tự điều khiển, tối đa 200 ký tự) |
| `setExpression(s)` | `normal`, `happy`, `dizzy`, `scared`, `tired`; từ chối khi pet đang bị kéo hoặc đang bay |
| `notifyTaskFinished(s)` | bong bóng "Xong rồi: …", pet nhảy mừng, chuông (trừ khi yên lặng hoặc tắt âm) |
| `startPomodoro(i)` | bắt đầu tập trung `i` phút (1 đến 180) |

Mỗi phương thức trả `true` nếu đã thực hiện, `false` nếu bị từ chối (đầu vào sai, hoặc quá 20 lời gọi trong 10 giây). Ví dụ:

```sh
gdbus call --session --dest org.mochi.Pet --object-path /pet \
  --method org.mochi.Pet.notifyTaskFinished "make -j8"
make -j8 && gdbus call --session --dest org.mochi.Pet --object-path /pet --method org.mochi.Pet.showMessage "Build xong"
```

Bất kỳ tiến trình nào trong phiên của bạn đều gọi được API này (giống mọi dịch vụ session bus), nên nó chỉ làm những việc vô hại: hiện chữ, đổi biểu cảm, bắt đầu đồng hồ.

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
├── state.py      Motion × Expression × Action, thời lượng, quy tắc chuyển trạng thái (kể cả theo giờ)
├── physics.py    hình học thuần (bề mặt, cửa sổ bị che, nhảy), ném/nảy, phát hiện lắc; không phụ thuộc Qt
├── bubble.py     bong bóng thoại: cửa sổ riêng, hàng đợi, chọn vị trí
├── pomodoro.py   đồng hồ Pomodoro (logic thuần, đồng hồ tiêm được)
├── monitor.py    đọc CPU (psutil tuỳ chọn) và hysteresis
├── api.py        API DBus công khai (kiểm tra đầu vào, giới hạn tần suất)
├── settings_dialog.py  cửa sổ Cài đặt
├── sound.py      tiếng chuông
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

- **v0.2:** ổn định, tách kiến trúc, đóng gói. (xong)
- **v0.3:** ném pet bằng chuột (quán tính), va chạm cạnh màn hình, chóng mặt, lắc, double-click lộn vòng, hoảng sợ khi cửa sổ biến mất, đẩy tường. (xong)
- **v0.4 (bản này):** bong bóng thoại, Pomodoro, phản ứng theo giờ/CPU, API DBus, cửa sổ Cài đặt và chế độ yên lặng.
- **v0.5:** nhiều pet / linh thú với hành vi và hình dạng riêng.

## License

MIT
