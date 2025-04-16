import os
import sys
import subprocess

def main():
    print("开始打包电子相册应用...")
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"当前Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major == 3 and python_version.minor >= 12:
        print("警告: 检测到Python 3.12或更高版本")
        print("PyInstaller可能与Python 3.12不完全兼容，尝试安装最新的开发版本...")
        
        # 卸载当前版本并安装最新的开发版本
        subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", "pyinstaller"])
        subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "setuptools", "wheel"])
        subprocess.call([sys.executable, "-m", "pip", "install", "--no-cache-dir", "pyinstaller>=6.0.0"])
        
        print("安装完成，尝试使用最新版本...")
        
    else:
        # 检查PyInstaller是否已安装
        try:
            import PyInstaller
            print("PyInstaller已安装")
        except ImportError:
            print("正在安装PyInstaller...")
            subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller安装完成")
    
    # 检测操作系统
    is_windows = sys.platform.startswith('win')
    path_separator = ';' if is_windows else ':'
    
    # 尝试使用pyinstaller直接命令
    try:
        print("尝试直接使用PyInstaller命令...")
        
        # 创建打包命令
        pyinstaller_cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--name=电子相册",
            "--windowed",  # 不显示控制台窗口
            "--onefile",   # 打包成单一exe文件
        ]
        
        # 添加图标（如果存在）
        if os.path.exists("photo_icon.ico"):
            pyinstaller_cmd.append("--icon=photo_icon.ico")
        else:
            print("警告: 图标文件 'photo_icon.ico' 未找到，将使用默认图标")
        
        # 添加数据文件
        pyinstaller_cmd.append(f"--add-data=README.md{path_separator}.")
        
        # 添加主程序
        pyinstaller_cmd.append("photo_album.py")
        
        # 运行PyInstaller命令
        print("正在执行打包命令...")
        print(f"执行命令: {' '.join(pyinstaller_cmd)}")
        result = subprocess.call(pyinstaller_cmd)
        
        if result != 0:
            raise Exception("PyInstaller执行失败")
        
        print("\n打包完成！")
        print("可执行文件位于 dist/电子相册.exe")
        print("双击此文件即可运行程序")
        
    except Exception as e:
        print(f"打包过程中发生错误: {e}")
        print("\n尝试使用替代方法...")
        print("请尝试手动运行以下命令:")
        print(f"pip install --upgrade pyinstaller")
        print(f"pyinstaller --onefile --windowed --name=\"电子相册\" photo_album.py")
        print("\n或考虑使用Python 3.11版本进行打包，它与PyInstaller完全兼容")

if __name__ == "__main__":
    main() 