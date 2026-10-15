#!/usr/bin/env bash
# Cài đặt & chạy dự án trên Linux / macOS:  bash setup.sh
set -e
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations accounts catalog orders
python manage.py migrate
python manage.py seed_data
python manage.py runserver
