# # Sử dụng base image chuẩn của Node.js (phiên bản ổn định)
# FROM node:20-alpine

# USER root

# # Cài đặt FFmpeg, Python và các công cụ biên dịch (g++, make) cần thiết để build các module của n8n
# # (FFmpeg đã nằm sẵn ở đây)
# RUN apk update && \
#     apk add --no-cache ffmpeg python3 py3-pip g++ make python3-dev

# # Cài đặt yt-dlp VÀ edge-tts vĩnh viễn vào hệ thống (Chỉ cần thêm chữ edge-tts vào dòng này)
# RUN pip3 install --no-cache-dir yt-dlp edge-tts --break-system-packages

# # Trả lại quyền chuẩn cho n8n
# USER node

# # Cài đặt hệ thống n8n từ npm
# RUN npm install -g n8n

# # Khởi tạo thư mục và cấp quyền cho user 'node' để chạy an toàn
# RUN mkdir -p /home/node/.n8n && chown -R node:node /home/node

# # Chuyển xuống user node để đảm bảo bảo mật
# USER node
# WORKDIR /home/node

# # Lệnh khởi động n8n
# CMD ["n8n"]


# Dùng lõi hệ điều hành Debian 12 (Bookworm) siêu mới và ổn định kèm Node 20
FROM node:20-bookworm

USER root

# 1. Cập nhật hệ thống và cài đặt FFMPEG, Python3
RUN apt-get update && apt-get install -y ffmpeg python3 python3-pip curl

# 2. Cài đặt n8n phiên bản mới nhất toàn cầu
RUN npm install -g n8n

# 3. Cài đặt các công cụ MMO (TikTok Uploader, Playwright...)
RUN pip3 install tiktok-uploader playwright --break-system-packages

# 4. Tải trình duyệt ngầm Chromium và TẤT CẢ các lõi C++ cần thiết
RUN playwright install chromium chrome --with-deps

# 5. Khởi tạo thư mục và cấp quyền để n8n chạy an toàn
RUN mkdir -p /home/node/.n8n && chown -R node:node /home/node

RUN pip3 install --break-system-packages \
   --index-url https://download.pytorch.org/whl/cpu \
   --extra-index-url https://pypi.org/simple \
   torch \
   torchaudio

RUN pip3 install --break-system-packages \
    soundfile
#    piper-tts

RUN pip3 install --break-system-packages \
   demucs \
   silero-vad

USER node
WORKDIR /home/node

# Lệnh khởi động n8n
CMD ["n8n"]

# docker ps (Lệnh này sẽ liệt kê các container đang chạy. Bạn hãy nhìn cột NAMES để xem tên container n8n của bạn là gì, thường nó sẽ là n8n, n8n-automation-n8n-1 hoặc tương tự).

# Khi đã biết tên, hãy chui vào container bằng quyền cao nhất (root) với lệnh:
# docker exec -u root -it <tên_container_của_bạn> sh

# Cập nhật hệ thống và cài đặt Python:
# apk update
# apk add python3 py3-pip