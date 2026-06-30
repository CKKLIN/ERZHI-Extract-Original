"""
WeChat 视频号 XOR 解密模块

支持的加密类型:
  - xWT98/111/126: MD5-based XOR
  - 无加密: 直接透传

用法:
  python decryptor.py <encrypted_file> <encfilekey> [xwt_version]
"""

import hashlib
import sys
import struct
from pathlib import Path


def detect_xwt_version(url: str) -> str:
    """从 URL 中检测 X-snsvideoflag (xWT 版本)"""
    import re
    m = re.search(r'X-snsvideoflag=xWT(\d+)', url)
    if m:
        return f"xWT{m.group(1)}"
    return "xWT98"  # default


def make_xor_key(encfilekey: str, version: str = "xWT98") -> bytes:
    """根据 encfilekey 和版本生成 XOR 密钥"""
    if version == "xWT98":
        seed = b"WXVideo" + encfilekey.encode()
    elif version == "xWT111":
        seed = encfilekey.encode()
    elif version == "xWT126":
        # xWT126 uses a different seed derivation
        seed = encfilekey.encode() + b"_finder_video"
    else:
        seed = encfilekey.encode()
    return hashlib.md5(seed).digest()  # 16-byte key


def get_skip_bytes(version: str) -> int:
    """不同版本跳过的头部字节数"""
    if version == "xWT98":
        return 0
    elif version == "xWT111":
        return 32
    elif version == "xWT126":
        return 0
    return 0


def decrypt_bytes(data: bytes, encfilekey: str, version: str = "xWT98") -> bytes:
    """解密视频数据"""
    key = make_xor_key(encfilekey, version)
    skip = get_skip_bytes(version)
    key_len = len(key)

    result = bytearray(len(data))
    # 前 skip 字节原样保留
    result[:skip] = data[:skip]
    # 剩余部分 XOR 解密
    for i in range(skip, len(data)):
        result[i] = data[i] ^ key[(i - skip) % key_len]
    return bytes(result)


def is_mp4(data: bytes) -> bool:
    """检查是否是有效 MP4 文件（以 ftyp 开头）"""
    if len(data) < 12:
        return False
    # MP4 文件第 4-11 字节通常是 'ftyp'
    return data[4:8] == b'ftyp'


def decrypt_file(input_path: str, encfilekey: str, version: str = None,
                 output_path: str = None) -> str:
    """解密视频文件，返回输出路径"""
    with open(input_path, 'rb') as f:
        data = f.read()

    # 检查是否需要解密
    if is_mp4(data):
        print(f"[decrypt] File is already a valid MP4, skipping decryption")
        if output_path and output_path != input_path:
            Path(output_path).write_bytes(data)
        return output_path or input_path

    # 尝试解密
    if version is None:
        versions_to_try = ["xWT126", "xWT111", "xWT98"]
    else:
        versions_to_try = [version]

    for ver in versions_to_try:
        decrypted = decrypt_bytes(data, encfilekey, ver)
        if is_mp4(decrypted):
            print(f"[decrypt] Success with version={ver}")
            out = output_path or input_path
            Path(out).write_bytes(decrypted)
            return out
        print(f"[decrypt] Version {ver}: result not valid MP4")

    # 如果所有版本都失败，可能 key 不对或文件未被加密
    print(f"[decrypt] All versions failed. File might use different encryption.")
    # 返回原文件（可能是未加密的，让播放器尝试）
    if output_path and output_path != input_path:
        Path(output_path).write_bytes(data)
        return output_path
    return input_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python decryptor.py <input_file> <encfilekey> [xWT_version]")
        print("Example: python decryptor.py video.mp4 Cvvj5Ix3eew... xWT126")
        sys.exit(1)

    input_file = sys.argv[1]
    encfilekey = sys.argv[2]
    version = sys.argv[3] if len(sys.argv) > 3 else None
    output = sys.argv[4] if len(sys.argv) > 4 else input_file + ".dec.mp4"

    result = decrypt_file(input_file, encfilekey, version, output)
    print(f"[decrypt] Output: {result}")
