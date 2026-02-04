import time
from datetime import timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import datetime
from urllib import response

from google.genai import types
from .gemini_client import get_client
from api.schemas import BiddingNoticeResponse
from logger import log

# 사용법


client = get_client()

def get_system_instruction() -> str:
    # 현재 파일의 위치를 기준으로 prompts/system_v1.txt 경로 계산
    base_path = Path(__file__).parent.parent
    prompt_path = base_path / "prompts" / "system_v1.txt"
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        # 파일이 없을 경우를 대비한 기본값 또는 에러 처리
        return "기본 시스템 지시사항입니다."

# 입찰 조달문서 도우미 전용 프롬프트
SYSTEM_INSTRUCTION = get_system_instruction()

def query_rag(
    user_query: str, 
    store_name: str, 
    model: str = "gemini-2.5-flash",
    temperature: float = 0.1
) -> Optional[BiddingNoticeResponse]:
    """문서 기반 질의응답 실행"""

    # 인덱스 범위 내에서만 검색하도록 설정

    index_tool = types.Tool(
        file_search=types.FileSearch(
            file_search_store_names=[store_name],
            metadata_filter="scope=index",
        )
    )
    # 2. 딕셔너리 형태로 필터 구성 (가장 안전)
    # MetadataFilter 객체 대신 dict를 사용합니다.
    index_filter = {
        "key": "scope",
        "value": "index",
        "operator": "MATCH"
    }
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[index_tool],
        temperature=temperature,
        # tool_config = {
        #     "file_search_config": {
        #         "metadata_filter": [index_filter]
        #     }
        # }
    )   

    log("인덱스 질문 실행 중...")
    # 모델에게 인덱스에서 상세 파일 ID를 찾아내라고 요청
    resp = client.models.generate_content(
        model=model,
        contents="추정가격 1.3억 이상의 입찰 공고문의 입찰기간과 관련된 항목올 알려줘 ",
        config=config
    )
    log("인덱스 질문 완료 중...")
    print("Reason:", resp)
    # File Search Tool 설정
    tool = types.Tool(
        file_search=types.FileSearch(
            file_search_store_names=[store_name]
        )
    )
    
    raw_response_schema = {
        "type": "OBJECT",
        "properties": {
            "sections": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {
                            "type": "STRING",
                            "description": "섹션의 제목"
                        },
                        "items": {
                            "type": "ARRAY",
                            "items": {
                                "type": "STRING"
                            },
                            "description": "섹션 내 상세 항목 리스트"
                        }
                    },
                    "required": ["title", "items"]
                }
            }
        },
        "required": ["sections"]
    }
    
    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[tool],
        # tool_config=types.ToolConfig(
        # function_calling_config=types.FunctionCallingConfig(
        #         mode="AUTO", # 모델이 반드시 도구를 사용하도록 강제
        #     )
        # ),
        temperature=temperature,
        # response_mime_type="application/json",
        # response_schema=raw_response_schema,
    )

    # 답변 생성
    
    log("질의응답 실행 중...")
    resp = client.models.generate_content(
        model=model,
        contents=user_query,
        config=cfg,
    )
    log("질의응답 완료 중...") 
    # # 1. 모델이 툴 호출을 하긴 했는가?
    # # print("Function Calls:", resp.candidates[0].content.parts[0].function_call)
    
    # # 수정 전: print("Function Calls:", resp.candidates[0].content.parts[0].function_call)

    # # 수정 후: 방어적 코드 작성
    # if not resp.candidates:
    #     print("에러: 모델 응답에 candidates가 없습니다.")
    #     print("응답 상태:", resp.prompt_feedback) # 차단 사유 확인 가능
    # else:
    #     candidate = resp.candidates[0]
    #     # if candidate.content and candidate.content.parts:
    #     #     part = candidate.content.parts[0]
    #     #     if hasattr(part, 'function_call') and part.function_call:
    #     #         print("Function Calls:", part.function_call)
    #     #     else:
    #     #         print("텍스트 응답 또는 빈 파트입니다.")
    #     # else:
    #     #     print("Content 또는 Parts가 비어 있습니다. Finish Reason:", candidate.finish_reason)
    #     print("Reason:", resp)
    #     # if candidate.grounding_metadata:
    #     #     # 모델이 참조하려고 했던 문서 조각들 확인
    #     #     print("참조 시도된 텍스트:", candidate.grounding_metadata.grounding_chunks)
    print("Reason:", resp)
    # 결과 파싱
    data = resp.parsed
    try:
        response_obj = BiddingNoticeResponse(
            sections=data.get("sections", [])
        )
        return response_obj
    except Exception as e:
        return None