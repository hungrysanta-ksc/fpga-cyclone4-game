# NES 주요 진전

이 문서는 개발 단계의 색인이다. 진단 통과는 일반 게임 또는 제품 완료를 의미하지 않는다. 원시 로그는 공개하지 않고 후보별 요약·계약·해시를 제공한다.

| 단계 | 진전과 관측 | 근거 |
| --- | --- | --- |
| 001–018 | upstream/고지 조사, 자체 CPU·PPU·DMA·IRQ 진단, 자원 조사 | [source lock](../../analysis/source-lock.json), `analysis/*RESULT*` |
| 019–032 | 영상 부하·스크롤·CHR/뱅크·전송 큐·CDC·SNES 경계의 제한된 실현 가능성 | [누적 기록](history/README-053.md) |
| 033–036 | 가독성 있는 LINK SCREEN 진단, MCU GPIO 파형 재생. 이전 SPI 응답 비트 밀림을 보존·수정 | [SPI 결과](../../analysis/H1-SPI-RESULT.ko.md) |
| 037–043 | 자동 메뉴 복귀 실패. 종료 로그·일관된 오류 사건·입력 샘플링 조사. 원래 SDF 실패 보존 | [누적 기록](history/README-053.md) |
| 044 | 실기 화면 순환·RESET 복구, GBC 정상 플레이 보고 | [실기 기록](../../analysis/H1-HARDWARE-044-RESULT.ko.md) |
| 045–046 | 메모리 패킷 생산기와 제한된 NCR1 BG 인코더 | [045](../../analysis/PACKET-MEMORY-RESULT.ko.md), [046](../../analysis/NCR1-ENCODER-RESULT.ko.md) |
| 047 | 실제 코어 PPU→인코더→전송 연결, 8프레임/491520픽셀 비교 | [047](../../analysis/NCR1-LIVE-RESULT.ko.md) |
| 048 | OAM 쓰기 구조 최적화, 216362클록 비교. 870 LE 절감 | [048](../../analysis/OAM-BANKED-RESULT.ko.md) |
| 049 | 12 KiB 로컬 RAM·초기화 연결 | [049](../../analysis/LOCAL-MEMORY-RESULT.ko.md) |
| 050–051 | 공유 ROM 서비스 마감 오류 재현 및 조기 읽기, 2–4클록 모델 통과 | [050](../../analysis/ROM-SERVICE-RESULT.ko.md), [051](../../analysis/ROM-EARLY-RESULT.ko.md) |
| 052 | PSRAM 읽기 핀·서로 다른 클록 연결, 16위상 검사 | [052](../../analysis/ROM-PHYSICAL-RESULT.ko.md) |
| 053 | 핀으로 ROM 적재 후 코어 실행, 8프레임/491520픽셀. 공동 929 LAB | [053](../../analysis/ROM-BOOT-RESULT.ko.md) |
| 054 | SPI 프레임·C 파형·80KiB 전체 적재/읽기, 공동948LAB | [054](../../analysis/SPI-BOOT-RESULT.ko.md) |
| 055 | 96/80KiB SPI 적재 후 실제 코어2종8프레임·491520픽셀,053 이벤트 비교 | [055](../../analysis/SPI-LIVE-RESULT.ko.md) |
| 056 | STM32 SD 검증·적재·복구 바인딩,26호스트/18입력 거부,29024응답 비트, ARM 전체 링크 | [056](../../analysis/MCU-LOADER-RESULT.ko.md) |
| 057 | 승인된 로더 형상→코어 mask,입력 변조 후8프레임 동일,새954LAB/9여유 | [057](../../analysis/ROM-GEOMETRY-RESULT.ko.md) |
| 058 | 실행 전 공유 CHECK 포트,180238읽기·4096요청 차등·오류 대조,공동949LAB | [058](../../analysis/ROM-READBACK-PORT-RESULT.ko.md) |
| 059 | SPI CHECK/held data·tag/순서ACK/실행 gate,MCU 비교,8프레임 회귀,공동959LAB | [059](../../analysis/SPI-READBACK-RESULT.ko.md) |
| 060 |SD 적재·읽기 비교·STOP 복구,41경우/18거부,72312C GPIO 응답 비트,ARM 링크 | [060](../../analysis/SD-READBACK-RESULT.ko.md) |
| 061 |CPU 없는 적재 진단135핀/PLL,8MHz PSRAM,C GPIO·START 이중 차단·정지 클록 reset,186LAB/44M9K·내부 STA | [061](../../analysis/BOARD-DIAGNOSTIC-RESULT.ko.md) |
| 062 |CF61/형상 확인·수동 메뉴3호출·복구 로그,41SD/18입력/16메뉴,ARM호출·72320C GPIO응답비트 | [062](../../analysis/MENU-DIAGNOSTIC-RESULT.ko.md) |
| 063 |80/96KiB 전체 C→보드 핀 적재/비교/ACK/FINISH/STOP,50,464,224응답 비트; 생산 소스 보존 | [063](../../analysis/BOARD-SESSION-RESULT.ko.md) |
| 064 |진단 SD/FPGA/UART 대기·오류 반환,LED/진행·FatFS 보호·ARM 호출;전체 SPI063 동일 | [064](../../analysis/DIAG-RECOVERY-RESULT.ko.md) |
| 065 |메뉴 버퍼/전체 비교·SPI/TIM2/FatFS/로그 종료·RESET 이후 보호·ARM 호출 | [065](../../analysis/MENU-RETURN-RESULT.ko.md) |

