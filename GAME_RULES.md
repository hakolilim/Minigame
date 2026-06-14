# Cờ Cá Ngựa - Luật Chơi

## 🎯 Mục Tiêu

Đưa tất cả 4 quân cờ từ nhà xuất phát, đi hết 40 ô trên bảng, vào nhà (4 ô cuối).

## 🏁 Bảng Chơi

```
Nhà (4 ô): [0][1][2][3]
                    ↑
            40 ô chính bảng
```

## 👥 Người Chơi

- 2-4 người chơi
- 4 quân cờ/người
- **3 chế độ**: single (1 bot), double (2 bots), triple (3 bots)

## 🎲 Cách Chơi

### Quân Cờ Chưa Ra Khỏi Nhà
- Bắt đầu ở vị trí -1 (ở nhà)
- **Phải tung được 6** để ra khỏi nhà
- Ra khỏi nhà → quân cờ xuất hiện ở vị trí 0

### Quân Cờ Trên Bảng
- Tung xúc xắc, di chuyển quân cờ **bằng số ô được tung**
- Có thể chọn quân cờ nào để di chuyển (nếu có nhiều cách)
- **Tung được 6**: Chơi tiếp một lần nữa (tối đa 3 lần liên tiếp)

### Quân Cờ Vào Nhà
- Quân cờ tới **ô 40** → vào nhà
- Nhà có **4 ô** (0, 1, 2, 3)
- Phải vào hết 4 ô để hoàn thành
- **Ví dụ**: ở ô 38, tung 4 → vào nhà ở ô 2

## ⚔️ Ăn Quân

Quân cờ của bạn **cùng vị trí** với quân đối thủ → **Bạn ăn nó**!
- Quân cờ bị ăn về nhà (vị trí -1)
- Chiến lược: Ăn quân bot để chậm tiến độ họ

## 🎮 Lệnh

**Bắt đầu**: `/horsechess mode:1 Bot` (hoặc 2/3 Bots)

**Chơi**: Nhấn nút **Quân 0/1/2/3** để di chuyển quân cờ tương ứng

## 💡 Mẹo

1. Ưu tiên ăn quân bot → làm họ chậm lại
2. Tập trung một quân vào nhà trước, rồi chuyển qua quân khác
3. Tung được 6 = may mắn → dùng để ăn quân hoặc tiến xa
4. Chú ý vị trí bot → tránh để họ ăn quân bạn

## ❓ FAQ

**Q: Tôi tung 3, không có quân cờ nào ở nhà để di chuyển?**
A: Đợi tung 6 để quân ra khỏi nhà. Nếu tất cả quân đã ở ngoài, chọn quân nào để di chuyển 3 ô.

**Q: Tung 6 ba lần, có được chơi lần thứ 4 không?**
A: Không! Tối đa 3 lần liên tiếp tung được 6. Lần thứ 3 là giới hạn.

**Q: Quân ở ô 39, tôi tung 5, quân tới đâu?**
A: Quân vào nhà ở ô 4 (39 + 5 = 44, nhà 4 ô → 44 - 40 = 4).

**Q: Làm sao biết thắng?**
A: Tất cả 4 quân ở ô 3 (ô cuối nhà) = bạn thắng. Bot sẽ thông báo: 🎉 Người thắng: YOU!
