# Dockerfile
# Ubuntu asosidagi Python 3.10 slim tasvirini ishlatish (GPU siz muhit uchun)
FROM python:3.10-slim-buster

# Ishlayotgan katalog
WORKDIR /app

# Loyiha tuzilmasini yaratish
RUN mkdir -p /app/data/raw_videos /app/runs/train/exp_fast_train3/weights /app/results /app/static /app/templates

# Tizim bog'liqliklarini o'rnatish
# Bu OpenCV, Scipy, Numpy kabi kutubxonalarning to'g'ri o'rnatilishi uchun zarur.
# libGL.so.1 xatosini tuzatish uchun yangi qo'shimchalar: libgl1-mesa-glx libglib2.0-0
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libgtk2.0-dev \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfreetype6-dev \
    libssl-dev \
    gfortran \
    libatlas-base-dev \
    liblapack-dev \
    libblas-dev \
    # ============== YANGI QO'SHILGANLAR ==============
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg  \
    # ===============================================
    && rm -rf /var/lib/apt/lists/*

# kerakli Python kutubxonalarini nusxalash
COPY requirements.txt .

# PyTorch va Torchvisionni CPU versiyasi uchun o'rnatish
RUN pip install --no-cache-dir torch==2.5.0 torchvision==0.20.0 -f https://download.pytorch.org/whl/torch_stable.html
# Keyin requirements.txt dagi qolgan kutubxonalarni o'rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Modelni nusxalash
COPY runs/train/exp_fast_train3/weights/best.pt /app/runs/train/exp_fast_train3/weights/best.pt

# Data papkasini (va ichidagi tr.mp4 ni) nusxalash
COPY data/ /app/data/

# Frontend fayllarini nusxalash
COPY landing.html /app/templates/landing.html
COPY static/tr.mp4 /app/static/tr.mp4

# Python skriptlarini nusxalash
COPY main.py /app/main.py
COPY infer_and_track_violations.py /app/infer_and_track_violations.py

# Natijalarni saqlash uchun katalog
VOLUME /app/results

# Ilova ishlaydigan portni ochish
EXPOSE 8000

# Ilovani ishga tushirish
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]