cd database
sudo docker-compose up -d
cd ..
source .venv/bin/activate
uvicorn cinecloud.asgi:application --reload

