# 🐾 Mochi - Desktop Pet

<p align="center">
  <b>Một chú pet desktop nhỏ nhắn, thông minh, vẽ hoàn toàn bằng vector, đồng hành cùng bạn khi làm việc.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.8.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-brightgreen.svg" alt="Python">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="License">
</p>

---

![Mochi: 5 màu sắc, biểu cảm vector](docs/preview.png)
<p align="center"><i>5 bảng màu thanh lịch cùng hàng chục biểu cảm vector sắc nét ở mọi độ phân giải màn hình.</i></p>

---

## ⚡ Cài đặt & Chạy nhanh (1 dòng lệnh)

Mở Terminal / PowerShell và dán lệnh tương ứng với hệ điều hành của bạn:

### 🪟 Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install.ps1 | iex
```

### 🍎 macOS (Terminal)
```bash
curl -fsSL https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install-mac.sh | bash
```

### 🐧 Linux (Terminal)
```bash
curl -fsSL https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install-linux.sh | bash
```

> **Tải thủ công:** Truy cập [GitHub Releases](https://github.com/longtmb2003/desktop-pet/releases) để tải trực tiếp file đóng gói sẵn `mochi.exe` (Windows), `mochi.dmg` (macOS), hoặc `mochi.AppImage` (Linux).

---

## ✨ Tính năng nổi bật

### 🐾 Tương tác vật lý sống động
- **Đi trên cửa sổ thực tế**: Nhận diện cửa sổ ứng dụng đang mở (KDE Plasma, Win32 API trên Windows, Quartz trên macOS), trèo lên thanh tiêu đề, nhảy qua lại giữa các cửa sổ hoặc đi lại trên sàn màn hình.
- **Vật lý chân thực**: Kéo thả, ném pet bay theo quán tính, nảy khỏi mép màn hình, chóng mặt khi va chạm mạnh hoặc lắc chuột.
- **Biểu cảm phong phú**: Tự do ngáp, vươn vai, liếm chân, chớp mắt, mắt dõi theo con trỏ chuột, nhảy múa ăn mừng hoặc hoảng sợ khi cửa sổ bên dưới biến mất.

### ⏱️ Pomodoro & Báo thức thông minh
- **Tập trung làm việc (Pomodoro)**: Khi kích hoạt, Mochi sẽ ngồi gõ chiếc laptop mini cùng bạn. Hết giờ sẽ có chuông êm dịu và chuyển sang giờ nghỉ giải lao.
- **Báo thức linh hoạt & Báo lại (Snooze)**: Đặt lời nhắc định kỳ (uống nước, nghỉ mắt) hoặc theo giờ cố định. Hỗ trợ Snooze hoãn lại 5–10 phút tiện lợi như báo thức điện thoại.
- **Hỗ trợ múi giờ (`zoneinfo`)**: Chọn múi giờ linh hoạt trong Cài đặt, chuẩn xác cho người dùng làm việc từ xa.
- **Lịch ngủ tự nhiên**: Mochi ngủ khi màn hình khoá / máy ngủ đông, tự động ngủ trưa (12:00–13:30) và ngủ tối (22:00–06:00).

### 🎨 Giao diện Catppuccin & Triết lý "Không làm phiền"
- **Dark Minimalist**: Cửa sổ Cài đặt, Nhắc việc mang phong cách Catppuccin Mocha hiện đại, bo tròn góc mềm mại.
- **Tuyệt đối không cướp focus**: Cửa sổ pet và bong bóng thoại dùng cờ không nhận focus (`Qt.WindowDoesNotAcceptFocus`), không bao giờ ngắt quãng luồng gõ code hoặc văn bản của bạn.
- **Cảnh báo thị giác tinh tế**: Icon `!` nhỏ nhắn xuất hiện trên đầu khi có lời nhắc; hiệu ứng chuyển cảnh mềm mại fade-in / fade-out.
- **Chế độ yên lặng (Quiet Mode)**: Tự động tắt tiếng và giảm tần suất cử động khi xem phim hoặc mở ứng dụng toàn màn hình.

---

## 🎮 Thao tác điều khiển

| Thao tác | Tác dụng |
|---|---|
| **Chuột trái (click)** | Pet nhảy vui mừng và bay trái tim |
| **Double click** | Pet bật nhảy và lộn vòng 360° trên không |
| **Kéo chuột** | Nhấc pet lên và di chuyển |
| **Hất chuột nhanh** | Ném pet bay theo quán tính |
| **Kéo lắc mạnh** | Làm pet chóng mặt |
| **Thả file lên pet** | Pet "nhai" file và phản ứng vui nhộn |
| **Chuột phải** | Menu tuỳ chọn: Đổi màu, Chế độ, Pomodoro, Nhắc việc, Cài đặt, Ngủ, Gọi về, Thoát |

---

<details>
<summary><b>🔌 DBus API (Dành cho Linux script / automation)</b></summary>
<br>

Mochi cung cấp session bus `org.mochi.Pet` tại đường dẫn `/pet`:
- `showMessage(string)`: Hiện bong bóng thoại.
- `notifyTaskFinished(string)`: Thông báo tác vụ hoàn thành (chuông + nhảy mừng).
- `startPomodoro(int)`: Kích hoạt phiên Pomodoro tập trung.

Ví dụ thông báo khi build xong lệnh trong terminal:
```bash
make -j8 && gdbus call --session --dest org.mochi.Pet --object-path /pet --method org.mochi.Pet.showMessage "Build hoàn tất!"
```
</details>

---

## 🛠️ Tự build từ mã nguồn

Dành cho lập trình viên muốn tinh chỉnh hoặc đóng góp tính năng:

```bash
# 1. Clone kho mã nguồn
git clone https://github.com/longtmb2003/desktop-pet.git
cd desktop-pet

# 2. Tạo môi trường ảo & cài đặt thư viện
python3 -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3. Chạy trực tiếp
python -m mochi

# 4. Đóng gói 1-file độc lập bằng PyInstaller
./scripts/build.sh --onefile
./scripts/install.sh --autostart
```

---

## ❓ Xử lý sự cố thường gặp

| Sự cố | Cách khắc phục |
|---|---|
| **Linux: Thiếu plugin `xcb`** | Cài thư viện hệ thống: `sudo apt install -y libxcb-cursor0` (Ubuntu/Debian) hoặc `sudo dnf install xcb-util-cursor` (Fedora). |
| **`mochi: already running`** | Đã có một tiến trình Mochi đang chạy ngầm. Tắt bằng lệnh `pkill -x mochi` (hoặc qua Task Manager trên Windows). |
| **Pet bị kẹt ngoài màn hình** | Chuột phải vào pet chọn **Gọi về**. |
| **Không trèo lên cửa sổ** | Mochi tự động chuyển sang chế độ an toàn *floor-only* (chỉ đi lại trên sàn / Taskbar / Dock) nếu môi trường không hỗ trợ API cửa sổ. |

---

## 📄 Bản quyền (License)

Dự án được phân phối theo giấy phép mã nguồn mở [MIT License](LICENSE).
