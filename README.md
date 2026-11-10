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
- Pomodoro: chuột phải → Pomodoro → Bắt đầu. Khi tập trung, Mochi ngồi gõ laptop nhỏ (Hà Nhân thì cầm biển đỏ cấm "BẬN" lắc lư: đang bận, đừng làm phiền); hết giờ thì có bong bóng, tiếng chuông và chuyển sang giờ nghỉ (tự đặt độ dài trong Cài đặt)
- Chỉ ngủ khi có lý do, không bao giờ ngủ ngẫu nhiên: lúc bạn khoá màn hình hoặc cho máy ngủ (thức dậy khi mở khoá, có lời chào), ngủ trưa từ 12:00 đến 13:30 và ngủ tối từ 22:00 đến 06:00 (giờ địa phương, chỉnh được trong Cài đặt). Vuốt ve thì nó dậy chơi rồi lại ngủ sau nửa phút; chọn một chế độ (trừ Ngủ) thì nó dậy ngay và không ngủ lại trong khung giờ đó, khung ngủ kế tiếp vẫn bình thường; đang Pomodoro thì nó vẫn ngồi gõ laptop. Từ 22:00 nó còn bớt chạy đuổi
- Máy bận: nếu cài `psutil`, CPU trên 80% thì Mochi toát mồ hôi, đi chậm lại và giảm tốc độ vẽ; xuống dưới 65% mới hết (khoảng giữa hai ngưỡng để không nhấp nháy). Đọc CPU 8 giây một lần
- Chế độ yên lặng: không nói vu vơ, không âm thanh, giảm tốc độ vẽ khi đứng yên. Tự bật khi có ứng dụng toàn màn hình (KDE), tắt được trong Cài đặt
- Nhắc việc do bạn tự đặt: lặp lại sau mỗi N phút ("Uống nước đi!") hoặc hằng ngày vào giờ nhất định, chọn được các ngày trong tuần. Đến hạn Mochi nói câu nhắc bằng bong bóng, nhún nhảy và kêu chuông (trừ khi yên lặng hoặc tắt âm). Chuột phải → Nhắc việc...
- **Báo thức linh hoạt & Báo lại (Snooze)**: Dữ liệu JSON có ID riêng biệt; khi có nhắc nhở, bạn có thể click chuột phải vào pet chọn hoãn lại 5–10 phút (Snooze), trải nghiệm tiện lợi như báo thức điện thoại
- **Hỗ trợ Múi giờ (Timezone)**: Dùng `zoneinfo` chuẩn của Python 3.9+, hỗ trợ chọn múi giờ (`Asia/Ho_Chi_Minh`, `UTC`, v.v.) trong Cài đặt để lịch ngủ và báo thức luôn chuẩn xác cho người dùng làm việc từ xa
- **Giao diện Dark Minimalist (Catppuccin)**: Các hộp thoại Cài đặt, Nhắc việc và menu chuột phải khoác phong cách Catppuccin Mocha tối giản, bo tròn góc 8–10px, hiệu ứng hover nhẹ nhàng, loại bỏ hoàn toàn viền sắc cạnh mặc định của Qt
- **Triết lý "Không làm phiền" (Do Not Disturb)**:
  - *Chống cướp focus tuyệt đối*: Cửa sổ pet và bong bóng thoại dùng cờ `Qt.WindowDoesNotAcceptFocus` và `Qt.WA_ShowWithoutActivating`, không bao giờ cướp con trỏ hay làm ngắt quãng khi bạn đang gõ code hoặc văn bản
  - *Cảnh báo thị giác tinh tế*: Khi đến giờ nhắc việc, Mochi nhún nhảy và hiện huy hiệu icon `!` nhỏ nhắn trên đầu; người dùng rảnh tay có thể click vào để xem
  - *Hiệu ứng chuyển cảnh mềm mại*: Dùng `QPropertyAnimation` (fade-in / fade-out) mượt mà cho bong bóng thoại thay vì bật/tắt đột ngột
  - *Âm thanh êm ái*: Âm chuông/pop cực ngắn và nhẹ nhàng trên Linux, Windows, macOS; tuân thủ nghiêm ngặt chế độ yên lặng (Quiet Mode)
