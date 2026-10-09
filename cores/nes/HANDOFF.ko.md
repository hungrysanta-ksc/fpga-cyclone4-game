# NES 현재 인계 —122 보호 reader 코어 회귀 통과

[122 결과](../../analysis/SAFE122-RESULT.ko.md) · [검증 메타](../../analysis/safe122-verification.json) · [121 비교 기준](../../analysis/FRAMES121-RESULT.ko.md)

## 바로 이어 할 작업

**READ16/168MHz 등록형 CF86 reader 후보의 실제 클록·자원·STA 가능성을 먼저 확인한다.** 정상 속도 코어의 전체 프레임 회귀는 끝났다. 같은 회귀나119의80KiB·BASE·ENTRY 시험을 이유 없이 반복하지 않는다. 이번 변경은 테스트벤치 바인딩과 파라미터이며 제품 RTL·펌웨어는 그대로다. 아직 보드에 설치할122 패키지는 없다.

보드 후보에서 기존8MHz 로더의 WRITE3클록=375ns를 유지할 도메인 분리 또는 시간 매개변수화를 결정한다.168MHz에 그대로 연결하면17.856ns여서 이전 쓰기 근거가 사라진다. guard085의8MHz memory/20–22MHz reference heartbeat·timeout도 새 클록에 맞춰 검증해야 한다. raw fault 비동기 취소,각 도메인 동기 reset 해제,로드/CHECK/RUN 독점 소유권을 보존한다. 같은 후보 PLL/핀/CDC/내부 STA·실제 SNES 소비자/DMA/표시 기한까지 연결한다.059의959/963LAB·가상핀·PLL0이나 진단191LAB를 최종 여유로 재사용/단순 합산하지 않는다.

168MHz가 물리 fit/STA에서 불가능하면 reader/서비스 구조를 수정한다. NES 감속·프레임 버림·데이터 검사 제거로 숨기지 않는다. 최소 RUN의 관측·오류 종료·독립044복원 경로가 준비되면 실기를 우선한다.

구체적 출발점은 [변경하지 않은 safe reader](../../src/nes/diagnostic/nes_diag_safe_rom_physical.sv), [8MHz 로더](../../src/nes/diagnostic/nes_diag_rom_loader.sv), [guard085](../../src/nes/diagnostic/nes_diag_clock_guard085.sv)다. [086 보드 구성 도구](../../tools/nes_clock_reset086.py)와 [059 전체 코어 구성 도구](../../tools/nes_spi_readback_checks.py)는 연결 구조를 확인하는 자료로 사용한다. 각각 따로 통과한 수치를 합쳐 통합 통과로 처리하지 않는다. 실제 클록 선언·PLL 생성·핀 매핑과 같은 빌드에서 자원/미배치 핀/타이밍 예외/CDC 목록을 남겨야 한다. loader와 reader가 다른 도메인이 되면 정지·소유권 인계가 두 핀 구동기를 동시에 활성화하지 않는지 확인한다.

## 이번에 확인한 사실과 경계

- failed01: CF86 safe reader READ8/84MHz·70ns는 첫 fine_x/위상3.5ns에서 CPU deadline tick852209.852198 PPU요청→852199 CPU주소변경→852204 CPU수락→852208 CPU소비 시미완료. 다른 사례를 실패했다고 확대하지 않는다.
- unit01: 위 READ8 reader 단독16위상8,400완료/208취소·110ns 거부 PASS. 단독 핀 PASS와 공유 CPU/PPU 기한은 다르다.
- full02: 동일 safe RTL, READ16/168MHz 제어,70ns 모델.3.5/0/5.625ns×fine_x/banks32×4프레임=24프레임/1,474,560픽셀 및패킷/PPU이벤트일치.95.232ns 캡처 접근 시간은 READ8/84MHz와 동일. 코어46.560ns는 유지했다.
- unit02: READ16,16위상0..5.625ns,8,400완료/208취소. 정상 샘플 후 HOLD5.952ns/CE활성101.184ns와 응답 전 핀 해제 관측.110ns 및 HOLD제거 변형 거부. 비동기 reset취소는 별도다.

고정지연 모델이며 메타안정성·보드패드/PCB·전압/부하·모든 위상/지터 보증이 아니다. CHECK=0이고 SPI로더/STM32/guard/PLL/실제SNES프로그램은 통합되지 않았다. 자체 입력은80/96KiB,배경전용·불변CHR이다. 새 제품RTL/C/ARM/fit/STA/ASM/SD패키지는 없다.168MHz는 reader 내부 제어 목표이며 PSRAM168MHz 동기버스를 뜻하지 않는다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 보존

`run_nes_safe_reader122.ps1`과 `run_nes_safe122_unit.ps1`은 Python/기존 FloatWrapper/QuestaBin/핀된052live Baseline/새 ASCII Out을 받는다. 기존 FLOAT RunOnly 한 좌석으로 직렬 실행한다. uncounted 라이선스·smoke 반복은 금지한다. `verify_nes_safe122.py --evidence <frozen122>`는 새 시뮬레이션 없이 동결 해시/실패이력/프레임을 재검증한다. full02/unit02가 최종이고 failed01/unit01 실행 당시 소스도 보존한다. 완료 finalizer 재실행이나044–113/116/118/120–122 동결 자료 수정은 금지한다.

PR67 병합 `79daf3f539c1f0956d71f2fc50c0984e3293c4ef` 확인. 한국어 PR제목과 작업 목표·작업 내용·작업 결과·작업 의미 네 항목을 유지하고 사용자만 병합한다. GBC152·원래NES334·과거 공개 소스 핀을 보존한다. ROM/바이너리/미디어/라이선스/개인 경로는 Git에 올리지 않는다.
