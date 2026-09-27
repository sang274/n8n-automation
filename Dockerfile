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
FROM node:20-bookworm-slim

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
   ffmpeg python3 python3-pip curl \
   chromium \
   libnss3 libfreetype6 libharfbuzz0b ca-certificates fonts-freefont-ttf \
   libsndfile1 \
   && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

RUN npm install -g n8n

RUN --mount=type=cache,target=/root/.cache/pip \
   pip3 install --break-system-packages \
   yt-dlp edge-tts tiktok-uploader \
   soundfile \
   piper-tts

RUN --mount=type=cache,target=/root/.cache/pip \
   pip3 install --break-system-packages \
   --index-url https://download.pytorch.org/whl/cpu \
   --extra-index-url https://pypi.org/simple \
   torch \
   torchaudio

RUN --mount=type=cache,target=/root/.cache/pip \
   pip3 install --break-system-packages \
   demucs \
   silero-vad

RUN mkdir -p /home/node/.n8n /data/files \
   && chown -R node:node /home/node /data/files

USER node
WORKDIR /home/node
CMD ["n8n"]

# docker ps (Lệnh này sẽ liệt kê các container đang chạy. Bạn hãy nhìn cột NAMES để xem tên container n8n của bạn là gì, thường nó sẽ là n8n, n8n-automation-n8n-1 hoặc tương tự).

# Khi đã biết tên, hãy chui vào container bằng quyền cao nhất (root) với lệnh:
# docker exec -u root -it <tên_container_của_bạn> sh

# Cập nhật hệ thống và cài đặt Python:
# apk update
# apk add python3 py3-pip