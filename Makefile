# InvestForge Development Commands

.PHONY: help setup dev build test deploy clean

# Default target
help: ## Show this help message
	@echo "InvestForge Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and Development
setup: ## Set up development environment
	@echo "Setting up development environment..."
	cp config/env/.env.example .env
	docker-compose build
	@echo "Setup complete! Run 'make dev' to start development servers."

dev: ## Start development environment
	@echo "Starting development environment..."
	docker-compose up -d
	@echo "Services running:"
	@echo "  📱 Streamlit App: http://localhost:8501"
	@echo "  🌐 Landing Page: http://localhost:8080"
	@echo "  🔌 API: http://localhost:3000"
	@echo "  🗄️  Redis: localhost:6379"
	@echo "  🗃️  DynamoDB: http://localhost:8000"

dev-logs: ## Show development logs
	docker-compose logs -f

stop: ## Stop development environment
	docker-compose down

restart: ## Restart development environment
	docker-compose restart

# Building
build-app: ## Build Streamlit app
	cd app && docker build -t investforge-app .

build-landing: ## Build landing page
	cd landing && npm install && npm run build

build-all: ## Build all components
	@echo "Building all components..."
	make build-app
	make build-landing
	@echo "Build complete!"

# Testing
test-app: ## Run Streamlit app tests
	cd app && python -m pytest tests/ -v

test-api: ## Run API tests
	cd api && python -m pytest tests/ -v

test-all: ## Run all tests
	@echo "Running all tests..."
	make test-app
	make test-api
	@echo "All tests complete!"

# Deployment
deploy-dev: ## Deploy to development environment
	./scripts/deploy.sh development

deploy-staging: ## Deploy to staging environment
	./scripts/deploy.sh staging

deploy-prod: ## Deploy to production environment
	./scripts/deploy.sh production

# Infrastructure
infra-plan: ## Plan infrastructure changes
	cd infrastructure/terraform && terraform plan

infra-apply: ## Apply infrastructure changes
	cd infrastructure/terraform && terraform apply

infra-destroy: ## Destroy infrastructure (careful!)
	cd infrastructure/terraform && terraform destroy

# Utilities
logs-app: ## Show app logs from ECS
	aws logs tail /ecs/financial-analysis --since 1h --follow

logs-api: ## Show API logs from Lambda
	aws logs tail /aws/lambda/investforge-api --since 1h --follow

shell-app: ## Shell into app container
	docker-compose exec app /bin/bash

shell-redis: ## Shell into Redis container
	docker-compose exec redis redis-cli

# Database
db-migrate: ## Run database migrations
	cd api && python scripts/migrate.py

db-seed: ## Seed database with test data
	cd api && python scripts/seed_data.py

# Cleanup
clean-docker: ## Clean Docker containers and images
	docker-compose down -v
	docker system prune -f

clean-all: ## Clean everything (docker, node_modules, __pycache__)
	make clean-docker
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "node_modules" -type d -exec rm -rf {} +

# Security
security-scan: ## Run security scans
	cd app && safety check
	cd api && safety check

# Formatting
format-python: ## Format Python code
	cd app && black . && isort .
	cd api && black . && isort .

format-js: ## Format JavaScript code
	cd landing && prettier --write .

format-all: ## Format all code
	make format-python
	make format-js

# Documentation
docs-serve: ## Serve documentation locally
	cd docs && python -m http.server 8000

# Environment Management
env-copy: ## Copy environment template
	cp config/env/.env.example .env
	@echo "Environment file created. Please edit .env with your settings."

# Quick commands for daily development
quick-start: setup dev ## Quick start for new developers

quick-test: test-all ## Quick test all components

quick-deploy: test-all deploy-dev ## Quick test and deploy to dev