- Chế độ: Bình thường, Làm việc (ngồi gõ laptop suốt, ít nói, không chạy đuổi), Chơi đùa (hiếu động, hay chạy đuổi), Ngủ (ngủ liền, tắt tiếng), Yên lặng; và bạn lưu được cài đặt hiện tại thành chế độ của riêng mình. Đổi nhanh ở chuột phải → Chế độ
- Màn hình nền: thả một file/icon lên Mochi thì nó phản ứng ("Nom nom! báo cáo.pdf ngon quá!"; nó không mở, không di chuyển, không xoá file); thỉnh thoảng nó nhận xét về một mục trên desktop
- Nghịch ngợm trên cửa sổ bạn đang làm việc: khi bạn dùng một cửa sổ được một lúc (trên 15 giây), thỉnh thoảng (mỗi 1 đến 2,5 phút) Mochi nói một câu hợp với ứng dụng đó ("Bug đâu, ra đây!" với trình soạn code, "Mở bao nhiêu tab rồi?" với trình duyệt...), nhảy lên đỉnh cửa sổ và nghịch: nhún nhảy, nhảy múa, ngồi ở mép đung đưa chân, hoặc thò người nhìn xuống. Cửa sổ không đứng được (phóng to hết cỡ, che khuất, quá hẹp) thì nó nghịch ngay ở sàn. Không nghịch khi đang Pomodoro, yên lặng, đang ngủ hay vừa bị bạn vuốt ve; tắt được trong Cài đặt
- Hà Nhân còn mắng bạn: chìa ngón tay chỉ thẳng vào con trỏ chuột, giơ ngón tay lắc "không được đâu", hoặc đi đi lại lại vung tay lên lớp, kèm câu mắng ("Làm việc đi, đừng có lười!")
- Hà Nhân đi hướng nào thì mặt quay hướng đó, đổi chiều thì xoay người lại (không đi lùi)
- Hà Nhân đi là **đạp xe ba bánh**: nhanh gấp đôi, bánh xe quay theo quãng đường, bụi và vạch gió phía sau, nhún nhảy và lấy đà nghiêng người khi quay đầu (xe "drift"), thỉnh thoảng bấm chuông "Ting ting!". Khi mắng hoặc cầm biển, cánh tay vẽ thay cho cánh tay đặt sau lưng trong ảnh gốc (dùng bản ảnh đã cắt cánh tay), nên không bao giờ có hai cánh tay một bên; cánh tay là một ống tay áo thon liền mạch có cổ tay áo trắng và bàn tay 5 ngón, theo tranh gốc của tác giả
- Lời thoại hiện 2,5 đến 5 giây tuỳ độ dài
- Chuột phải: Màu / Chế độ / Pomodoro / Nhắc việc / Chế độ yên lặng / Cài đặt / Nhân vật / Ngủ / Gọi về / Tạm dừng / Tự chạy khi đăng nhập / Thoát

## Nền tảng hỗ trợ

| Môi trường | Trạng thái |
|---|---|
| KDE Plasma 6, Wayland (qua XWayland) | Đầy đủ: đi trên cửa sổ thông qua kwin.js và DBus |
| Windows 10 / 11 | Đầy đủ: Win32 API trực tiếp qua `ctypes` (`EnumWindows`, `GetWindowRect`, DWM cloaked check, phát hiện toàn màn hình, chống chạy đè bằng Named Mutex) |
| macOS | Hỗ trợ qua Quartz / CoreGraphics và Accessibility API |
| Môi trường khác / kẹt quyền | Tự động lui về chế độ an toàn "floor-only" (chỉ đi lại trên sàn màn hình / thanh Taskbar / Dock) |

Chưa kiểm tra: fractional scaling và nhiều màn hình có scale khác nhau. Qt/XWayland xử lý toạ độ ở các trường hợp này khác nhau, nên pet có thể lệch vị trí so với cửa sổ.

## Cài đặt & Chạy nhanh (1 dòng lệnh cho từng OS)

### 🪟 Windows (PowerShell)
Tải, tạo lối tắt khởi động cùng Windows và chạy ngay:
```powershell
irm https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install.ps1 | iex
```
*Hoặc chỉ tải về và chạy file `.exe`:*
```powershell
Invoke-WebRequest -Uri "https://github.com/longtmb2003/desktop-pet/releases/latest/download/mochi.exe" -OutFile "$env:TEMP\mochi.exe"; Start-Process "$env:TEMP\mochi.exe"
```

### 🍎 macOS (Terminal)
Tải, cài đặt vào `/Applications` và mở app:
```bash
curl -fsSL https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install-mac.sh | bash
```

### 🐧 Linux (Terminal)
Tải `mochi.AppImage` vào `~/.local/bin` và chạy ngay:
```bash
curl -fsSL https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install-linux.sh | bash
```

---

## Tải thủ công từ Releases hoặc Tự build

