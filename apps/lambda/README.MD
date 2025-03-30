
## Docker Build  
```bash 
docker build --platform=linux/amd64 -t 536697256393.dkr.ecr.us-east-1.amazonaws.com/ingestion-pipeline-lambda:latest .
```

## Docker Push 
```bash
docker push ${aws_ecr_repository.lambda_repo.repository_url}:latest
```