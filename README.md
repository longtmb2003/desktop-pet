# desktop-pet

**Mochi** — một pet desktop nhỏ, nhẹ, vẽ hoàn toàn bằng vector (không cần sprite).
## Tính năng

- Đi lại, ngồi, ngủ (có Zzz), chớp mắt, mắt nhìn theo con trỏ chuột
- Tự chọn ngẫu nhiên các động tác: ngáp, vươn vai, liếm chân, và chạy đuổi theo con trỏ
- Kéo thả để nhấc lên, thả ra thì rơi; bấm vào thì nhảy lên và bay trái tim
- Đứng và đi trên đỉnh các cửa sổ (đi theo khi bạn kéo cửa sổ), thỉnh thoảng nhảy lên cửa sổ gần đó
- Click xuyên qua phần trong suốt quanh pet
- 5 màu (Kem, Cam, Xám, Bạc hà, Hồng): chuột phải → Màu, được nhớ cho lần chạy sau
- Chuột phải: Màu / Ngủ / Thoát

## Chạy

Cần Python 3 và PySide6:

```sh
pip install PySide6
python3 -m mochi
```

Tự chạy khi đăng nhập KDE: tạo `~/.config/autostart/mochi-pet.desktop` với `Exec=python3 /đường/dẫn/pet.py`.

## Cách hoạt động

- Trên Wayland, app thường không được tự đặt vị trí cửa sổ, nên `pet.py` ép Qt chạy qua XWayland (`QT_QPA_PLATFORM=xcb`).
- Để biết vị trí các cửa sổ khác, `pet.py` nạp `kwin.js` vào KWin; script này báo vị trí cửa sổ về pet qua DBus. Ngoài KDE, pet vẫn chạy nhưng chỉ đi trên sàn màn hình.

## Chưa làm

- Leo tường / bám cạnh cửa sổ
- Nhiều pet cùng lúc

Đã thử trên Fedora 44, KDE Plasma 6.7 (Wayland), PySide6.

## License

MIT
