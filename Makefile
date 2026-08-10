.PHONY: install run-api run-ui test lint eval docker-up docker-down k8s-deploy

install:
	pip install -r requirements.txt

run-api:
	uvicorn app.api:app --reload --port 8000

run-ui:
	API_URL=http://localhost:8000 streamlit run ui/streamlit_app.py

test:
	pytest -q

lint:
	ruff check .

eval:
	python -m eval.run_eval

docker-up:
	docker compose up --build

docker-down:
	docker compose down

k8s-deploy:
	kubectl apply -f k8s/
