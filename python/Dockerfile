FROM python:3.11.5-alpine

RUN addgroup -S mercari && adduser -S trainee -G mercari
# RUN chown -R trainee:mercari /path/to/db

USER trainee

WORKDIR /python

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade pip setuptools wheel

# CMD ["sleep", "inf"] 
# CMD ["uvicorn", "main:app",  "--reload",  "--port",  "9000"]
CMD ["/home/trainee/.local/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]