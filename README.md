# FXPAK Pro Game Boy Color — C44

Game Boy / Game Boy Color FPGA core for **FXPAK Pro / Mk.III (STM32 + Cyclone IV)**. C44 passed the user's final hardware checks on 2026-10-04. This branch prepares the source and an update package; a final GitHub Release has not been published.

**[사용 가이드 / Korean user guide](docs/USER-GUIDE.ko.md)** · [Compatibility](docs/COMPATIBILITY.ko.md) · [Build](docs/BUILD-C44.ko.md) · [Release notes](docs/RELEASE-C44.ko.md) · [Source and notices](docs/DEPENDENCY-REGISTER.ko.md)

## 사용 개요

- 게임 파일의 복사본 확장자를 `.egbc`로 변경하면 새 코어로 실행합니다.
- `.gb/.gbc`는 기존 SGB 경로를 유지합니다. 기존 코어·BIOS 설치가 필요합니다.
- L+R+Start 메뉴: 복귀, WRITE SRAM, AUTO WRITE SRAM, 소리, 4슬롯 강제 저장·복원, 게임 리셋.
- R을 누르는 동안 약 3배 빨리감기. 배속은 게임·화면 갱신 시간에 따라 달라집니다.
- MBC1/MBC1M/MBC3+RTC/MBC5를 구현했습니다. SGB 테두리·치트·통신·특수 주변장치는 지원 범위 밖입니다.
- C44는 SD 진단 로그 3종을 만들지 않습니다. 게임 저장·강제 저장·설정 파일은 정상 기록합니다.

## 배포 구성

정상 동작하는 **공식 sd2snes 1.11.2 계열 설치** 위에 적용하는 업데이트입니다. SD에 복사할 파일은 `firmware.stm`, `fpga_egbc.bi3`, `gbc_snes.bin`, `gbc-utc-offset.txt`입니다. 기존 시차 설정이 있으면 자신의 설정을 유지합니다.

SGB 코어·BIOS, 상용 게임 ROM, 세이브, 외부 도구는 포함하지 않습니다. 구형 SD2SNES/Mk.II용 바이너리가 아닙니다. ludufre 2.16.4 배포판은 파일 구성만 참고했으며, 해당 포크의 기능 병합이나 혼합 설치를 검증하지 않았습니다.

## 소스

| 경로 | 내용 |
| --- | --- |
| src/fpga | C43에서 실기 검증한 HDL·제약·공개 부트 초기값. C44에서도 동일 |
| src/firmware-overlay | 고정 sd2snes 커밋에 적용하는 C44 MCU 변경·추가 파일 30개 |
| src/renderer | 자체 SNES 화면·메뉴·SPC 코드 생성기 |
| tools / tests | 소스 복원·재현 빌드·RTC와 로그 정책 검사·패키징 |
| source-manifest.json | 파일별 해시와 고정 upstream 출처 |
| release | 바이너리 해시·재현 및 기능 검증 기록 |

원래 저작권·라이선스를 유지하며, 저장소 전체를 새 단일 라이선스로 덮지 않습니다. 기존 실험·방법론 문서는 당시 이력입니다. 현재 동작과 설치는 C44 문서를 우선합니다.
