import os
import time
import tempfile
from typing import List, Dict, Any, Iterable
from .gemini_client import get_client


client = get_client()
COMPANY = "starbill"


# ---------------------------------
# Helpers
# ---------------------------------
def safe_get(obj: Any, attr: str, default=None):
    try:
        return getattr(obj, attr)
    except Exception:
        return default

def normalize_meta(meta: Any) -> Dict[str, str]:
    """SDK 버전별로 다른 메타데이터 구조를 dict로 정규화"""
    if meta is None: return {}
    if isinstance(meta, dict): return {str(k): str(v) for k, v in meta.items()}
    
    out = {}
    if isinstance(meta, list):
        for item in meta:
            k = getattr(item, 'key', None) or item.get('key')
            v = getattr(item, 'string_value', None) or item.get('string_value')
            if k and v: out[str(k)] = str(v)
    return out


def list_files(store_name: str, scope: str = None) -> List[Dict[str, str]]:
    """Store 내 문서 목록 조회 및 필터링"""
    rows = []
    # SDK 구조에 맞게 documents.list 호출
    stores = client.file_search_stores.list()
    cnt = len(stores)
    print(f"count: {cnt}")
    for s in stores:
        print(f"Name: {s.name}")  # 이 출력값을 복사해서 .env의 STORE_NAME에 넣으세요.
        print(f"Display Name: {s.display_name}")
        print("-" * 30)

    pager = client.file_search_stores.documents.list(parent=store_name)
    
    for doc in pager:
        meta = normalize_meta(getattr(doc, "custom_metadata", None))
        if meta.get("company") != COMPANY:
            continue
        if scope and meta.get("scope") != scope:
            continue
            
        rows.append({
            "display_name": getattr(doc, "display_name", ""),
            "name": getattr(doc, "name", ""), # document resource name
            "scope": meta.get("scope", "")
        })
    return rows

def upload_to_store(store_name: str, file_path: str, filename: str, scope: str):
    """파일 업로드 및 인덱싱 완료 대기"""

    config = {
        "display_name": filename,
        "custom_metadata": [
            {"key": "company", "string_value": COMPANY},
            {"key": "scope", "string_value": scope},
        ],
    }
    
    # 업로드 실행
    op = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store_name,
        config=config,
    )
    
# 2. 인덱싱 완료 대기
    while not op.done:
        time.sleep(2)
        
        # 수정된 부분: name= 인자를 제거하고 op.name(문자열)만 전달
        # 만약 그래도 에러가 난다면 client.operations.get(op) 로 시도하세요.
        op = client.operations.get(op)
    
    # 3. 결과 확인 및 에러 처리
    if getattr(op, "error", None):
        raise Exception(f"인덱싱 중 오류 발생: {op.error}")

    
    # response 속성이 있으면 반환, 없으면 op 객체 자체 반환
    return getattr(op, "response", op)

def delete_file(document_resource_name: str):
    """특정 문서 삭제"""
    docs_service = safe_get(client.file_search_stores, "documents", None)
    if docs_service is None:
        raise AttributeError("client.file_search_stores.documents 가 없습니다. SDK 버전을 확인하세요.")

    delete_fn = safe_get(docs_service, "delete", None)
    if delete_fn is None:
        raise AttributeError("client.file_search_stores.documents.delete 가 없습니다. SDK 버전을 확인하세요.")

    try:
        delete_fn(name=document_resource_name, force=True)
    except TypeError:
        # SDK 버전에 따라 인자 형태가 다를 수 있어 fallback
        try:
            delete_fn(document_resource_name, force=True)
        except TypeError:
            # 또 다른 버전 형태: config 딕셔너리
            delete_fn(name=document_resource_name, config={"force": True})