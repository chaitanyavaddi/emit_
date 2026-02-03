.PHONY: setup migrate seed clean

migrate-create:
	alembic revision --autogenerate -m "$(name)"

migrate-up:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
