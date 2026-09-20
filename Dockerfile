FROM python:3.12.10

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py shell -c \"from django.contrib.auth import get_user_model; User=get_user_model(); User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists() or User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')\" && gunicorn ecom.wsgi:application --bind 0.0.0.0:8000"]
