# ⚡ AI 에이전트

## 🔧 환경설정

### 1️⃣ `.env` 파일 생성
프로젝트 **루트 디렉토리 (PROJECT ROOT)** 에 `.env` 파일을 생성하고 아래 내용을 입력합니다.
```env
GOOGLE_API_KEY=Google API 키 값
FILE_SEARCH_STORE_NAME=
FILE_SEARCH_STORE_DISPLAY_NAME=starbill-main-store
GEMINI_API_KEY : Gemini API 키 값
```

### 2️⃣ 스토어 생성 및 설정
아래 명령어를 실행합니다.

```
python manage_store.py
```

실행 후 출력되는 store.name 값을 복사하여
.env 파일의 FILE_SEARCH_STORE_NAME 항목에 입력합니다.

### 3️⃣ API 실행
  프로젝트 root terminal 에서 실행
```
 uvicorn api.main:app --reload
```
### 4️⃣ Swagger
  api service 실행후 
  `http://api domain:8000/docs` 로 접근


