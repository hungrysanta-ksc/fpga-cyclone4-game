# NES 현재 인계 —123 물리 배치 성공, 교차 클록 타이밍 미해결

[123 결과](../../analysis/CLOCK123-RESULT.ko.md) · [검증 메타](../../analysis/clock123-verification.json) · [122 기능 기준](../../analysis/SAFE122-RESULT.ko.md)

## 다음 작업의 우선순위

**코어 초기화/reset을 각 도메인에 연결하는 방식과 묶음 데이터 CDC 제약부터 해결한다.** 168MHz reader의 같은 클록 내부 setup은 최종 fit02에서3corner 최솟값+1.432ns다. NES+9.014ns,host84+2.885ns다. 클록 속도를 낮추는 것부터 시작하거나 변하지 않은122 전체 프레임을 반복하지 않는다. 전체 raw slack은−8.104ns이며 전기적/전체STA통과가 아니다.

123의 `nes_clock_fit123.py`가 생성한 `nes_live_joint.sv`에서 `reset_request=boot_reset||!run_enable`, `reset=reset_request||!memory_ready`이고 memory_ready는 코어 도메인의 local_memory.init_done이다. 이 reset이84MHz transport와168MHz reader로 전달된다. 원시60개 최악 경로에는 init_done→다른 도메인의 데이터/reset 입력 위반이 있다. 비동기 assert와 도메인별 동기 release를 유지하는 연결을 구현하고, 기존 reader 안의 source_reset/memory_reset 및 raw reset gating과 중복·우회를 함께 검사한다. 단순 전 클록 false-path는 금지한다.

그다음 reader address_hold/data_hold와 request/ack toggle,영상 bridge의 req/reply 묶음 데이터에 대해 실제 안정 유지 구간과 동기화 단계를 조사한다. 데이터의 종착점이 CPU의 직접 소비 조합 경로까지 이어지는 경우도 포함한다. 같은 라우팅DB에서 경로 최대지연·정확한 제약을 검증하며 handshake의 존재만으로 모든 CDC를 통과 처리하지 않는다. 전체 IO는 미제약 상태다.

## 확정된 결과와 범위

fit02: EP4CE15F17C8,13,558LE,938/963LAB(25남음),26M9K,PLL1개. 보드 핀표와일치하는 PSRAM/CLKIN/SNES_SYSCLK46개 물리핀,가상264핀이다. PLL은8MHz에서84/168MHz를 만든다. 코어 STA22MHz는 보수적 목표이며122 기능 시뮬레이션은21.477MHz다. 코어·reader 공통 소스는122와같다. 차이나는 TB/메모리모델2파일은 합성하지 않는다.

로더/CHECK·guard·실제SNES프로그램은 제외한 읽기 전용 가능성 검사다. RUN/reset/컨트롤·SNES버스/관측은 가상입력이다.25LAB는 최종 통합 여유가 아니다. full123 빌드나 설치패키지가 있다는 뜻이 아니다. fit01은 PPU 관측주소3개가 미지정 물리핀으로 바뀌었고,fit02는 기능 경로 밖의 보존 관측레지스터로 이를 분리했다. 첫fit/audit경로오류·UTF8보고서해석오류도 보존한다.

그 뒤 로더 WRITE375ns와 guard의 감시시간·소유권을 보존하며 통합한다.8MHz의 WRITE3클록을168MHz에 그대로 옮기면17.856ns가 된다. 도메인 분리/쓰기시간 매개변수화 중 실제 설계를 정하고 로더·CHECK·RUN 핀 구동이 겹치지 않는지 확인한다. 실제SNES소비자/DMA/표시 기한,새RUN 진행관측·오류종료·독립044복원 준비 후 실기로 간다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 보존

`nes_clock_fit123.py --baseline <pinned059fit> --out <newASCII> --quartus-bin <bin64>`은 map/fit/STA를 실행한다. 같은 출력 디렉터리에 `nes_clock_audit123.tcl`을 복사해 `quartus_sta -t`로 클록쌍을 조사한다. 동결 DB에서 직접 쓰지 말고 새 작업 사본을 만든다. `verify_nes_clock123.py --evidence <frozen123>`은 재빌드 없이 증거를 검증한다. 기존044–113/116/118/120–123 자료·완료 finalizer는 수정/재실행하지 않는다. 제품 소스는 그대로이며 새 C/RTL/ARM/ASM/실기이미지/Questa 작업은 없다.

PR68 병합878c8ce 확인. 한국어 제목과 작업 목표·작업 내용·작업 결과·작업 의미 네 항목을 지키며 사용자가 병합한다. GBC152·원래NES334·모든 과거 공개 핀은 보존한다. ROM/바이너리/미디어/라이선스/개인경로는 Git에 올리지 않는다.
