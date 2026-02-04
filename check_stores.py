# check_stores.py
import os
import shutil
import time
import uuid
from services.file_service import safe_get
from services.gemini_client import get_client, get_default_store_name

client = get_client()
COMPANY = "starbill"
def list_my_stores():
    print("--- 접근 가능한 스토어 목록 ---")
    try:
        # 내 API 키로 볼 수 있는 모든 스토어 나열
        stores = client.file_search_stores.list()
        for s in stores:
            print(f"Name: {s.name}")  # 이 출력값을 복사해서 .env의 STORE_NAME에 넣으세요.
            print(f"Display Name: {s.display_name}")
            print("-" * 30)
    except Exception as e:
        print(f"목록 조회 실패: {e}")

def upload_folder_to_store(store_name: str, folder_path: str, scope: str):
    """지정된 폴더 내의 모든 .txt 파일을 업로드하고 인덱싱 대기"""
    
    # 1. 폴더 내 모든 파일 리스트 가져오기
    files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    
    if not files:
        print(f"폴더에 .txt 파일이 없습니다: {folder_path}")
        return

    # 임시 저장용 폴더 생성
    temp_dir = "upload_tmp"
    os.makedirs(temp_dir, exist_ok=True)

    print(f"총 {len(files)}개의 파일을 업로드 시작합니다...")

    for filename in files:
        original_path = os.path.join(folder_path, filename)
        # 2. 한글 파일명 문제를 피하기 위한 UUID 임시 파일 생성
        file_extension = os.path.splitext(filename)[1]
        safe_temp_filename = f"{uuid.uuid4()}{file_extension}"
        temp_file_path = os.path.join(temp_dir, safe_temp_filename)

        try:
            # 원본 파일을 임시 파일로 복사
            shutil.copy2(original_path, temp_file_path)
            print(f"업로드 중: {filename}...", end="", flush=True)
        
            config = {
                "display_name": filename,
                "custom_metadata": [
                    {"key": "company", "string_value": COMPANY},
                    {"key": "scope", "string_value": scope},
                ],
            }
        
            # 1. 업로드 실행
            op = client.file_search_stores.upload_to_file_search_store(
                file=temp_file_path,
                file_search_store_name=store_name,
                config=config,
            )
        
            # 2. 인덱싱 완료 대기
            while not op.done:
                time.sleep(2)
                # op_name = op if isinstance(op, str) else op.name
                op = client.operations.get(op) # op.name 문자열만 전달
            
            # 3. 결과 확인 및 에러 처리
            if getattr(op, "error", None):
                print(f"\n[오류] {filename} 인덱싱 실패: {op.error}")
            else:
                print(" 완료!")
        except Exception as e:
            print(f"\n[오류] {filename} 업로드 실패: {e}")
            return

        finally:
            # 5. 업로드 후 임시 파일 삭제 (용량 관리)
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    print("\n모든 파일의 업로드 및 인덱싱이 끝났습니다.")

def delete_all_documents(store_name: str):
    docs_service = safe_get(client.file_search_stores, "documents", None)
    if not docs_service:
        print("client.file_search_stores.documents 가 없습니다. SDK 버전을 확인하세요.")
        return
    try:
        documents = docs_service.list(parent=store_name)
        count = 0
        for doc in documents:
            doc_name = doc.name # 예: fileSearchStores/.../documents/...
            try:
                # 2. 개별 문서 삭제 (force=True를 반드시 포함)
                # 에러 메시지로 보아 force 인자가 제대로 전달되지 않으면 'non-empty' 에러가 납니다.
                docs_service.delete(name=doc_name, force=True)
                print(f"삭제 성공: {doc_name}")
                count += 1
            except Exception as e:
                print(f"삭제 실패 ({doc_name}): {e}")
                return
    except Exception as e:
        print(f"목록을 가져오는 중 오류 발생: {e}")
        return




# if __name__ == "__main__":
    # list_my_stores()
    # 실행 예시
    # 스토어 자체를 삭제하는 법 (문서가 들어있어도 스토어 삭제는 보통 가능합니다)
try:
    delete_all_documents(store_name="fileSearchStores/starbillmainstores-p0oxu3imunip")
    print("스토어 삭제 완료. 이제 새로 생성하세요.")
except Exception as e:
    print(f"스토어 삭제 실패: {e}")