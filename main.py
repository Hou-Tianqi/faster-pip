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
current_venv = None  # 当前虚拟环境路径


#函数定义区
def is_windows():
    return platform.system().lower() == 'windows'


def run(command, timeout=300):
    try:
        # 统一使用列表形式，避免 shell=True 的安全风险
        if isinstance(command, str):
            command = shlex.split(command)
        # 不指定 encoding，让 subprocess 自动处理字节流
        res = sub.run(command, check=True, capture_output=True, timeout=timeout, shell=False)
        
        # 尝试多种编码解码输出
        output = None
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                output = res.stdout.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用 replace 模式忽略错误字符
        if output is None:
            output = res.stdout.decode('latin-1', errors='replace')
        
        return output
    except sub.TimeoutExpired:
        print(f"命令超时（{timeout}s）：{command}")
        raise
    except sub.CalledProcessError:
        # 命令执行失败（比如找不到命令），返回空字符串
        return ""


def find_all_executables(name):
    if is_windows():
        result = run(["where", name])
        if not result:  # 处理 None 或空字符串
            return []
        return [line.strip() for line in result.strip().splitlines() if line.strip()]
    result = run(["which", "-a", name])
    if not result:
        return []
    return [line.strip() for line in result.strip().splitlines() if line.strip()]


def find_global_pip():
    """查找全局pip路径"""
    pip_candidates = ['pip', 'pip3'] if not is_windows() else ['pip']
    for cmd in pip_candidates:
        # 优先使用 find_all_executables
        paths = find_all_executables(cmd)
        if paths and paths[0].strip():
            return paths[0].strip()
        # 降级使用 shutil.which
        path = shutil.which(cmd)
        if path:
            return path
    return None


def detect_current_env():
    """自动检测当前是否在虚拟环境中"""
    # Python 3.3+ 标准方法（兼容 Python 3.11+）
    if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        return sys.prefix
    
    # 检查环境变量 VIRTUAL_ENV
    venv_path = os.environ.get('VIRTUAL_ENV')
    if venv_path:
        return venv_path
    
    return None


def use_venv(venv_path=None):
    """切换到虚拟环境，venv_path=None 表示切换回全局"""
    global pip_path, current_venv
    
    if venv_path:
        # 规范化路径
        venv_path = os.path.abspath(venv_path)
        
        # 检查是否是有效的虚拟环境
        if is_windows():
            pip_exe = os.path.join(venv_path, "Scripts", "pip.exe")
            python_exe = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            pip_exe = os.path.join(venv_path, "bin", "pip")
            python_exe = os.path.join(venv_path, "bin", "python")
        
        if not os.path.exists(pip_exe):
            print(f"⚠️ {venv_path} 不是有效的虚拟环境（找不到pip）")
            return False
        
        pip_path = pip_exe
        current_venv = venv_path
        print(f"✅ 已切换到虚拟环境: {venv_path}")
        return True
    else:
        # 切换回全局
        global_pip = find_global_pip()
        if global_pip:
            pip_path = global_pip
        else:
            pip_path = None
        current_venv = None
        print("✅ 已切换回全局环境")
        return True


def pip_run(sub_cmd):
    if isinstance(sub_cmd, list):
        args = sub_cmd
    else:
        args = shlex.split(sub_cmd)
    
    # 修复：检查 pip_path 是否有效
    if pip_path and os.path.exists(pip_path):
        cmd = [pip_path] + args
    else:
        # 降级使用 python -m pip
        cmd = [sys.executable, "-m", "pip"] + args
    # pip 安装可能较慢，默认给大些时间
    return run(cmd, timeout=600)


def pip_list():
    print(pip_run('list'))


def pip_install(pkg):
    if not pkg or not pkg.strip():
        print("⚠️ 未指定要安装的包")
        return
    print(pip_run(f"install {pkg}"))


def pip_uninstall(pkg):
    if not pkg or not pkg.strip():
        print("⚠️ 未指定要卸载的包")
        return
    print(pip_run(["uninstall", "-y"] + pkg.split()))


def pip_upgrade(pkg):
    if not pkg or not pkg.strip():
        print("⚠️ 未指定要升级的包")
        return
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
            if not deps:
                return []
            clean_deps = []
            for dep in deps.split(','):
                dep = dep.strip()
                # 去除版本号：>=, <=, >, <, ==, ~=, !=
                for sep in ['>=', '<=', '>', '<', '==', '~=', '!=']:
                    if sep in dep:
                        dep = dep.split(sep)[0]
                        break
                # 去除 [extra] 标记
                if '[' in dep:
                    dep = dep.split('[')[0]
                clean_deps.append(dep.strip())
            return clean_deps
    return []


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


def set_pip_source(source_url="https://pypi.tuna.tsinghua.edu.cn/simple"):
    """配置 pip 下载源"""
    try:
        sub.check_call(
            [sys.executable, "-m", "pip", "config", "set", "global.index-url", source_url]
        )
        print(f"✅ pip 下载源已设置为: {source_url}")
    except sub.CalledProcessError:
        print("❌ 设置 pip 下载源失败")


