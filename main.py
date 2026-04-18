import subprocess as sub
from functools import wraps
import time
import os
import sys
import platform
import shutil
import shlex


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

#函数定义区
def is_windows():
    return platform.system().lower() == 'windows'


def run(command, timeout=300):
    try:
        if isinstance(command, str):
            res = sub.run(command, check=True, capture_output=True, timeout=timeout, encoding="utf-8", shell=True)
        else:
            res = sub.run(command, check=True, capture_output=True, timeout=timeout, encoding="utf-8", shell=False)
        return res.stdout
    except sub.TimeoutExpired:
        print(f"命令超时（{timeout}s）：{command}")
        raise


def find_all_executables(name):
    if is_windows():
        return run(["where", name]).strip().splitlines()
    return run(["which", "-a", name]).strip().splitlines()


def pip_run(sub_cmd):
    args = shlex.split(sub_cmd)
    if pip_path:
        cmd = [pip_path] + args
    else:
        cmd = [sys.executable, "-m", "pip"] + args
    # pip 安装可能较慢，默认给大些时间
    return run(cmd, timeout=600)

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


def pip_installed_packages():
    output = pip_run('list --format=freeze')
    packages = []
    for line in output.splitlines():
        if '==' in line:
            packages.append(line.split('==', 1)[0].strip())
    return packages


def pip_requires(pkg):
    try:
        info = pip_run(f'show {pkg}')
    except Exception:
        return []
    for line in info.splitlines():
        if line.startswith('Requires:'):
            deps = line.split(':', 1)[1].strip()
            return [dep.split(' ')[0].strip() for dep in deps.split(',') if dep.strip()]
    return []


def pip_uninstall_with_deps(pkg, auto_remove=False):
    deps = pip_requires(pkg)
    pip_uninstall(pkg)
    if not deps:
        return

    packages = pip_installed_packages()
    if not packages:
        return

    requires = {name: pip_requires(name) for name in packages}
    dependents = {name: set() for name in packages}
    for name, subdeps in requires.items():
        for dep in subdeps:
            if dep in dependents:
                dependents[dep].add(name)

    keep = {'pip', 'setuptools', 'wheel'}
    remove_set = {pkg}
    queue = [dep for dep in deps if dep in dependents and dep.lower() not in keep]
    orphan_deps = []

    while queue:
        dep = queue.pop()
        if dep in remove_set or dep.lower() in keep:
            continue
        other_dependents = dependents.get(dep, set()) - remove_set
        if not other_dependents:
            remove_set.add(dep)
            orphan_deps.append(dep)
            for subdep in requires.get(dep, []):
                if subdep in dependents and subdep.lower() not in keep:
                    queue.append(subdep)

    if not orphan_deps:
        return

    print('检测到以下依赖库在卸载目标后未被其他包依赖：')
    for dep in orphan_deps:
        print(' -', dep)
    if auto_remove:
        print('正在卸载依赖库...')
        pip_uninstall(' '.join(orphan_deps))
        print('依赖库卸载完成')
        return

    confirm = input('是否同时卸载这些依赖库? (y/n): ').strip().lower()
    if confirm != 'y':
        print('保留依赖库')
        return

    print('正在卸载依赖库...')
    pip_uninstall(' '.join(orphan_deps))
    print('依赖库卸载完成')


def pip_cleanup_unused_deps():
    packages = pip_installed_packages()
    if not packages:
        print('未检测到已安装包')
        return

    requires = {pkg: pip_requires(pkg) for pkg in packages}
    dependents = {pkg: set() for pkg in packages}
    for pkg, deps in requires.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].add(pkg)

    keep = {'pip', 'setuptools', 'wheel'}
    unused = [pkg for pkg, childs in dependents.items() if not childs and pkg.lower() not in keep]
    if not unused:
        print('未检测到当前无用依赖')
        return

    print('检测到当前可删除的无用依赖：')
    for pkg in unused:
        print(' -', pkg)
    confirm = input('是否卸载这些包? (y/n): ').strip().lower()
    if confirm != 'y':
        print('取消卸载')
        return

    print('正在卸载...')
    pip_uninstall(' '.join(unused))
    print('无用依赖已卸载')

