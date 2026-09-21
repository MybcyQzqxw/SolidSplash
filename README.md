# SolidSplash

*Personalize your SOLIDWORKS splash screen.*

SolidSplash 是一个桌面小工具，帮助你把任意 PNG 图片快速处理成 SOLIDWORKS 启动画面（`900×604`，透明背景）所需的规格，并以单个 `.exe` 文件分发给最终用户，无需安装 Python 或任何依赖。

## 功能特性

- **拖放上传**：支持拖拽、文件浏览器、手动输入路径三种方式批量添加 PNG 图片，支持单张图片可视化删除。
- **智能缩放限制**：自动检测已上传图片中最大的高度，实时计算并限制"缩小倍数"的可选范围，避免生成结果超出画布。
- **尺寸校验**：图片高度低于 200px 时会被拒绝上传并提示；多张图片尺寸不一致时会给出比例提示（不阻止上传）。
- **精确偏移控制**：横向 / 纵向偏移量均以 5px 为步进，缩小倍数以 0.05 为步进，支持点击箭头或直接输入。
- **实时预览**：只要有图片、缩放值与偏移值，无需点击"转换"即可实时预览效果，透明区域以马赛克网格展示，预览比例与最终导出结果一致。
- **不改动源文件**：所有缩放、合成操作均在内存中完成，原始图片文件不会被修改。
- **批量导出**：一键将全部转换结果导出到指定文件夹，文件名自动追加 `_splash` 后缀。
- **运行日志**：内置终端式日志面板，实时展示校验、转换、导出过程中的所有提示与错误信息。

## 处理规则

1. 按"缩小倍数"对原图等比缩放。
2. 在 `900×604` 透明画布上，将缩放后的图片放置在右下角区域：其右下角与画布右下角的水平/垂直距离，分别等于"横向偏移"和"纵向偏移"的像素值。
3. 转换按钮仅在图片列表非空时可用；导出按钮仅在至少完成过一次转换后可用。两者一旦满足条件即保持可用，方便反复调整参数、多次导出。

## 快速开始（终端用户）

从 [Releases](../../releases) 下载 `SolidSplash.exe`，双击运行即可，无需安装 Python 或其他依赖。

## 从源码构建

### 环境要求

- Windows 10/11
- [Miniconda / Anaconda](https://docs.conda.io/en/latest/miniconda.html)，且 `conda` 已加入 `PATH`

> `build.bat` 会自动创建/复用名为 `solidsplash` 的 conda 环境，并**通过 `pip`**（而非 `conda install`）安装 PySide6。
> 这样可以避免 conda-forge 版 PySide6 依赖外部 Qt 动态库、导致 PyInstaller 打包后缺少 DLL 而无法运行的问题。

### 一键打包

```bat
build.bat
```

`build.bat` 会自动：

1. 创建独立 conda 环境 `solidsplash`（Python 3.11，若已存在则跳过）；
2. 通过 `pip` 安装 `requirements.txt` 中的依赖（PySide6、Pillow、PyInstaller）；
3. 使用 PyInstaller 打包为单文件可执行程序；
4. 将结果复制到 `release\SolidSplash.exe`。

### 手动运行（开发调试）

```bat
conda create -n solidsplash python=3.11 -y
conda activate solidsplash
pip install -r requirements.txt
python src\main.py
```

## 项目结构

```
SolidSplash/
├── build.bat                  # 一键打包脚本
├── requirements.txt            # 运行 / 打包依赖
├── src/
│   ├── main.py                 # 程序入口
│   └── solidsplash/
│       ├── constants.py        # 画布尺寸、步进等常量
│       ├── image_processing.py # 核心图像处理逻辑（校验、缩放、合成）
│       ├── main_window.py      # 主窗口与业务逻辑
│       └── widgets/            # 拖放列表、预览、日志等自定义控件
└── release/                     # build.bat 打包产物（已加入 .gitignore）
```

## 技术栈

- [PySide6](https://doc.qt.io/qtforpython/)：图形界面
- [Pillow](https://python-pillow.org/)：图像处理
- [PyInstaller](https://pyinstaller.org/)：单文件可执行程序打包

## License

MIT
