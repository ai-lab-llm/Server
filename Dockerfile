FROM python:3.10-slim

# 작업 디렉토리
WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 복사
COPY . .

# Hugging Face 캐시 디렉토리 환경 변수 설정
ENV HF_HOME=/hf_cache

# 컨테이너 시작 시 실행 명령
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
