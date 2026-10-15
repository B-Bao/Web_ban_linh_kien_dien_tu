@echo off
REM Cai dat & chay du an tren Windows: double-click hoac chay setup.bat
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations accounts catalog orders
python manage.py migrate
python manage.py seed_data
python manage.py runserver
