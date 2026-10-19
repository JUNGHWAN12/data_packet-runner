# PyInstaller 설정: 부스 노트북(Python 미설치)에서 켜지는 실행 파일 폴더를 만든다.
#   pyinstaller packaging/PacketRunner.spec   →   dist/PacketRunner/PacketRunner.exe
# 한 폴더(onedir) 방식: 한 파일(onefile)보다 켜지는 시간이 짧다. 순위·로그는 실행 파일 옆 data/, logs/에 생긴다.
from pathlib import Path

root = Path(SPECPATH).parent
assets = root / "assets"

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    datas=[
        (str(assets / "generated"), "assets/generated"),
        (str(assets / "fonts"), "assets/fonts"),
        (str(assets / "licenses"), "assets/licenses"),
        (str(assets / "CREDITS.md"), "assets"),
    ],
    excludes=["tkinter", "pytest"],
    # 파이썬 코드를 .exe 안의 묶음(PYZ)이 아니라 _internal 폴더의 일반 파일로 둔다.
    # 실행 중에 .exe를 다시 열어 읽지 않으므로, 백신이 새 실행 파일 읽기를 막아
    # "[Errno 13] Permission denied: ...PacketRunner.exe"로 켜지지 않던 문제를 피한다.
    noarchive=True,
)
# Arcade 3.3.3의 PyInstaller 설정은 VERSION 파일을 'arcade/VERSION/VERSION'(폴더 안)에 넣어 버전을 못 읽는다.
# 'arcade/VERSION' 파일로 바로잡는다.
import arcade as _arcade
_version = Path(_arcade.__file__).parent / "VERSION"
a.datas = [d for d in a.datas if not d[0].replace("\\", "/").startswith("arcade/VERSION")]
a.datas.append(("arcade/VERSION", str(_version), "DATA"))

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PacketRunner",
    console=False,          # 검은 콘솔 창 없이 (꺼질 때 남는 창이 없도록)
    upx=False,
    append_pkg=False,       # 실행 묶음을 .exe 안이 아니라 옆의 PacketRunner.pkg로 (위 noarchive와 같은 이유)
)
coll = COLLECT(exe, a.binaries, a.datas, name="PacketRunner", upx=False)
