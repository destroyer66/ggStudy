### 安卓 APK 打包指南

当前您的开发环境是 Windows，而 Kivy 的 `buildozer` 工具主要支持在 **Linux (Ubuntu)** 环境下运行来打包 APK。

您可以通过以下几种方式进行打包：

#### 方法 1：使用 GitHub Actions (推荐)
这是最简单的方法，不需要在本地安装任何 Linux 环境。
1. 将本项目上传到您的 **GitHub 仓库**。
2. 项目中已预设了 `.github/workflows/android.yml` 文件。
3. 每次提交代码（Push）到 `main` 分支时，GitHub 将自动启动构建。
4. 在 GitHub 项目页面的 **Actions** 标签页下，您可以实时查看构建状态。
5. 构建完成后，在 **Artifacts** 区域即可下载打包好的 `package.zip`，解压后即为 APK 文件。

#### 方法 2：使用 WSL2 (Windows Subsystem for Linux)
1. 在 Windows 上安装 Ubuntu (从 Microsoft Store)。
2. 在 Ubuntu 中运行以下命令安装依赖：
   ```bash
   sudo apt update
   sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
   pip3 install --user --upgrade buildozer
   ```
3. 进入项目目录并运行：
   ```bash
   buildozer android debug
   ```

#### 方法 3：使用虚拟机
安装 VirtualBox 并下载 Kivy 官方提供的 [Kivy Virtual Machine](https://kivy.org/#download)，里面预装了所有打包工具。

---

### 打包注意事项
- **buildozer.spec**：已经为您配置好了 `requirements = python3,kivy`，并包含了 `assets/*.png` 图标。
- **Android API**：设置为 31 (Android 12)，符合 Google Play 的最新要求。
- **权限**：已申请 `INTERNET` 和 `STORAGE` 权限。
- **字体说明**：代码中已经包含了 Android 系统中文字体的自动检测逻辑，防止弹窗乱码。

如果您有可用的 Ubuntu 环境，只需在项目根目录执行 `buildozer android debug` 即可。
