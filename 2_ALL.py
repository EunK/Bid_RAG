import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def get_or_create_store():
    """
    1. 현재 접근 가능한 모든 스토어를 조회합니다.
    2. 동일한 Display Name을 가진 스토어가 있다면 그 이름을 반환합니다.
    3. 없다면 새로 생성합니다.
    """
    display_name = os.getenv("FILE_SEARCH_STORE_DISPLAY_NAME")
    try:
        # [STEP 1] 전체 목록 조회
        print("🔍 기존 스토어 목록 확인 중...")
        stores = client.file_search_stores.list()
        
        if stores:
            for store in stores:
                if store.display_name == display_name:
                    print(f"✅ 기존 스토어를 찾았습니다: {display_name}")
                    return store.name
        
        # [STEP 2] 스토어가 없으면 새로 생성
        print(f"➕ '{display_name}' 스토어가 없어 새로 생성합니다...")
        
        # 인자 오류를 피하기 위해 가장 표준적인 config 방식으로 생성
        new_store = client.file_search_stores.create(
            config=types.FileSearchStore(
                display_name=display_name
            )
        )
        
        print(f"✨ 새 스토어가 생성되었습니다!")
        return new_store.name

    except Exception as e:
        print(f"🚨 오류 발생: {e}")
        return None

if __name__ == "__main__":
    store_full_path = get_or_create_store()
    
    if store_full_path:
        print("\n" + "="*50)
        print("🚩 아래의 Full Name을 .env 파일의 FILE_SEARCH_STORE_NAME에 복사하세요:")
        print(f"\nFILE_SEARCH_STORE_NAME={store_full_path}")
        print("="*50)