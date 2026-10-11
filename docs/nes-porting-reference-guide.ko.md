# NES 이식 참고 자료와 적용 순서

2026-10-11 검색·소스 대조. 사용자 요청에 따라158의 수정·기능 시험·배치 검증을 정리한 뒤 조사했다. 이 목록은 검증되지 않은 코드를 일괄 교체하는 계획이 아니라, 현재 이식 경계를 비교하는 기준이다.

## 이미 가져온 것과 새로 맞추는 것

현재 CPU·PPU·APU·MMC3 기반은 [NES_MiSTer](https://github.com/MiSTer-devel/NES_MiSTer)이며, 저장소 `analysis/source-lock.json`에 **49a0a662e244469ca77b2155746a066df704ffae**로 고정돼 있다. `analysis/mmc3-unit-verification.json`에 기존 매퍼 단위 검증도 있다. 따라서 매퍼를 처음부터 다시 구현하거나 기존 단위 시험 전부를 반복할 필요가 없다.

FXPAK Pro에 새로 맞춘 부분은 PSRAM 읽기·중재·클록 경계, STM32 ROM 적재/복귀, SNES 화면 소비·패드 연결이다. 원본 매퍼가 동작해도 이 경로가 필요한 시점에 데이터를 공급하지 못하면 게임이 멈춘다.157에서 확인한 것은 물리 CHR주소 변경 직후의 공급 실패이며 특정 매퍼 쓰기의 실기 원인까지 확정한 것은 아니다.

## 우선 사용할 자료

| 자료 | 확인한 내용 | 우리 작업에 쓰는 방법 |
|---|---|---|
| [고정 NES_MiSTer 상위 연결](https://github.com/MiSTer-devel/NES_MiSTer/blob/49a0a662e244469ca77b2155746a066df704ffae/NES.sv#L897) | SDRAM ch0은 PPU/적재, ch1은 CPU, ch2는 저장 계통이며 ch0/ch1 busy는 이 연결에서 소비하지 않는다 | 메모리 지연이 이미 맞춰진 원본의 전제를 확인한다. 우리 단일 outstanding PSRAM/CDC 경로와 요청·데이터 샘플 간격을 비교한다 |
| [MiSTer SDRAM 구현](https://github.com/MiSTer-devel/NES_MiSTer/blob/master/rtl/sdram.sv) | 3요청 채널, ch0→ch1→ch2 순서, 이전16비트 워드 재사용 및 읽기 데이터 반환 상태가 있다 | 중재·짧은 재접근 처리의 비교 자료. SDRAM 전용 명령/타이밍을70ns PSRAM에 그대로 복사하지 않는다. 이 링크는 이동하는master이므로 채택 시 커밋을 새로 고정한다 |
| [MMC3 프로그래밍](https://www.nesdev.org/wiki/Programming_MMC3), [MMC3 레지스터](https://www.nesdev.org/wiki/MMC3) | 8000의 레지스터 선택·뱅크 모드,8001의 데이터 쓰기와 CHR배치 관계 | bank-data만 보지 말고 CHR A12 반전도 비교한다. 본문 직접 열기는403이라 검색 색인과 아래 실제 구현을 교차 확인했으며 전 문서를 읽었다고 주장하지 않는다 |
| [Mesen2 MMC3 구현](https://github.com/SourMesen/Mesen2/blob/master/Core/NES/Mappers/Nintendo/MMC3.h) | WriteRegister에서8000/8001 뒤 UpdateState, CHR모드별 배치, R0/R1 하위비트 처리 | FPGA와 독립된 동작 대조군. 동일 게임의 매퍼 쓰기 순서를 필요할 때만 확인한다. 소프트웨어의 즉시 메모리 접근을 FPGA 외부 버스 지연 증명으로 쓰지 않는다 |
| [NESTang](https://github.com/nand2mario/nestang) | Gowin Tang 계열 이식, HDMI·음원·SD 메뉴·컨트롤러·다수 매퍼를 가진 공개 프로젝트이며 현재 TangCore 통합을 안내한다 | 다른 제조사 FPGA로 플랫폼 계층을 분리한 사례. 이번에는README까지 확인했고 세부 SDRAM·오디오 RTL의 동일성/타이밍은 미검증이다. 향후 해당 경계가 막힐 때만 파일을 선정해 비교한다 |
| [MiST NES](https://github.com/mist-devel/nes) / [초기 FPGANES](https://github.com/strigeus/fpganes/blob/master/README.md) | MiST 포트 저장소와 Nexys4/Xilinx ISE용 원형을 확인했다 | 같은 계열의 이식 이력 참고. Nexys4의 UART ROM·패드 방식은 우리의 STM32/SNES 연결과 다르다. 구형 구현으로 무조건 되돌리지 않는다 |
| [NES test ROM 소스 모음](https://github.com/christopherpow/nes-test-roms) | 공개된 에뮬레이터 검사용 소스/ROM 모음 | 매퍼 IRQ·DMA·PPU 등 실제 실패와 직접 관련된 시험만 선택한다. 모든 시험을 통과할 때까지 실제 게임을 미루는 새 관문을 만들지 않는다 |

## 이번158과 이후 판단

원본의 **매퍼 기능 계약**과 우리 **메모리 공급 계약**을 분리해서 판단한다.158은 실제 뱅크 레지스터를 먼저 바꾸지 않고, 이미 제시된 CPU 쓰기 값을 선행 조회에만 적용한다. 기존 physical-tag 검사와 샘플 기한은 그대로다. 이 접근이157 실기 실패의 해결인지는158 SMB3 로그가 결정한다.

다음158에서도 같은 주소 전환으로 실패하면 고정 뱅크 시험을 다시 돌리지 않는다. 최소 이력과 소스로 매퍼 쓰기인지 PPU 논리주소 전환인지 확인하고, 현재 예측 방식의 한계인지 판단한다. 반복적인 예측 예외 추가가 필요해지면 원본의 메모리 시간 계약을 기준으로 서비스 구조 자체를 재검토한다. 새로운 대형 캐시·코어 정지를 먼저 도입하지 않는다.

게임이 진행되면 이동·점프·스크롤을 먼저 확인하고, 현재 진단용 음원 차단을 해제하는 작업으로 간다. DMA·사운드 자료는 실제 재발 경계에 맞춰 조회한다. 부품 식별·SD쓰기·메뉴 복귀·044복원처럼 이미 확인한 공정을 다시 선행조건으로 삼지 않는다.

다른 코어에서도 같은 순서를 사용한다: **출처/고정판과 기존 검증 확인 → 플랫폼별 메모리·클록·화면·입력 차이 확인 → 바뀐 경계의 최소 검사 → 실제 목표 ROM**. 원본 전체 업그레이드, 새 매퍼 일괄 활성화, 동결 소스 덮어쓰기는 별도 근거 없이 하지 않는다. 적용할 파일의 출처·기존 라이선스 표기·변경 경계를 보존한다.
