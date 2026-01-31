FROM python:3.11-slim

WORKDIR /app

# copy whole project
COPY . /app

# install dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# install cron
RUN apt-get update && apt-get install -y cron

ENV TZ=Asia/Tashkent
RUN apt-get install -y tzdata

# add cron job
COPY cron/crontab /etc/cron.d/notify-debts
RUN chmod 0644 /etc/cron.d/notify-debts
RUN crontab /etc/cron.d/notify-debts

CMD ["cron", "-f"]
