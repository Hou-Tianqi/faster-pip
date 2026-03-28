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


pip_path = None

def run(command):
    res = sub.run(command,check=True,capture_output=True,timeout=4,encoding="utf-8",shell=True)
    return res.stdout

def pip_run(sub_cmd):
    if pip_path:
        # 适配多个 pip 路径
        return run(f'"{pip_path}" {sub_cmd}')
    return run(f"python -m pip {sub_cmd}")

def pip_list():
    print(pip_run('list'))

def pip_install(pkg):
    print(pip_run(f"install {pkg}"))

def pip_uninstall(pkg):
    print(pip_run(f"uninstall -y {pkg}"))

def pip_upgrade(pkg):
    print(pip_run(f"install -U {pkg}"))

def pip_find(pkg):
    if not pkg:
        print('库名不能为空')
        return
    try:
        info = pip_run(f"show {pkg}")
    except Exception:
        print(f"{pkg} 未安装")
        return
    if not info.strip():
        print(f"{pkg} 未安装")
        return
    version = None
    for line in info.splitlines():
        if line.startswith('Version:'):
            version = line.split(':', 1)[1].strip()
            break
    if version:
        print(f"{pkg} 已安装, 版本 {version}")
    else:
        print(f"{pkg} 已安装, 版本未知")

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

    if len(wh_pip) == 1:
        print("发现1个pip版本")
        print('路径：',wh_pip[0])
        pip_path = wh_pip[0]
    elif len(wh_pip) == 0:
        print("OoO? 未发现pip")
        pip_path = None
    else:
        print(f"OoO? 发现多个pip版本，{len(wh_pip)}个")
        print(f"路径：")
        for i in range(len(wh_pip)):
            print('第',i+1,'个：',wh_pip[i])
        try:
            idx = int(input('请选择默认pip序号 (1~%d): ' % len(wh_pip)).strip()) - 1
            if 0 <= idx < len(wh_pip):
                pip_path = wh_pip[idx]
            else:
                print('序号无效，采用第一个pip')
                pip_path = wh_pip[0]
        except Exception:
            print('输入无效，采用第一个pip')
            pip_path = wh_pip[0]

    while True:
        print('\n=== pip库管理 ===')
        print('1. 列出已安装库')
        print('2. 安装库')
        print('3. 卸载库')
        print('4. 升级库')
        print('5. 查找库')
        print('6. 退出')

        choice = input('请输入选项数字: ').strip()
        if choice == '1':
            pip_list()
        elif choice == '2':
            pkg = input('要安装的库名: ').strip()
            if pkg:
                pip_install(pkg)
        elif choice == '3':
            pkg = input('要卸载的库名: ').strip()
            if pkg:
                pip_uninstall(pkg)
        elif choice == '4':
            pkg = input('要升级的库名（留空升级pip本身）: ').strip()
            if pkg:
                pip_upgrade(pkg)
            else:
                pip_upgrade('pip')
        elif choice == '5':
            pkg = input('要查找的库名: ').strip()
            pip_find(pkg)
        elif choice == '6':
            print('退出pip管理')
            break
        else:
            print('无效选项')
    
