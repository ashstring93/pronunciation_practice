import qrcode

# 1) QR에 담을 URL
url = "https://yourapp.com"

# 2) QR 코드 만들기
qr = qrcode.QRCode(
    version=1,            # 코드 크기
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,          # 한 칸 픽셀 크기
    border=4,             # 바깥 여백 칸 수
)

qr.add_data(url)
qr.make(fit=True)

# 3) PNG 파일로 저장
img = qr.make_image(fill_color="black", back_color="white")
img.save("qr_homepage.png")

print("✅ qr_homepage.png 파일이 생성되었어요!")
