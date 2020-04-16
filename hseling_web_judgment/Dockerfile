FROM python:3.7
WORKDIR /app
COPY . .
RUN pip install -r hseling_web_judgment/requirements.txt
EXPOSE 8000
CMD ["python3", "hseling_web_judgment/manage.py", "runserver", "0.0.0.0:8000"]