def get_installed_packages():
    """获取所有已安装的包列表"""
    try:
        output = pip_run('list --format=freeze')
        packages = []
        for line in output.strip().split("\n"):
            if line and "==" in line:
                name, version = line.split("==", 1)
                packages.append({"name": name, "version": version})
        return packages
    except Exception as e:
        print(f"❌ 获取包列表失败: {e}")
        return []

def uninstall_packages(package_names, auto_confirm=False):
    """卸载指定的包"""
    if not package_names:
        print("没有需要卸载的包")
        return {"success": [], "failed": []}
    
    success = []
    failed = []
    
    for name in package_names:
        print(f"\n正在卸载: {name}")
        
        try:
            pip_uninstall(name)
            success.append(name)
        except Exception as e:
            print(f"❌ 卸载失败: {name} - {e}")
            failed.append(name)
    
    return {"success": success, "failed": failed}

def interactive_uninstall(packages):
    """交互式卸载（支持多选）"""
    print("\n请输入要卸载的包名（多个用空格分隔）")
    choice = input("> ").strip()
    
    if not choice:
        return []
    
    to_uninstall = []
    
    names = choice.split()
    for name in names:
        # 检查包名是否存在
        if any(p["name"] == name for p in packages):
            to_uninstall.append(name)
        else:
            print(f"⚠️ 未找到包: {name}")
    
    if to_uninstall:
        print(f"\n即将卸载以下 {len(to_uninstall)} 个包:")
        for name in to_uninstall:
            print(f"  - {name}")
        
        confirm = input("\n确认卸载？(y/N): ").strip().lower()
        if confirm == 'y':
            return to_uninstall
        else:
            print("取消操作")
            return []
    else:
        print("没有选择有效的包")
        return []

def search_and_uninstall(packages, pattern):
    """按名称模式搜索并卸载"""
    matched = [p["name"] for p in packages if pattern.lower() in p["name"].lower()]
    
    if not matched:
        print(f"没有找到包含 '{pattern}' 的包")
        return []
    
    print(f"找到 {len(matched)} 个匹配的包:")
    for name in matched:
        print(f"  - {name}")
    
    confirm = input(f"\n确认卸载以上 {len(matched)} 个包？(y/N): ").strip().lower()
    if confirm == 'y':
        return matched
    return []

