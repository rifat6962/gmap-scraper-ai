# Playwright-এর অফিসিয়াল ইমেজ (সব লিনাক্স ফাইল আগে থেকেই আছে)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# রিকোয়ারমেন্টস কপি করা
COPY requirements.txt .

# প্যাকেজ ইন্সটল করা (কোনো sudo বা root লাগবে না)
RUN pip install --no-cache-dir -r requirements.txt

# শুধু ব্রাউজার ইন্সটল করা
RUN playwright install chromium

# প্রজেক্টের সব ফাইল কপি করা
COPY . .

# রান করার কমান্ড (এখানেই Start Command দেওয়া আছে, Render-এ লিখতে হবে না)
CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
