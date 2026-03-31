# Playwright-এর অফিসিয়াল ইমেজ, যেখানে সব OS পারমিশন আগে থেকেই আছে
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# ওয়ার্কিং ডিরেক্টরি
WORKDIR /app

# রিকোয়ারমেন্টস কপি করা
COPY requirements.txt .

# পাইথন প্যাকেজ ইন্সটল করা
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn eventlet

# শুধু ক্রোমিয়াম ব্রাউজার ইন্সটল করা
RUN playwright install chromium

# প্রজেক্টের সব ফাইল কপি করা
COPY . .

# অ্যাপ রান করার কমান্ড
CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
