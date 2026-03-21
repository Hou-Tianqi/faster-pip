import subprocess as sub
from functools import wraps
import time


def timer(unit='ms'):
    '''
    unit: 's' (秒), 'ms' (毫秒)
    '''
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end = time.perf_counter()
                duration = end - start
                
                # 单位换算
                if unit == 'ms':
                    duration *= 1000
                    unit_str = "毫秒"
                else:
                    unit_str = "秒"
                
                print(f"{func.__name__} 耗时: {duration:.2f} {unit_str}")
        return wrapper
    return decorator

'''
def write_log(th):
    with open("log.log","a",encoding="utf-8")  as f:
        f.write(th+"\n")

def read_log():
    with open("log.log",encoding="utf-8") as f:
        return f.read()


def log(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        try:
            res = func(*args,**kwargs)
            write_log(f"[INFO][{func.__module__}/{func.__name__}]-result :  {res}")
            return res
        except Exception as e:
            write_log(f"[ERROR][{func.__module__}/{func.__name__}]-Exception :  {e}")
            return e
    return wrapper
'''

def run(command):
    res = sub.run(command,check=True,capture_output=True,timeout=4,encoding="utf-8",shell=True)
    return res.stdout

if __name__ == "__main__":
    wh_py = run("where python").strip().split("\n")
    wh_pip = run("where pip").strip().split("\n")
    if len(wh_py) == 1:
        print("发现1个Python版本")
        print(f"版本号：{run(str(wh_py[0] --version))}")
    elif len(wh_py) == 0:
        print("OoO? 未发现Python")
    else:
        print(f"OoO? 发现多个Python版本，{len(wh_py)}个")
    
