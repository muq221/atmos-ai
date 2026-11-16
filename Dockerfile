FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# build the data + models inside the image so the container starts ready
RUN python -m atmos.pipeline.run && python -m atmos.models.train
ENV ATMOS_SOURCE=sample
EXPOSE 8000
CMD ["uvicorn", "atmos.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
