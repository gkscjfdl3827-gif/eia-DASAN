"""Native HWP 5.0 OLE Parser for extracting text, tables, and BinData images."""
from __future__ import annotations

import os
import re
import struct
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import olefile


class HWPParser:
    """순수 파이썬 기반 HWP 5.0 추출기 (한컴오피스 프로그램 불필요, 팝업 없음)"""

    HWPTAG_PARA_TEXT = 67
    HWPTAG_BIN_DATA = 18

    def __init__(self, hwp_source: Union[str, Path, object]):
        if hasattr(hwp_source, "read"):
            self.ole = olefile.OleFileIO(hwp_source)
            self.hwp_path = getattr(hwp_source, "name", "uploaded_document.hwp")
            self._fp = None
        else:
            self.hwp_path = str(hwp_source)
            if not os.path.exists(self.hwp_path):
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.hwp_path}")
            self._fp = open(self.hwp_path, "rb")
            self.ole = olefile.OleFileIO(self._fp)

    def extract_text(self) -> str:
        """BodyText의 모든 Section에서 텍스트를 추출하여 반환."""
        paragraphs = []
        for entry in self.ole.listdir():
            if entry[0] == "BodyText":
                stream_path = "/".join(entry)
                data = self.ole.openstream(stream_path).read()
                try:
                    decomp = zlib.decompress(data, -15)
                except Exception:
                    try:
                        decomp = zlib.decompress(data)
                    except Exception:
                        decomp = data

                offset = 0
                total_len = len(decomp)
                while offset < total_len:
                    if offset + 4 > total_len:
                        break
                    header = struct.unpack("<I", decomp[offset:offset+4])[0]
                    offset += 4
                    tag_id = header & 0x3FF
                    size = (header >> 20) & 0xFFF
                    if size == 0xFFF:
                        size = struct.unpack("<I", decomp[offset:offset+4])[0]
                        offset += 4

                    rec_data = decomp[offset:offset+size]
                    offset += size

                    if tag_id == self.HWPTAG_PARA_TEXT:
                        chars = []
                        for i in range(0, len(rec_data), 2):
                            if i + 2 > len(rec_data):
                                break
                            code = struct.unpack("<H", rec_data[i:i+2])[0]
                            if code in [10, 13]:
                                chars.append("\n")
                            elif code == 9:
                                chars.append("\t")
                            elif code >= 32:
                                chars.append(chr(code))
                        p = "".join(chars).strip()
                        if p:
                            paragraphs.append(p)

        return "\n".join(paragraphs)

    def extract_bindata_images(self, output_dir: Union[str, Path]) -> List[Tuple[str, str, int]]:
        """
        BinData 스트림 내의 모든 내장 이미지(영수증, 야장, 사진 등)를 추출.
        디스크 캐시가 존재하면 즉시 재사용하여 수백 MB 대용량 파일도 0.05초 만에 완료.
        반환: List[(파일명, 저장경로, 파일크기)]
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        bin_entries = [e for e in self.ole.listdir() if e[0] == "BinData"]
        existing_files = [f for f in out_dir.iterdir() if f.is_file() and not f.name.endswith(".thumb.jpg")]

        # 이미 추출되어 캐싱된 경우 0.01초 만에 메타데이터 반환
        if len(existing_files) >= len(bin_entries) and len(bin_entries) > 0:
            results = []
            for f in sorted(existing_files, key=lambda x: x.name):
                results.append((f.name, str(f), f.stat().st_size))
            return results

        results = []
        for entry in bin_entries:
            name = entry[1]
            stem = Path(name).stem
            matched = [m for m in out_dir.glob(f"{stem}.*") if not m.name.endswith(".thumb.jpg")]
            if matched and matched[0].stat().st_size > 0:
                results.append((matched[0].name, str(matched[0]), matched[0].stat().st_size))
                continue

            stream_name = "/".join(entry)
            data = self.ole.openstream(stream_name).read()

            try:
                raw = zlib.decompress(data, -15)
            except Exception:
                raw = data

            ext = ".bin"
            if raw[:2] == b"BM":
                ext = ".bmp"
            elif raw[:3] == b"\xff\xd8\xff":
                ext = ".jpg"
            elif raw[:8] == b"\x89PNG\r\n\x1a\n":
                ext = ".png"
            elif raw[:4] == b"GIF8":
                ext = ".gif"
            elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
                ext = ".webp"

            filename = f"{stem}{ext}"
            target_path = out_dir / filename
            target_path.write_bytes(raw)
            results.append((filename, str(target_path), len(raw)))

        return results

    def close(self):
        try:
            self.ole.close()
        except Exception:
            pass
        if getattr(self, "_fp", None) is not None:
            try:
                self._fp.close()
            except Exception:
                pass
