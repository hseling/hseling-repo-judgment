FROM python:3.7
WORKDIR /app
COPY . .
RUN pip install -r hseling_api_judgment/requirements.txt

EXPOSE 5000
CMD ["python3", "hseling_api_judgment/app.py"]