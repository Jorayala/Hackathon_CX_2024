# Usar la imagen oficial de AWS Lambda con Python 3.11
FROM public.ecr.aws/lambda/python:3.11

# Copiar los archivos de la función al contenedor
COPY . ${LAMBDA_TASK_ROOT}

# Instalar las dependencias
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt -t ${LAMBDA_TASK_ROOT}

# Configurar el handler de Lambda
CMD ["lambda_functionBedrock.main"]