def uninstall_from_file(filepath):
    """从文件读取要卸载的包列表"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if packages:
            print(f"从文件读取到 {len(packages)} 个包:")
            for pkg in packages:
                print(f"  - {pkg}")
            
            confirm = input("\n确认卸载？(y/N): ").strip().lower()
            if confirm == 'y':
                return packages
        return []
    except FileNotFoundError:
        print(f"❌ 文件不存在: {filepath}")
        return []
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return []

def batch_uninstall_menu():
    """批量卸载菜单"""
    packages = get_installed_packages()
    
    if not packages:
        print("没有找到已安装的包")
        return
    
    while True:
        print("\n" + "-" * 40)
        print("批量卸载选项:")
        print("  1. 交互式选择卸载（支持多选）")
        print("  2. 按名称搜索并卸载")
        print("  3. 从文件读取列表卸载")
        print("  4. 返回上级菜单")
        print("-" * 40)
        
        choice = input("请输入选项 (1-4): ").strip()
        
        if choice == '1':
            to_uninstall = interactive_uninstall(packages)
            if to_uninstall:
                result = uninstall_packages(to_uninstall, auto_confirm=True)
                print(f"\n📊 卸载完成: 成功 {len(result['success'])} 个, 失败 {len(result['failed'])} 个")
                # 刷新包列表
                packages = get_installed_packages()
        
        elif choice == '2':
            pattern = input("请输入搜索关键词: ").strip()
            if pattern:
                to_uninstall = search_and_uninstall(packages, pattern)
                if to_uninstall:
                    result = uninstall_packages(to_uninstall, auto_confirm=True)
                    print(f"\n📊 卸载完成: 成功 {len(result['success'])} 个, 失败 {len(result['failed'])} 个")
                    packages = get_installed_packages()
        
        elif choice == '3':
            filepath = input("请输入包列表文件路径: ").strip()
            if filepath:
                to_uninstall = uninstall_from_file(filepath)
                if to_uninstall:
                    result = uninstall_packages(to_uninstall, auto_confirm=True)
                    print(f"\n📊 卸载完成: 成功 {len(result['success'])} 个, 失败 {len(result['failed'])} 个")
                    packages = get_installed_packages()
        
        elif choice == '4':
            break
        
        else:
            print("无效选项，请重新输入")

#主程序入口
if __name__ == "__main__":

    # 检测系统环境变量 PATH
    path_str = os.environ.get('PATH', '')
    path_dirs = [p.strip() for p in path_str.split(os.pathsep) if p.strip()]
    python_candidates = ['python']
    pip_candidates = ['pip']
    if not is_windows():
        python_candidates.insert(0, 'python3')
        pip_candidates.append('pip3')

    has_python_in_path = any(shutil.which(cmd) for cmd in python_candidates)
    has_pip_in_path = any(shutil.which(cmd) for cmd in pip_candidates)

    if not has_python_in_path:
        print("PATH 中未找到 Python")
        try:
            py_paths = find_all_executables('python')
            if not py_paths and not is_windows():
                py_paths = find_all_executables('python3')
            if py_paths and py_paths[0].strip():
                py_path = py_paths[0].strip()
                print(f"找到 Python 路径: {py_path}")
                add_py = input("是否添加此路径到 PATH? (y/n): ").strip().lower()
                if add_py == 'y':
                    py_dir = os.path.dirname(py_path)
                    if is_windows():
                        try:
                            sub.run(f'setx PATH "%PATH%;{py_dir}"', shell=True, check=True)
                            print("已添加 Python 到 PATH，请重启终端以生效")
                        except sub.CalledProcessError:
                            print("添加失败，请手动添加或以管理员身份运行")
                    else:
                        print(f"请手动将以下路径添加到 PATH: {py_dir}")
        except Exception:
            print("未找到 Python 可执行文件")

    if not has_pip_in_path:
        print("PATH 中未找到 pip")
        try:
            pip_paths = find_all_executables('pip')
            if not pip_paths and not is_windows():
                pip_paths = find_all_executables('pip3')
            if pip_paths and pip_paths[0].strip():
                pip_path_found = pip_paths[0].strip()
                print(f"找到 pip 路径: {pip_path_found}")
                add_pip = input("是否添加此路径到 PATH? (y/n): ").strip().lower()
                if add_pip == 'y':
                    pip_dir = os.path.dirname(pip_path_found)
                    if is_windows():
                        try:
                            sub.run(f'setx PATH "%PATH%;{pip_dir}"', shell=True, check=True)
                            print("已添加 pip 到 PATH，请重启终端以生效")
                        except sub.CalledProcessError:
                            print("添加失败，请手动添加或以管理员身份运行")
                    else:
                        print(f"请手动将以下路径添加到 PATH: {pip_dir}")
        except Exception:
            print("未找到 pip 可执行文件")

    wh_py = find_all_executables('python')
    if not wh_py and not is_windows():
        wh_py = find_all_executables('python3')
    wh_pip = find_all_executables('pip')
    if not wh_pip and not is_windows():
        wh_pip = find_all_executables('pip3')
    path = path_dirs

    if len(wh_py) == 1:
        print("发现1个Python版本")
        print(f"版本号：{run(str(wh_py[0])+' --version').strip()}")
        print('路径：',wh_py[0])
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

    print()

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
            print('\n=== 卸载选项 ===')
            print('1. 卸载库')
            print('2. 清除当前无用依赖')
            print('3. 批量卸载')
            sub_choice = input('请选择操作: ').strip()
            if sub_choice == '1':
                pkg = input('要卸载的库名: ').strip()
                if pkg:
                    pip_uninstall(pkg)
            elif sub_choice == '2':
                pip_cleanup_unused_deps()
            elif sub_choice == '3':
                batch_uninstall_menu()
            else:
                print('无效选项')
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
    
