#!/bin/bash
# Script to extract exact package versions from the last successful ECR image
# Run this in an environment with Docker access (CodeBuild, EC2, etc.)

# AWS configuration
AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-453636587892}
IMAGE_REPO_NAME=${IMAGE_REPO_NAME:-financial-analysis-app}

# ECR repository URI
REPOSITORY_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_REPO_NAME

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REPOSITORY_URI

echo "Pulling latest image from ECR..."
docker pull $REPOSITORY_URI:latest

echo "Extracting exact package versions..."
docker run --rm $REPOSITORY_URI:latest pip freeze > requirements-locked.txt

echo "=== EXTRACTED PACKAGE VERSIONS ==="
cat requirements-locked.txt
echo "=================================="

echo "Package versions saved to requirements-locked.txt"
echo "Use these exact versions for faster future builds"