Bạn có thể tải trực tiếp file đóng gói từ mục [Releases](https://github.com/longtmb2003/desktop-pet/releases):
- `mochi.exe`: Windows (click chạy luôn)
- `mochi.dmg`: macOS (kéo vào Applications)
- `mochi.AppImage`: Linux (cấp quyền `chmod +x` và chạy)

Hoặc tự build từ mã nguồn:

```sh
git clone https://github.com/longtmb2003/desktop-pet
cd desktop-pet
scripts/build.sh --onefile       # tạo 1 file duy nhất dist/mochi (đã nén UPX và loại bỏ Qt bloat)
scripts/install.sh --autostart   # cài cho riêng bạn vào ~/.local; bỏ --autostart nếu không muốn tự chạy khi đăng nhập
```

`install.sh` không cần quyền root. Nó chép ứng dụng vào `~/.local/opt/mochi`, tạo lệnh `mochi`, mục trong menu ứng dụng (không mở terminal) và icon. Nếu bạn từng tạo `~/.config/autostart/mochi-pet.desktop` theo cách chạy `pet.py` cũ, script sẽ đổi tên nó thành `.disabled` để khỏi chạy hai bản.

Tiến trình chạy nền có tên `mochi`, hiện đúng tên đó trong System Monitor (`pgrep -x mochi`). Mochi chỉ chạy một bản: chạy lần hai sẽ báo `already running` và thoát.

## Cài đặt

Chuột phải → **Cài đặt...** mở cửa sổ chỉnh: màu, tốc độ đi, tần suất hành vi, chạy đuổi, nói vu vơ, theo giờ trong ngày, âm thanh, theo dõi CPU, chế độ yên lặng (và tự bật khi toàn màn hình), tự chạy khi đăng nhập, độ dài Pomodoro, gọi Mochi về. Thay đổi có hiệu lực ngay và được nhớ (QSettings, `~/.config/mochi-pet/mochi.conf`). Giá trị hỏng trong file được thay bằng mặc định. Chưa có: đổi kích thước pet.

Theo dõi CPU cần `psutil` (bản build sẵn có kèm; chạy từ mã nguồn thì `pip install psutil` hoặc `pip install ".[monitor]"`). Không có psutil thì mọi thứ khác vẫn chạy bình thường.

## Nhắc việc, chế độ và màn hình nền

**Nhắc việc** lưu trong cài đặt (JSON, tối đa 30). Nhắc lặp lại tính bằng đồng hồ đơn điệu, nên máy ngủ đông không làm dồn cục các lần nhắc; nhắc hằng ngày trễ quá 5 phút thì bỏ qua thay vì nhắc muộn. Đang có ứng dụng toàn màn hình (và "Tự yên lặng" bật) thì lời nhắc đợi đến khi hết toàn màn hình.

**Chế độ** là một gói các cài đặt (tần suất, tốc độ, chạy đuổi, nói vu vơ, theo giờ, âm thanh, yên lặng) cộng với việc nghiêng về hành vi nào, hoặc giữ pet mãi ở một việc (ngủ / gõ laptop). Chọn chế độ thì các cài đặt đó được đặt lại theo chế độ; chỉnh tay sau đó vẫn được. Đang Pomodoro thì pet luôn ngồi gõ laptop bất kể chế độ.

**Cửa sổ đang làm việc**: script KWin của Mochi gửi cho pet thêm **id và lớp chương trình** của cửa sổ đang dùng (ví dụ `code`, `firefox`), không bao giờ gửi tiêu đề cửa sổ (vì tiêu đề chứa tên file và tên trang). Mochi chỉ dùng lớp chương trình để chọn câu nói hợp với công việc; không lưu và không gửi đi đâu.

**Màn hình nền**: KDE không cho biết icon nằm ở đâu trên màn hình, và Mochi không tự bật hỗ trợ tiếp cận (AT-SPI) của cả phiên làm việc chỉ để dò icon. Vì vậy Mochi làm việc với **nội dung thư mục desktop** (tên các mục, đọc `Name=` của lối tắt `.desktop`), không với vị trí. Nó không đi tới đứng cạnh từng icon.

## Nhân vật (pet) và gói nhân vật

Ngoài Mochi (vẽ bằng code), Mochi có thể hoá thân thành nhân vật khác: chuột phải → **Nhân vật**, hoặc trong Cài đặt. Liệt kê những gì có: `mochi pets`. Cỡ pet chỉnh trong Cài đặt (60% đến 200%).

Mỗi nhân vật là **dữ liệu**, không phải code: kích thước, tốc độ, hành vi hay làm (trọng số), câu hay nói, tiếng kêu khi mất chỗ đứng, cách vẽ. Nhân vật dạng ảnh ("sprite") là một thư mục có `pack.json` cùng vài file PNG, đặt trong `~/.local/share/mochi-pet/pets/<tên>/`:

```
pack.json        khai báo (xem bên dưới)
body.png         cả người, nền trong suốt, mép dưới chạm sàn, mặt để trống
faces/*.png      các khuôn mặt vẽ đè lên (nét mực trên nền trong suốt): neutral (bắt buộc), talk, laugh
```

```json
{"id": "hanhan", "name": "Hà Nhân", "size": 240, "feet": 232, "height": 200, "walk_speed": 42,
 "body": "body.png", "face": {"box": [69, 162, 198, 172]},
 "faces": {"neutral": ["faces/neutral_00.png"], "talk": ["faces/talk_00.png", "faces/talk_01.png"], "laugh": ["faces/laugh_00.png"]},
 "fps": {"talk": 12}, "behaviors": {"idle": 4, "walk": 4, "sleep": 1, "chase": 1, "rant": 2},
 "chatter": ["Làm việc đi!"], "scream": "Trời ơi!", "sway": 4, "bob": 5, "work_prop": "sign"}
```

Mochi chỉ đọc gói, không chạy code trong đó. Gói sai (thiếu ảnh, số lạ, đường dẫn chui ra ngoài thư mục) bị bỏ qua kèm cảnh báo, không làm Mochi hỏng. Ảnh chỉ được chuyển động bằng phép biến đổi (nhún, nghiêng, lộn, nằm xuống) và đổi mặt; biểu cảm ngủ và chóng mặt do Mochi tự vẽ lên khuôn mặt.

`scripts/make_hanhan.py` là ví dụ dựng một gói từ hai ảnh nguồn (cắt nền, xoá mặt gốc, biến bảng biểu cảm thành lớp mặt trong suốt). Hà Nhân là nhân vật hư cấu do AI tạo ra; ảnh nguồn nằm trong `packaging/` và gói đã dựng sẵn nằm trong `mochi/pets/packs/hanhan/`.

## API DBus cho chương trình khác

Mochi lắng nghe trên session bus, dịch vụ `org.mochi.Pet`, đường dẫn `/pet`, giao diện `org.mochi.Pet`:

| Phương thức | Việc làm |
|---|---|
| `showMessage(s)` | hiện bong bóng (bỏ ký tự điều khiển, tối đa 200 ký tự) |
| `setExpression(s)` | `normal`, `happy`, `dizzy`, `scared`, `tired`; từ chối khi pet đang bị kéo hoặc đang bay |
| `notifyTaskFinished(s)` | bong bóng "Xong rồi: …", pet nhảy mừng, chuông (trừ khi yên lặng hoặc tắt âm) |
| `startPomodoro(i)` | bắt đầu tập trung `i` phút (1 đến 180) |
| `setMode(s)` | đổi chế độ theo tên hoặc id (`normal`, `work`, `play`, `sleep`, `quiet`, hoặc chế độ của bạn) |

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
├── pets/         định nghĩa nhân vật (dữ liệu) và bộ đọc gói ảnh (pack.py)
├── sprite.py     vẽ nhân vật dạng ảnh: chuyển động bằng phép biến đổi, vùng click
├── state.py      Motion × Expression × Action, thời lượng, quy tắc chuyển trạng thái (kể cả theo giờ)
├── physics.py    hình học thuần (bề mặt, cửa sổ bị che, nhảy), ném/nảy, phát hiện lắc; không phụ thuộc Qt
├── bubble.py     bong bóng thoại: cửa sổ riêng, hàng đợi, chọn vị trí
├── pomodoro.py   đồng hồ Pomodoro (logic thuần, đồng hồ tiêm được)
├── monitor.py    đọc CPU (psutil tuỳ chọn) và hysteresis
├── api.py        API DBus công khai (kiểm tra đầu vào, giới hạn tần suất)
├── settings_dialog.py  cửa sổ Cài đặt
├── reminders.py  lịch nhắc việc (logic thuần, đồng hồ tiêm được); reminders_dialog.py là cửa sổ chỉnh
├── modes.py      chế độ (có sẵn và của riêng bạn)
├── desktop.py    các mục trên màn hình nền (tên, mở)
├── sound.py      tiếng chuông (Linux, Windows, macOS)
├── renderer.py   vẽ vector, màu, vùng click
├── style.py      giao diện Catppuccin dark minimalist (QSS)
├── settings.py   lưu cài đặt (QSettings)
├── autostart.py  mục autostart XDG
└── platform/     nguồn thông tin cửa sổ: base (chỉ sàn), kde (KWin), windows (Win32 ctypes) và macos (Quartz)
```

Build lại icon / ảnh xem trước: `python scripts/make_icon.py`, `python scripts/make_preview.py`.

## Cách hoạt động và quyền truy cập thông tin cửa sổ

- Trên Wayland, app thường không được tự đặt vị trí cửa sổ, nên Mochi ép Qt chạy qua XWayland (`QT_QPA_PLATFORM=xcb`), và chỉ làm vậy khi có `WAYLAND_DISPLAY`.
- Để biết vị trí các cửa sổ khác:
  - **Linux (KDE Plasma)**: Mochi nạp `kwin.js` vào KWin qua DBus. Script này chỉ gửi id nội bộ và toạ độ của cửa sổ đang hiển thị theo thứ tự xếp chồng, không đọc tiêu đề hay nội dung.
  - **Windows**: Mochi gọi trực tiếp Win32 API (`EnumWindows`, `GetWindowRect`) qua module `ctypes` chuẩn, kiểm tra cửa sổ ảo DWM (`DWMWA_CLOAKED`) và trạng thái toàn màn hình.
  - **macOS**: Sử dụng Quartz / Accessibility API để lấy toạ độ các cửa sổ đang mở.
- Ngoài KDE/Windows hoặc khi kẹt quyền truy cập, Mochi tự động lui về chế độ an toàn `floor-only` (chỉ đi lại trên sàn màn hình / thanh Taskbar / Dock).

## Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| `mochi: already running` | Đã có một bản đang chạy. Dừng nó: `pkill -x mochi` (trên Windows: tắt qua Task Manager) |
| Pet không đứng lên cửa sổ | Trên KDE: kiểm tra script đã nạp (`gdbus call --session --dest org.kde.KWin --object-path /Scripting --method org.kde.kwin.Scripting.isScriptLoaded mochi`). Trên Windows/macOS: đảm bảo app có quyền truy cập cửa sổ desktop |
| `Could not load the Qt platform plugin "xcb"` | Thiếu thư viện hệ thống: Fedora `sudo dnf install xcb-util-cursor`, Debian/Ubuntu `sudo apt install libxcb-cursor0` |
| Pet kẹt ngoài màn hình | Chuột phải → "Gọi về". Nếu không chạm được vào pet: `pkill -x mochi` rồi chạy lại. Khi rút màn hình, pet tự về màn hình chính |
| Không có KDE / Windows API | Bình thường: chế độ floor-only, chỉ đi trên sàn |

## Lộ trình

- **v0.2:** ổn định, tách kiến trúc, đóng gói. (xong)
- **v0.3:** ném pet bằng chuột (quán tính), va chạm cạnh màn hình, chóng mặt, lắc, double-click lộn vòng, hoảng sợ khi cửa sổ biến mất, đẩy tường. (xong)
- **v0.4:** bong bóng thoại, Pomodoro, phản ứng theo giờ/CPU, API DBus, cửa sổ Cài đặt và chế độ yên lặng. (xong)
- **v0.5:** nhân vật là dữ liệu: đổi được giữa Mochi và các gói ảnh (như Hà Nhân), mỗi nhân vật có cỡ, tốc độ, hành vi, lời thoại riêng; chỉnh cỡ pet. Chưa có: nhiều pet chạy cùng lúc. (xong)
- **v0.6:** nhắc việc tự đặt, chế độ có sẵn và tự tạo, tương tác với các mục trên màn hình nền (thả file, mở, nhận xét), lời thoại lâu hơn. (xong)
- **v0.7:** Hà Nhân đạp xe ba bánh, tay vẽ có ống tay áo thon và bàn tay 5 ngón (mắng người, cầm biển "BẬN"), nghịch ngợm trên cửa sổ đang làm việc, lịch ngủ (khoá màn hình, ngủ trưa, ngủ tối), mặt cười lộ răng. (xong)
- **v0.8 (bản này):** Giao diện Dark Minimalist phong cách Catppuccin Mocha, Báo thức linh hoạt có ID & Báo lại (Snooze 5–10 phút), Hỗ trợ Múi giờ (`zoneinfo`), Triết lý không làm phiền (chống cướp focus tuyệt đối, icon `!` tinh tế, fade-in/fade-out), Đa nền tảng Windows (`ctypes`) & macOS, Đóng gói 1-file click-to-run nén UPX và CI/CD GitHub Actions.

## License

MIT
