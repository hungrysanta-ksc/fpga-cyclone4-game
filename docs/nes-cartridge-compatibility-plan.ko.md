# NES 카트리지 호환성 확대 계획

1060 배포판과 첨부 ROM 7개를 기준으로 한 조사다. 1061 이무르 이동 시험은 현재 전달본으로 마무리한다. 이후 호환성 변경과 속도 변경은 서로 다른 비교판에서 측정한다.

## 헤더에서 보드까지

첫 대상은 SD에서 선택하는 일반 패미컴·NES 카트리지의 iNES 1.0과 NES 2.0이다. 둘 다 16바이트 헤더와 같은 식별자를 쓴다. 바이트 7의 비트 2–3이 이진수 10이면 NES 2.0 형식으로 해석한다. 구형 iNES의 오염된 예약 바이트, NES 2.0의 정상 확장 필드, 실제 잘린 파일을 별도 시험한다. UNIF는 별도 카트리지 컨테이너, FDS는 디스크 형식이다. VS·PlayChoice·PAL·Dendy·특수 주변기기는 식별한 기능과 실행 가능한 기능을 구분해 표시한다. [iNES](https://www.nesdev.org/wiki/INES) · [NES 2.0](https://www.nesdev.org/wiki/NES_2.0) · [서브매퍼](https://www.nesdev.org/wiki/NES_2.0_submappers)

ARM은 매퍼·서브매퍼, PRG/CHR ROM 크기, PRG/CHR의 휘발성 RAM과 배터리 RAM 크기, 미러링·4화면·매퍼 제어, 기종·타이밍을 정리한다. 512B trainer가 있으면 PRG 시작 위치와 초기 CPU 메모리 배치까지 처리한다. 사용 가능한 보드 중 이 요구사항을 만족하는 것을 선택한다. NES 2.0의 지수식 크기와 추가 ROM 영역도 경계를 검증하고, 미지원 조합은 누락한 기능을 표시한다. 기존 1060은 헤더 패턴과 용량을 보드별로 고정하고 MMC5는 DQ4 파일 CRC까지 확인한다. 로더 외에 FPGA 적재 길이, 주소 마스크, 캡처와 선행 CHR 주소, 저장 포맷의 크기 가정도 함께 점검한다. [1060의 기반 로더 생성 코드](../tools/prepare_cart_arm1056.py) · [보드별 주소·적재 조건](../tools/prepare_nes_carts1056.py)

NES 2.0에 명시된 구성을 우선한다. 구형 iNES에서 누락·충돌한 필드는 정확히 일치하는 덤프의 DB 기록과 실물 보드 자료로 보완하고, 보정한 필드와 근거를 디버그판에 남긴다. DB에 없는 한글 패치도 지원하는 구성이라면 실행 대상으로 삼는다. DB 대조용 해시는 trainer·헤더 등을 분리한 뒤 해당 DB의 규칙대로 계산한다. 배포판의 빠른 로딩을 위해 보정이 필요한 경우에는 기존 적재 중 계산하거나 별도의 작은 보정표를 쓰는 방식을 비교한다. 기존 배터리·퀵세이브 파일의 식별자는 보존한다. [NewRisingSun의 NES 2.0 XML DB](https://forums.nesdev.org/viewtopic.php?t=19940) · [Mesen iNES 로더](https://github.com/SourMesen/Mesen2/blob/master/Core/NES/Loaders/iNesLoader.cpp) · [Mesen 보드 DB](https://github.com/SourMesen/Mesen2/blob/master/UI/Dependencies/MesenNesDB.txt)

## 첨부 ROM으로 확인한 두 가지 설계 조건

- **테트리스 일본판.** 헤더는 수평 미러링이다. PRG+CHR CRC32 `B807446E`로 일치한 Mesen 항목은 수직 미러링, CNROM 서브매퍼 2다. 이 파일은 구형 헤더와 DB 충돌 시험으로 쓰고, 정상 수평 배선은 별도 표준 테스트 ROM으로 확인한다. [해당 DB 항목](https://github.com/SourMesen/Mesen2/blob/master/UI/Dependencies/MesenNesDB.txt#:~:text=B807446E) · [CNROM 버스 충돌의 의미](https://www.nesdev.org/wiki/INES_Mapper_003)
- **FF1&2 일본판.** PRG CRC32 `C9556B36`가 실물 HVC-SXROM-01과 일치한다. 512KiB PRG, 8KiB CHR RAM, 32KiB 배터리 SRAM을 포함한다. 두 게임 전환과 SRAM 네 뱅크의 독립 쓰기·전원 재실행·퀵로드를 인수 시험에 넣는다. 나머지 다섯 첨부 파일은 사용한 Mesen DB에서 PRG+CHR CRC가 일치하지 않았다. 원판 제목으로 패치판 배선을 추정하지 않는다. [실물 FF1&2 기판](https://nescartdb.com/profile/view/3642/final-fantasy-i-ii) · [MMC1 배선 변형](https://www.nesdev.org/wiki/INES_Mapper_001)

## 구현 순서와 대표 시험

| 단계 | 범위 | 대표 시험과 완료 조건 |
|---|---|---|
| 1. 판독기와 기존 보드 대조 | 같은 파일에서 현행 선택과 새 선택을 병행 기록. RAM 단위, trainer, 크기 초과·절단, 모호한 헤더, DB 미등록 패치, 지원 밖 기종을 시험 | 기존 드퀘4·FF3·커비·배틀토드·와이와이2·모아이군의 보드 선택과 저장 경로 보존. 현재 MMC5 전용 검사는 동등한 배선 검증이 마련된 뒤 완화 |
| 2. 단순 보드 | NROM(0), CNROM(3), UxROM(2) 및 기존 AxROM(7)의 용량·미러링·버스 충돌 조합 | Holy Mapperel로 모든 뱅크와 네임테이블 별칭 검사. 테트리스와 모아이군으로 SD 선택·배경·타일 뱅크 확인. 보드에 없는 네임테이블 RAM을 요구하면 보류 |
| 3. MMC1 | 256KiB CHR RAM형부터 SXROM 512KiB·배터리 RAM 뱅킹까지. 직렬 5회 쓰기, 리셋, 연속 CPU 쓰기 처리, 미러링 검사 | 젤다 1·2로 화면 전환·게임 저장 재개. FF1&2로 상위 PRG 절반과 저장 RAM 뱅킹, 슬롯 복원 후 다음 뱅크 쓰기까지 확인 |
| 4. MMC3 및 혼합 CHR | 현재 매퍼 4의 고정 용량을 풀고 191·192에서는 CHR 뱅크마다 ROM·RAM을 선택. 실제 PPU와 타일 공급기가 같은 물리 주소를 보고, RAM 쓰기가 표시 캐시에 반영되도록 검사 | MOTHER·메탈 맥스 한글판의 글자/배경 갱신, CHR ROM 쓰기 차단, IRQ와 슬롯 복원. 커비·모험도 4에서 기존 표시 경로의 회귀 확인 |
| 5. VRC6a(24) | PRG/CHR 뱅크, 미러링, IRQ, 확장음원 2펄스+톱니파 및 저장 상태 | 악마성 전설의 화면 분할·스크롤과 채널 출력을 각각 검사. 기존 VRC4 와이와이2로 회귀 확인 |

MiSTer의 `GameLoader`는 매퍼 플래그와 PRG·CHR 마스크를 카트리지에 넘긴다. `cart.sv`는 191·192를 공통 MMC3 경로로 분기하며, 소스에는 IRQ 타이밍 시험 관련 주석도 있다. 우리 보드에서는 이 구조와 개별 매퍼 동작을 참고하되 기존의 매퍼 계열별 FPGA 이미지 방식을 유지한다. DQ4 1061 계측 보드 한 개만으로도 15,275/15,408 LE와 56 M9K를 사용했다. [MiSTer 로더](https://github.com/MiSTer-devel/NES_MiSTer/blob/master/NES.sv) · [MiSTer 카트리지 RTL](https://github.com/MiSTer-devel/NES_MiSTer/blob/master/rtl/cart.sv) · [혼합 CHR 규격](https://www.nesdev.org/wiki/MMC3_with_CHR_ROM_and_CHR_RAM) · [1061 합성 결과](../analysis/nes-dq4-movement1061.json)

## 게임 수를 늘리지 않고 검증하는 방법

1. **목록 대조.** 메타데이터만으로 기종·매퍼·서브매퍼·메모리 구성별로 집계한다. 로컬 Mesen DB의 Famicom·NesNtsc 8,882항목 중 매퍼 0·1·2·3·4는 5,007항목(56.4%)이다. 판본·변형을 포함한 DB 행 단위의 개발 우선순위 지표다. 사용한 DB 파일의 SHA-256은 `200e19903f1b2eeda1f59a7f3bcdacf388d0f8d228f6f842373477ddc2f5a3e1`이다. [DB 필드와 원자료](https://github.com/SourMesen/Mesen2/blob/master/UI/Dependencies/MesenNesDB.txt)
2. **기능 대조.** Holy Mapperel로 PRG/CHR 뱅크 도달성, RAM, 미러링을 검사하고 MMC3 IRQ는 blargg의 개별 시험으로 확인한다. Mesen과 FPGA에 같은 레지스터 쓰기를 넣어 PRG/CHR 물리 주소·RAM 쓰기 허가·IRQ 시점을 비교한다. 배터리와 퀵세이브는 서로 다른 패턴으로 모든 뱅크를 채운 뒤 재실행·복원한다. [Holy Mapperel 원저자 저장소](https://github.com/pinobatch/holy-mapperel) · [NESdev 시험 목록](https://www.nesdev.org/wiki/Emulator_tests)
3. **우리 기기의 종단 시험.** 계열마다 위 표의 대표 ROM으로 SD 선택부터 실제 화면·소리, STOP·메뉴 복귀까지 확인한다. 보드 변경은 Quartus Lite 전체 FIT·STA를 거친다. 지원표에는 ‘헤더 판독’, ‘매퍼 기능 시험’, ‘대표 게임 실기’, ‘세이브·음원’ 결과를 각각 기록한다. 처리 속도는 드퀘4 이무르·모험도 4 같은 고정 동선으로 따로 비교한다.
