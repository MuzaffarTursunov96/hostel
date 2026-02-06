FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Asia/Tashkent
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy project
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Setup cron job
COPY cron/crontab /etc/cron.d/notify-debts
RUN chmod 0644 /etc/cron.d/notify-debts \
    && crontab /etc/cron.d/notify-debts

# Create log file
RUN touch /var/log/cron.log

# Start cron
CMD ["cron", "-f"]