def setup_venv(venv_name="my_env", use_mirror=True):
    """检查环境、创建虚拟环境并安装依赖"""
    venv_dir = os.path.join(os.getcwd(), venv_name)
    
    # 获取虚拟环境中的路径
    if platform.system() == "Windows":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
        venv_pip = os.path.join(venv_dir, "bin", "pip")

    # 创建虚拟环境（如果不存在）
    if not os.path.exists(venv_python):
        print(f"正在创建虚拟环境: {venv_name}")
        sub.check_call([sys.executable, "-m", "venv", venv_name])
        print("✅ 虚拟环境创建完成")
    else:
        print(f"虚拟环境已存在: {venv_name}")

    # 安装依赖
    req_file = os.path.join(os.getcwd(), "requirements.txt")
    if os.path.exists(req_file):
        print("正在安装依赖...")
        install_cmd = [venv_pip, "install", "-r", req_file]
        if use_mirror:
            mirror_url = "https://pypi.tuna.tsinghua.edu.cn/simple"
            install_cmd.extend(["-i", mirror_url])
            print(f"使用镜像源: {mirror_url}")
        sub.check_call(install_cmd)
        print("✅ 依赖安装完成")
    else:
        print("未找到 requirements.txt，跳过依赖安装")
    
    # 提示如何激活虚拟环境
    print(f"\n✅ 虚拟环境准备完成: {venv_name}")
    if platform.system() == "Windows":
        print(f"激活命令: {venv_dir}\\Scripts\\activate")
        print(f"退出命令: deactivate")
    else:
        print(f"激活命令: source {venv_dir}/bin/activate")
        print(f"退出命令: deactivate")
    
    # 询问是否切换到该虚拟环境
    switch = input(f"\n是否立即切换到虚拟环境 '{venv_name}'? (y/n): ").strip().lower()
    if switch == 'y':
        use_venv(venv_dir)
    
    return venv_python


def list_venvs():
    """列出当前目录下的所有虚拟环境"""
    venvs = []
    for item in os.listdir('.'):
        item_path = os.path.join('.', item)
        if os.path.isdir(item_path):
            if is_windows():
                if os.path.exists(os.path.join(item_path, "Scripts", "python.exe")):
                    venvs.append(item)
            else:
                if os.path.exists(os.path.join(item_path, "bin", "python")):
                    venvs.append(item)
    return venvs


def switch_env_menu():
    """切换环境菜单"""
    print("\n=== 切换环境 ===")
    print("1. 使用全局环境")
    print("2. 切换到虚拟环境（输入路径）")
    print("3. 切换到已有虚拟环境（从列表选择）")
    print("4. 查看当前环境")
    print("5. 返回上级菜单")
    
    choice = input("请选择: ").strip()
    
    if choice == '1':
        use_venv(None)
    
    elif choice == '2':
        venv_path = input("请输入虚拟环境路径: ").strip()
        if venv_path:
            use_venv(venv_path)
    
    elif choice == '3':
        venvs = list_venvs()
        if not venvs:
            print("当前目录下没有找到虚拟环境")
            return
        print("\n找到以下虚拟环境:")
        for i, venv in enumerate(venvs, 1):
            print(f"  {i}. {venv}")
        try:
            idx = int(input("请选择序号: ").strip()) - 1
            if 0 <= idx < len(venvs):
                venv_path = os.path.abspath(venvs[idx])
                use_venv(venv_path)
            else:
                print("无效序号")
        except ValueError:
            print("输入无效")
    
    elif choice == '4':
        if current_venv:
            print(f"当前环境: 虚拟环境 [{current_venv}]")
            print(f"pip路径: {pip_path}")
        else:
            print("当前环境: 全局环境")
            if pip_path:
                print(f"pip路径: {pip_path}")
    
    elif choice == '5':
        return
    
    else:
        print("无效选项")


def export_requirements(output_file="requirements.txt"):
    """导出当前环境的包列表到 requirements.txt"""
    try:
        output = pip_run('freeze')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"✅ 已导出包列表到: {output_file}")
    except Exception as e:
        print(f"❌ 导出失败: {e}")


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

    # 自动检测虚拟环境
    detected_venv = detect_current_env()
    if detected_venv:
        print(f"\n🔍 检测到已激活的虚拟环境: {detected_venv}")
        use_venv(detected_venv)
    else:
        print("\n当前使用全局环境")

    while True:
        # 显示当前环境状态
        if current_venv:
            env_status = f" [虚拟环境: {os.path.basename(current_venv)}]"
        else:
            env_status = " [全局环境]"
        
        print(f'\n=== pip库管理{env_status} ===')
        print('0. 切换环境')
        print('1. 列出已安装库')
        print('2. 安装库')
        print('3. 卸载库')
        print('4. 升级库')
        print('5. 查找库')
        print('6. 切换 pip 下载源')
        print('7. 创建/更新虚拟环境')
        print('8. 导出 requirements.txt')
        print('9. 退出')

        choice = input('请输入选项数字: ').strip()
        
        if choice == '0':
            switch_env_menu()
        
        elif choice == '1':
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
            source_url = input('请输入 pip 源地址 (回车使用默认清华镜像): ').strip()
            if source_url:
                set_pip_source(source_url)
            else:
                set_pip_source()
        
        elif choice == '7':
            venv_name = input('请输入虚拟环境名称 (默认 my_env): ').strip() or 'my_env'
            use_mirror = input('是否使用镜像源安装依赖? (y/n, 默认 y): ').strip().lower()
            setup_venv(venv_name, use_mirror != 'n')
        
        elif choice == '8':
            export_requirements()
        
        elif choice == '9':
            print('退出pip管理')
            break
        
        else:
            print('无效选项')