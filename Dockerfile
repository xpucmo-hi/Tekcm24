FROM python:3.11.1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8080

CMD streamlit run --server.port 8080 tekcm.py