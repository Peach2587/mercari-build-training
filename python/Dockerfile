FROM python:3.11.5-alpine

RUN addgroup -S mercari && adduser -S trainee -G mercari
# RUN chown -R trainee:mercari /path/to/db

USER trainee

CMD ["python", "-V"]
