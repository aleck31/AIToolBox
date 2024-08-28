FROM python:3.12-slim
WORKDIR "/webapp"
COPY . .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt
EXPOSE 8886
CMD ["python", "app.py"]