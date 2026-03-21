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


def run(command):
    res = sub.run(command,check=True,capture_output=True,timeout=4,encoding="utf-8",shell=True)
    return res.stdout

if __name__ == "__main__":
    wh_py = run("where python").strip().split("\n")
    wh_pip = run("where pip").strip().split("\n")
    if len(wh_py) == 1:
        print("发现1个Python版本")
        print(f"版本号：{run(str(wh_py[0])+' --version').strip()}")
    elif len(wh_py) == 0:
        print("OoO? 未发现Python")
    else:
        print(f"OoO? 发现多个Python版本，{len(wh_py)}个")
        print(f"路径：")
        for i in range(len(wh_py)):
            print('第',i+1,'个：',wh_py[i])
        for i in range(len(wh_py)):
            try:
                print(f'第{i+1}个，版本号：{run(str(wh_py[i])+" --version").strip()}')
            except:
                print(f'第{i+1}个，无效的python，建议清理')

    print("\n")

    if len(wh_pip) == 1:
        print("发现1个pip版本")
        print('路径：',wh_pip[0])
    elif len(wh_pip) == 0:
        print("OoO? 未发现pip")
    else:
        print(f"OoO? 发现多个pip版本，{len(wh_pip)}个")
        print(f"路径：")
        for i in range(len(wh_pip)):
            print('第',i+1,'个：',wh_pip[i])
    