| 066 | 오프라인061 FPGA/065 ARM 쌍·정확한 압축 복원·SD 백업/복원 모형 | [결과](../../analysis/PAIR-PREFLIGHT-RESULT.ko.md) |
| 067 | 진단 메모리 SETUP/샘플HOLD,정상4/실패4,bounded C 파형,새184LAB/내부STA30 통과 | [결과](../../analysis/DIAG-MEMORY-RESULT.ko.md), [Sol 인계](../../docs/development/NES-067-SOL-HANDOFF.ko.md) |

| 068 | PSRAM 초기대기/보호제거 대조,routed3168경로와외부예산,새195LAB/내부STA,클록정지반례 | [결과](../../analysis/DIAG-SAFETY-RESULT.ko.md) |

다음은 [제한된 진단의 관측/종료·외부 타이밍·쌍 구성](HANDOFF.ko.md)이다. 053 공개 메모리 회귀·054 SPI·056 MCU 시험은 [재현 안내](REPRODUCING.ko.md)에 구분하며 과거 실제 코어 실행을 다시 실행한 것으로 계산하지 않는다.

- **069 CF68 MCU 연결**: READY-before-GPIO/CF68·구형 거부/shared fault 보호, 하위95·상위41/18/16+추가3/native2·대조7, bounded C72320비트·ARM 링크. 전체 C 캡처180224bytes는 새 보드 전체 재생 전이며 FPGA068 fit만 재사용. 설치 불가.

- **070 전체 CF68 세션**: 실제069C→068핀80/96KiB180224byte/901152frames/50464224응답비트·마지막ACK/FINISH/STOP,원래클록prefix64/parked8192·응답대조1. [결과](../../analysis/CF68-SESSION-RESULT.ko.md), [계약](../../docs/nes-cf68-session-contract.md). 새쌍/실기 미완료.

- **099 RTC 종료 보호**: RSF/INITF 대기 한도, 실제 RTC/main/FatFS30경우·대조4·ARM 검증. 하위 IO·실기는 미완료. [099 결과](../../analysis/RTC099-RESULT.ko.md).

- **100 실제 하위 SPI**: SRAM·FPGA 명령·SPI 연결과 오류 후 CS LOW/DR 접근 차단.34경우·대조5·ARM, 주변장치/물리 핀은 미완료. [100 결과](../../analysis/LOWER100-RESULT.ko.md).

- **101 SPI 완료 순서**: TXE→BSY 순서 수정,336위상/오류+34통합+4보호대조+2원본반례/ARM. 강제 중단은 미완료. [101 결과](../../analysis/SPI101-RESULT.ko.md).

- **102 최종 정지**: CS 해제→GPIO 분리→SPI1 reset 유지.1024핀/21통합/6대조/1원본/ARM MMIO16, 최초오류부터 진입지연은 미완료. [102 결과](../../analysis/QUIESCE102-RESULT.ko.md).

- **103 오류 관측**: 공유 오류의 LED/UART 이전 정리, 실제 observer/printf/UART54호스트/6대조/ARM MMIO16. timer/CIC/물리시간 미완료. [103 결과](../../analysis/OBSERVER103-RESULT.ko.md).

