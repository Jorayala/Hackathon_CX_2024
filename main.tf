
provider "aws" {
  region     = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

# S3 Bucket
resource "aws_s3_bucket" "hackathon_bucket" {
  bucket = "hackathon-cx-2024"
}

# Subir archivos al bucket
resource "aws_s3_object" "model" {
  bucket = aws_s3_bucket.hackathon_bucket.id
  key    = "model.pkl"
  source = "model.pkl"
}

resource "aws_s3_object" "preprocessed_data" {
  bucket = aws_s3_bucket.hackathon_bucket.id
  key    = "X.csv"
  source = "X.csv"
}

# IAM Role para Lambda
resource "aws_iam_role" "lambda_role" {
  name = "lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

# Políticas IAM para acceso a S3
resource "aws_iam_policy" "s3_access" {
  name = "s3_access_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["s3:GetObject"]
        Effect   = "Allow"
        Resource = "arn:aws:s3:::hackathon-cx-2024/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# Agregar AWSLambdaBasicExecutionRole para permitir logs en CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# CloudWatch Log Group para Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.hackathon_lambda.function_name}"
  retention_in_days = 7
}

# Lambda con contenedor Docker
resource "aws_lambda_function" "hackathon_lambda" {
  function_name = "HackathonCX"
  package_type  = "Image"
  role          = aws_iam_role.lambda_role.arn

  # Subir una imagen Docker con el modelo cargado
  image_uri = "135256798456.dkr.ecr.us-east-1.amazonaws.com/hackathon-lambda:latest"

  memory_size = 512
  timeout     = 60

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.hackathon_bucket.id
    }
  }
}

resource "aws_lambda_permission" "apigateway_invoke_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.hackathon_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${var.aws_account_id}:${aws_api_gateway_rest_api.hackathon_api.id}/*"
}

# API Gateway
resource "aws_api_gateway_rest_api" "hackathon_api" {
  name = "HackathonCXAPI"
}

resource "aws_api_gateway_resource" "predict_resource" {
  rest_api_id = aws_api_gateway_rest_api.hackathon_api.id
  parent_id   = aws_api_gateway_rest_api.hackathon_api.root_resource_id
  path_part   = "predict"
}

resource "aws_api_gateway_method" "predict_method" {
  rest_api_id   = aws_api_gateway_rest_api.hackathon_api.id
  resource_id   = aws_api_gateway_resource.predict_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

# Habilitar CORS
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id            = aws_api_gateway_rest_api.hackathon_api.id
  resource_id            = aws_api_gateway_resource.predict_resource.id
  http_method            = aws_api_gateway_method.predict_method.http_method
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.hackathon_lambda.invoke_arn

}

resource "aws_api_gateway_method_response" "method_response" {
  rest_api_id = aws_api_gateway_rest_api.hackathon_api.id
  resource_id = aws_api_gateway_resource.predict_resource.id
  http_method = aws_api_gateway_method.predict_method.http_method

  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Methods" = true
  }
}

# Desplegar API
resource "aws_api_gateway_deployment" "hackathon_deployment" {
  rest_api_id = aws_api_gateway_rest_api.hackathon_api.id
  stage_name  = "default"
}

# Política de acceso público a la API
resource "aws_api_gateway_rest_api_policy" "api_public_policy" {
  rest_api_id = aws_api_gateway_rest_api.hackathon_api.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Principal = "*",
        Action   = "execute-api:Invoke",
        Resource = "arn:aws:execute-api:${var.aws_region}:${var.aws_account_id}:${aws_api_gateway_rest_api.hackathon_api.id}/*"
      }
    ]
  })
}

# CloudWatch Logs Role para API Gateway
resource "aws_iam_role" "apigateway_cloudwatch_role" {
  name = "apigateway-cloudwatch-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apigateway_cloudwatch_policy" {
  role       = aws_iam_role.apigateway_cloudwatch_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Configuración de CloudWatch Logs en API Gateway
resource "aws_api_gateway_account" "apigateway_account" {
  cloudwatch_role_arn = aws_iam_role.apigateway_cloudwatch_role.arn
}

# Configuración del stage para habilitar logs
resource "aws_api_gateway_stage" "stage_logs" {
  rest_api_id  = aws_api_gateway_rest_api.hackathon_api.id
  stage_name   = aws_api_gateway_deployment.hackathon_deployment.stage_name
  deployment_id = aws_api_gateway_deployment.hackathon_deployment.id

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId       = "$context.requestId",
      ip              = "$context.identity.sourceIp",
      httpMethod      = "$context.httpMethod",
      resourcePath    = "$context.resourcePath",
      status          = "$context.status",
      responseLength  = "$context.responseLength",
      integrationTime = "$context.integrationLatency",
    })
  }
}

# CloudWatch Log Group para API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/hackathon-cx-logs"
  retention_in_days = 30
}

output "api_url" {
  value = "https://${aws_api_gateway_rest_api.hackathon_api.id}.execute-api.${var.aws_region}.amazonaws.com/default/predict"
}

