# 소스·라이선스·의존성 등록부 — C44

공개 소스는 C44 성공 후보에서 추출했습니다. 파일별 SHA256, 동일 이름의 upstream 후보 및 원본 해시는 `source-manifest.json`에 있습니다. 이름 매칭 후보는 출처 추적 자료이며 모든 파일에 동일 라이선스를 부여한다는 뜻이 아닙니다.

| 구성 | 출처 및 고정 기준 | 조건·변경 범위 |
| --- | --- | --- |
| GBC core / T80 / video / sound | [Gameboy_MiSTer](https://github.com/MiSTer-devel/Gameboy_MiSTer/tree/7a5ff50528cd9c1d13ffb675e7df8506bffaa078) | gb.v는 GPL-3.0-or-later 표시, T80은 원본 허용 조건·고지 유지. 일부 파일은 개별 라이선스 헤더가 없어 upstream 전체를 임의로 MIT 등으로 표기하지 않음. |
| MCU·SPI·보드 경로 | [sd2snes](https://github.com/mrehkopf/sd2snes/tree/cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1) | MCU의 GPL-2.0-only 헤더·루트 COPYING 등 원래 조건 유지. 전체 clone 대신 30개 변경·추가 파일을 overlay로 제공. mini FPGA는 이 커밋에서 재생성. |
| 공개 CGB boot | 위 MiSTer의 BootROMs, SameBoy 기반 | Lior Halphon의 MIT 고지 보존. MIF 초기값과 주소 packing만 사용. 상용 SGB BIOS와 구분. |
| PLL wrapper | Quartus 생성 소스, Cyclone IV 대상 | 파일 내 Intel/Altera 조건 유지. 임의로 GPL/MIT 재지정하지 않음. |
| 자체 통합 HDL·renderer·검증·문서 | 본 프로젝트 C43 및 소스 생성기 | 저장소 전체에 대한 신규 포괄 재사용 라이선스는 아직 소유자 결정 전. 기존 파생 파일의 upstream 조건은 계속 적용. |

## 변경과 고지

MCU는 새 확장자 분기, 빠른 로딩, SRAM/RTC, 메뉴·강제 저장·복원·진단을 추가했습니다. FPGA는 MiSTer 기반 CPU/PPU/사운드와 FXPAK 메모리·SPI·SNES 출력 경로를 연결하고 매퍼·상태·RTC·배속을 수정했습니다. renderer는 자체 생성한 SNES/SPC 코드입니다. 변경일과 후보는 2026-10-04 / G13C44입니다.

원래 파일의 저작권·라이선스 문구는 삭제하지 않았습니다. `licenses`에 핵심 고지를 함께 제공합니다. 개별 헤더 없는 upstream 파일과 자체 작성 부분의 최종 배포 고지·라이선스 범위는 릴리스 전 점검 항목이며, 공개 접근 가능성만으로 재배포 조건이 모두 확정됐다고 주장하지 않습니다.

도구 설치본, 상용 게임·BIOS·사용자 세이브·메모리 덤프는 제외합니다. 참고한 ludufre 2.16.4 ZIP의 펌웨어·FPGA·메뉴 자산은 이 소스에 합치지 않았습니다.