- **104 타이머·IRQ**: 실제 timer/SysTick/LED/CIC/RESET 통합, 진단 ISR printf 재진입 수정.85호스트/6대조/ARM 분기 검증. 최종 파일조합·외부IO·실기 미완료. [104 결과](../../analysis/TIMER104-RESULT.ko.md).

- **105 최종 파일 조합**:11역할/정상1·거부23,094 로그의RESET-held 범위 정리. 디버깅 기반의 검증/배포 준비이며 배선·게임기능 추가 아님. [105 결과](../../analysis/PAIR105-RESULT.ko.md).

- **106 실기 조건**:3168경로 재계산, CE HIGH 외부예산109.565ns/경계 산술과관측600초 운영정책 정의. E1전기범위/E2공통고장 미완료. [106 결과](../../analysis/TRIAL106-RESULT.ko.md).

- **107 보드 자료 조사**: 공개 KiCad192blob/고정14입력 확인, 구형 회로도와Pro Rev.D 구분, 공통HSE·NMI 미처리 루프 확인. CSS/NMI 후속 구현·측정 계약. 새 코어 배선/실기 PASS 없음. [107 결과](../../analysis/BOARD107-RESULT.ko.md).

- **108 CSS/NMI 종료 구현**: 진단 소유권·고장고정·직접RESET/nCONFIG/SPI종료, 실제C63/대조4/ARM강한벡터 및무호출경로 검증. 전체native/전기적조건/실기 미완료. [108 결과](../../analysis/CSS108-RESULT.ko.md).

- **109 CSS 통합·파일 조합**: 실제108 C와native SD/메뉴38건·보호대조4건,11역할 새pair/정상1+거부23. 생산코드 변경/실기 없음. [109 결과](../../analysis/CSS109-RESULT.ko.md).
- **110 제한 실기 선택안**: 전기적 보증과정상80KiB 1회시험을구분, 검토ZIP13항목/9역할확인. 사용자선택/실기미완료. [110 결과](../../analysis/TRIAL110-RESULT.ko.md).

- **111 제한 실기 발행**: 사용자 명시적 선택을 기록하고80KiB 1회 시험/정확044 복원 ZIP12항목을 제공. 실기 결과 대기. [111 결과](../../analysis/TRIAL111-RESULT.ko.md).

- **112 단계 로그 개선판**: 111 짧은관측을 반영, write/sync/close 체크포인트·16KiB진행·기존예산보존과고장후IO금지 검증. 새ARM/80KiB패키지 제공, 실기결과대기. [112 결과](../../analysis/CHECKPOINT112-RESULT.ko.md).

| 113 | 112 무로그 중단 재현·bounded SD 읽기 인계 수정·진입 전용113 제공,실기 대기 | [113](../../analysis/ENTRY113-RESULT.ko.md) |

| 114–116 | 실기80KiB 적재·전체 비교·STOP 통과, BASE_START 이후 복구 미완료.116 복구 전용 진단 제공 | [116](../../analysis/BASE116-RESULT.ko.md) |

| 117–118 | 짧은116 복구·메뉴 실기 통과,같은ARM 전체80KiB 통합복구 전달물 | [118](../../analysis/FULL118-RESULT.ko.md) |

- **119–120**: 전체80KiB 검증·메뉴·044복원 실기통과. 정상코어70ns 3클록오류,7/8클록제한구간통과,8클록핀16위상통과. [120](../../analysis/CORE120-RESULT.ko.md).

- **121**: READ8/70ns 두입력×3위상,24프레임/1,474,560픽셀·패킷·이벤트일치. 보호 reader 고속통합이 다음. [결과](../../analysis/FRAMES121-RESULT.ko.md).

- **122**: 등록형 reader READ8/84MHz 실제 CPU 기한 실패를 보존하고 READ16/168MHz·95.232ns 접근 후보의24프레임/16위상 핀 검증 통과. 보드 클록·로더·STA는 다음. [결과](../../analysis/SAFE122-RESULT.ko.md).

- **123**: 실제PLL/PSRAM46핀 포함 코어 배치 성공.938LAB/PLL1,reader168MHz 동일클록 setup+1.432ns. 교차클록/reset raw−8.104ns·외부IO미해결. [결과](../../analysis/CLOCK123-RESULT.ko.md).

- **124**: 실제 코어/reader/영상 reset 동기해제 배선,4프레임245760픽셀,reader16위상·bridge/호스트reset통과.933LAB/동일클록STA통과,묶음CDC/외부IO미완료. [결과](../../analysis/RESET124-RESULT.ko.md).
