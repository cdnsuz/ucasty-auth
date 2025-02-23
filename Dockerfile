# 
FROM python:3.9

# 
WORKDIR /customer_telegrambot

# 
COPY ./requirements.txt ./

# 
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 
COPY . .

# 
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9020"]
