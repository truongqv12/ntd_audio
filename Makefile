backend:
	cd backend && PYTHONPATH=src uvicorn voiceforge.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd backend && PYTHONPATH=. dramatiq src.voiceforge.tasks

frontend:
	cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port 5173

docker-up:
	docker compose up --build

docker-up-gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build

migrate:
	cd backend && PYTHONPATH=. alembic upgrade head
