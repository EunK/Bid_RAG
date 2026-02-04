import shutil
import uuid
from google.genai import types
import fitz  # PyMuPDF
import re
import os
from typing import Dict, Any, Optional
from services.gemini_client import get_client

def get_all_indices(pattern, text):
    # re.escape는 패턴에 특수문자(괄호 등)가 있을 경우를 대비해 안전하게 처리합니다.
    return [m.start() for m in re.finditer(re.escape(pattern), text)]

# 실행 예시

def split_law_and_enforcement_decree(file_path, output_dir):
    # 1. PDF 텍스트 추출
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 2. 법률과 시행령의 시작 지점 찾기
    # 문서 내에 나타나는 정확한 명칭을 기준으로 인덱스를 찾습니다.
    law_start_pattern = "지방자치단체를당사자로하는계약에관한법률"
    decree_start_pattern = "지방자치단체를당사자로하는계약에관한법률시행령"

    first_position_title = full_text.find(law_start_pattern)
    first_position_contents = full_text.find(law_start_pattern, first_position_title + 1)

    second_position_title = full_text.find(decree_start_pattern)
    second_position_contents = full_text.find(decree_start_pattern, second_position_title + 1)


    # 세그먼트 분리
    segments = []
    if first_position_title != -1:
        segments.append(("법률_목차", full_text[:first_position_contents]))
        segments.append(("법률_내용", full_text[first_position_contents:second_position_title]))
        segments.append(("시행령_목차", full_text[second_position_title:second_position_contents]))
        segments.append(("시행령_내용", full_text[second_position_contents:]))
    else:
        segments.append(("미분류", full_text))

    client = get_client()
    
    for category, text in segments:
        if "목차" in category:
            # print(f"{category} 세그먼트 내용: {text[:200]}")
            file_name = f"{category}.txt"
            save_path = os.path.join(output_dir, file_name)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"[{category}]\n\n{text}")
        else:
            clause_pattern = re.compile(r'(제\d+조(?:의\d+)?\(.*?\))')
            chunks = clause_pattern.split(text)
            # chunks[0]은 조항 시작 전의 제목/서문 영역
            for i in range(1, len(chunks), 2):
                title = chunks[i].strip()
                content = chunks[i+1].strip()
                
                # 파일명 규칙: [법령구분]_[조항명].txt
                safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
                file_name = f"{category}_{safe_title}.txt"
                
                save_path = os.path.join(output_dir, file_name)
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(f"[{category}]\n{title}\n\n{content}")
    # return


    # print(f"{first_position_title} , {first_position_contents},{second_position_title}, {second_position_contents}")
    


    # # 3. 각 세그먼트 내에서 조항별로 분할 및 저장
    # # 조항 패턴: 제1조, 제1조의2, 제100조 등 대응
    # clause_pattern = re.compile(r'(제\d+조(?:의\d+)?\(.*?\))')

    # for category, text in segments:
    #     chunks = clause_pattern.split(text)
        
    #     # chunks[0]은 조항 시작 전의 제목/서문 영역
    #     for i in range(1, len(chunks), 2):
    #         title = chunks[i].strip()
    #         content = chunks[i+1].strip()
            
    #         # 파일명 규칙: [법령구분]_[조항명].txt
    #         safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    #         file_name = f"{category}_{safe_title}.txt"
            
    #         save_path = os.path.join(output_dir, file_name)
    #         with open(save_path, "w", encoding="utf-8") as f:
    #             f.write(f"[{category}]\n{title}\n\n{content}")

    print(f"분할 완료: {output_dir} 폴더를 확인하세요.")


def upload_file(store_name, output_dir):
    file_list = os.listdir(output_dir)
    for file_name in file_list:
        if not file_name.endswith('.txt'):
            continue
        file_extension = os.path.splitext(file_name)[1]
        safe_temp_filename = f"{uuid.uuid4()}{file_extension}"

        os.makedirs("temp", exist_ok=True)
        temp_file_path = os.path.join("temp", safe_temp_filename)

        full_path = os.path.join(output_dir, file_name)
        shutil.copyfile(full_path, temp_file_path)

        client = get_client()
        category_name = "법령" if "법률" in file_name else "시행령"
        if "목차" in file_name:
            config = {
                "display_name": f"{category_name} 관련 문서 통합 인덱스",
                "custom_metadata": [
                    {"key": "content_type", "string_value": "summary"},
                    {"key": "scope", "string_value": "index"}
                ],
            }
            op = client.file_search_stores.upload_to_file_search_store(
                file=temp_file_path,
                file_search_store_name=store_name,
                config=config,
                )
        else:
            new_name = file_name.removesuffix(".txt")
            config = {
                "display_name": f"{new_name} 조항 상세",
                "custom_metadata": [
                    {"key": "doc_id", "string_value": f"{new_name}"},
                    {"key": "scope", "string_value": "detail"},
                    {"key": "content_type", "string_value": "legal_text"},
                ],
            }
                # 업로드 실행
            op2 = client.file_search_stores.upload_to_file_search_store(
                file=temp_file_path,
                file_search_store_name=store_name,
                config=config,
            )
            
        print(f"Uplaod 완료: {full_path}")

    print(f"분할 완료: {output_dir} 폴더를 확인하세요.")


# split_law_and_enforcement_decree(file_path="2_ALL.pdf", output_dir="./law_chunks")

upload_file(store_name="fileSearchStores/starbillmainstores-p0oxu3imunips", output_dir="./law_chunks")