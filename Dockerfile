FROM python:3.8
COPY . /usr/src/app
WORKDIR /usr/src/app

EXPOSE 8501

RUN useradd -s /bin/sh -M -d /usr/src/app python && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

CMD [ "streamlit", "run", "./dashboard.py"]