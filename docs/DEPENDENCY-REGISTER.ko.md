# 소스·라이선스·의존성 등록부 — C44

공개 소스는 C44 성공 후보에서 추출했습니다. 파일별 SHA256, 동일 이름의 upstream 후보 및 원본 해시는 `source-manifest.json`에 있습니다. 이름 매칭 후보는 출처 추적 자료이며 모든 파일에 동일 라이선스를 부여한다는 뜻이 아닙니다.

| 구성 | 출처 및 고정 기준 | 조건·변경 범위 |
| --- | --- | --- |
| GBC core / T80 / video / sound | [Gameboy_MiSTer](https://github.com/MiSTer-devel/Gameboy_MiSTer/tree/7a5ff50528cd9c1d13ffb675e7df8506bffaa078) | gb.v는 GPL-3.0-or-later 표시, T80은 원본 허용 조건·고지 유지. 일부 파일은 개별 라이선스 헤더가 없어 upstream 전체를 임의로 MIT 등으로 표기하지 않음. |
| MCU·SPI·보드 경로 | [sd2snes](https://github.com/mrehkopf/sd2snes/tree/cf7e21d7a5978fcd74981d71c3cfbf6e982a4dd1) | MCU의 GPL-2.0-only 헤더·루트 COPYING 등 원래 조건 유지. 전체 clone 대신 30개 변경·추가 파일을 overlay로 제공. mini FPGA는 이 커밋에서 재생성. |
| 공개 CGB boot | 위 MiSTer의 BootROMs, SameBoy 기반 | Lior Halphon의 MIT 고지 보존. MIF 초기값과 주소 packing만 사용. 상용 SGB BIOS와 구분. |
| PLL wrapper | Quartus 생성 소스, Cyclone IV 대상 | 파일 내 Intel/Altera 조건 유지. 임의로 GPL/MIT 재지정하지 않음. |
| 자체 통합 HDL·renderer·검증·문서 | 본 프로젝트 C43 및 소스 생성기 | 2026-10-04 소유자 승인: 자체 FPGA GPL-3.0-or-later, MCU GPL-2.0-only, 독립 도구·renderer 생성기·문서 MIT. 기존 파생 파일의 upstream 조건 유지. LICENSE.md 참조. |

## 변경과 고지

MCU는 새 확장자 분기, 빠른 로딩, SRAM/RTC, 메뉴·강제 저장·복원·진단을 추가했습니다. FPGA는 MiSTer 기반 CPU/PPU/사운드와 FXPAK 메모리·SPI·SNES 출력 경로를 연결하고 매퍼·상태·RTC·배속을 수정했습니다. renderer는 자체 생성한 SNES/SPC 코드입니다. 변경일과 후보는 2026-10-04 / G13C44입니다.

원래 파일의 저작권·라이선스 문구는 삭제하지 않았습니다. `licenses`에 핵심 고지를 함께 제공합니다. 자체 작성 부분은 LICENSE.md로 범위를 확정했습니다. 개별 헤더 없는 upstream 파일은 원본 경로·커밋과 동봉 고지를 함께 보존하며, 자체 라이선스를 소급해 부여하지 않습니다. release/source-license-inventory.json은 152개 입력의 출처·고지 연결을 기록합니다.

도구 설치본, 상용 게임·BIOS·사용자 세이브·메모리 덤프는 제외합니다. 참고한 ludufre 2.16.4 ZIP의 펌웨어·FPGA·메뉴 자산은 이 소스에 합치지 않았습니다.

최종 source ZIP은 MCU 기본 소스와 mini FPGA 입력도 함께 제공합니다. [대응 소스 묶음](SOURCE-BUNDLE.ko.md)을 참조하세요. 파일별 원문·저작권과 적용 도구의 조건은 유지합니다.
