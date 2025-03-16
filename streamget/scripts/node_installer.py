import platform
import sys
import tarfile
import zipfile
from pathlib import Path

import httpx
from tqdm import tqdm


def install_node(version="22.14.0", install_path=None):
    """Cross-platform installation of Node.js to specified path"""
    system = platform.system().lower()
    node_dist_urls = {
        'windows': f"https://nodejs.org/dist/v{version}/node-v{version}-win-x64.zip",
        'darwin': f"https://nodejs.org/dist/v{version}/node-v{version}-darwin-x64.tar.gz",
        'linux': f"https://nodejs.org/dist/v{version}/node-v{version}-linux-x64.tar.xz"
    }

    url = node_dist_urls.get(system)
    if not url:
        raise NotImplementedError(f"Unsupported platform: {system}")

    # Setup paths
    default_path = Path.home() / ".streamget_node"
    install_path = Path(install_path) if install_path else default_path
    install_path.mkdir(parents=True, exist_ok=True)
    archive_path = install_path / f"node-v{version}.{'zip' if system == 'windows' else 'tar.gz'}"

    success = False
    try:
        print(f"📥 Downloading Node.js v{version}...")
        with httpx.Client(timeout=30) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                progress_bar = tqdm(
                    total=total_size,
                    ncols=100,
                    unit='iB',
                    unit_scale=True,
                    desc="Downloading",
                    dynamic_ncols=False,
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]"
                )

                with open(archive_path, 'wb') as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        progress_bar.update(len(chunk))
                progress_bar.close()

        print("\n📦 Extracting files...")
        if system == 'windows':
            with zipfile.ZipFile(archive_path) as zf:
                file_list = zf.infolist()
                with tqdm(
                        total=len(file_list),
                        ncols=100,
                        desc="Extracting",
                        unit="files",
                        dynamic_ncols=False
                ) as pbar:
                    for file in file_list:
                        zf.extract(file, install_path)
                        pbar.update(1)
        else:
            with tarfile.open(archive_path) as tf:
                members = tf.getmembers()
                with tqdm(
                        total=len(members),
                        ncols=100,
                        desc="Extracting",
                        unit="files",
                        dynamic_ncols=False
                ) as pbar:
                    for member in members:
                        tf.extract(member, install_path)
                        pbar.update(1)

        success = True

    except Exception as e:
        print(f"\n❌ Installation failed: {str(e)}")
        if archive_path.exists():
            print(f"⚠️  Archive retained for debugging: {archive_path}")
        sys.exit(1)

    finally:
        if success and archive_path.exists():
            try:
                archive_path.unlink()
                print(f"♻️  Cleaned up: {archive_path.name}")
            except Exception as cleanup_error:
                print(f"⚠️  Failed to clean up archive: {str(cleanup_error)}")

    bin_path = install_path / f"node-v{version}-{system}-x64" / ("bin" if system != 'windows' else "")
    print(f"\n🎉 Installation complete! Please add to PATH:\n👉 {bin_path}\n")
