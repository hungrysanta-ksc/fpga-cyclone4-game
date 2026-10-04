# sd2snesHST 0.9.0 대응 소스 묶음

제품 source ZIP은 검증된 C44 소스 152개를 그대로 포함하며, 라이선스 고지·빌드 도구·문서는 최종 준비 커밋을 사용합니다. manifest의 implementation_commit은 C44 실행 기준, source_commit은 이번 소스 묶음의 커밋입니다.

## 포함 범위

- src/fpga, src/firmware-overlay, src/renderer: 검증된 C44와 동일.
- upstream/sd2snes: 고정 upstream의 LICENSE, README, src, utils, verilog/sd2snes_mini 원본. 실행 바이너리·상용 게임·BIOS는 포함하지 않습니다.
- upstream/Gameboy_MiSTer/BootROMs: CGB 부트 원본 asm, include, logo 입력 및 CGB 빌드에 필요한 도구/Makefile.
- upstream-manifest.json: 포함 원본의 고정 커밋과 파일별 SHA256.
- 라이선스, source-manifest.json, 빌드 스크립트 및 재현 지침.

MCU의 기존 SGB 분기 C 소스는 기존 펌웨어와의 공존에 필요한 빌드 입력이라 포함합니다. 설치 ZIP에 SGB 코어·BIOS를 추가하는 것은 아닙니다.

## 네트워크 없이 MCU 소스 준비

소스 ZIP을 풀고 그 루트에서 실행합니다.

```text
python tools/prepare_firmware.py --offline --out build/firmware
python tools/verify_sources.py
```

동봉 upstream 해시를 검증하고 C44 overlay 30개 및 고정 VERSION을 적용합니다. 준비 폴더는 새 경로여야 합니다. 원래 온라인/기존 clone 방식도 유지합니다. compiler·Quartus·make 등 외부 개발 도구는 별도 설치하며 [기존 빌드 안내](BUILD-C44.ko.md)의 동일 버전을 사용합니다.

CGB 부트 원본을 수정하려면 upstream/Gameboy_MiSTer/BootROMs에서 `make bin/cgb_boot.bin`을 사용합니다. 일반 C44 재현 빌드는 검증된 MIF를 사용하므로 부트를 다시 컴파일할 필요가 없습니다. CGB 출력에서 0x000~0x0FF, 0x800~0x8FF, 0x200~0x7FF를 이 순서대로 취해 packed MIF의 0x000~0x7FF에 배치합니다. 원본 SGB/DMG 부트용 target은 이 CGB 소스 묶음의 빌드 대상이 아닙니다.

사용자 설치에는 source ZIP이 필요하지 않습니다. update ZIP의 sd2snes 폴더를 SD 루트의 같은 폴더에 합쳐 복사합니다.
