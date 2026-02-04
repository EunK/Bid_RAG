import datetime
import inspect
import sys

def log(message):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 호출한 곳의 정보를 가져옴
    caller = inspect.stack()[1]
    func_name = caller.function
    file_name = caller.filename.split('/')[-1] # 파일명만 추출
    
    print(f"[{now}] [{file_name} > {func_name}] {message}")