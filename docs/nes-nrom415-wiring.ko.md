# NES415: observer·screen 중재 공동 실행 준비

414의 실제 loader·프로그래머·run136 C fixture를 410 DPI 경계에 넣고, 227의 `nes_run_observer134`, `nes_pad_trace156`, `nes_ppu_history157`, `nes_screen_status151` RTL과 boot SPI에 선택 신호 기반 MISO 중재를 추가했다. 다른 선택 신호의 동시 주장에는 assertion을 넣었다. 실제 programmer·FatFS는 host C, 설정 핀과 PSRAM은 모델이다. observer의 CPU sample은 `run_enable`로, status의 SNES bus는 비활성 값으로 대체했으며 native display session과 base 장치는 모델이다. 실제 core나 표시·ROM workload가 아니다.

`wiring02`는 DLL 컴파일 및 Quartus 설치에 포함된 Questa `vlog`에서 RTL 구문 검사를 통과했다(0 errors/0 warnings). 생성기는 256바이트 이전 의도적 전송 중단 fixture이므로 실행하더라도 실제 run136의 START 이후를 검증하지 않는다. 기존 411 전체 시험이 단일 Starter FLOAT seat를 점유해 **415 시뮬레이션은 실행하지 않았다.** `wiring01`은 임시 source 사본에 4개 RTL을 빠뜨려 실패했으며 `wiring02`가 선택 컴파일이다. raw 로그는 `probes/nes-nrom415/wiring02`, 해시는 `analysis/nrom415-wiring.json`이다.

411은 다른 실행으로 2026-10-28 확인 시 311,296/393,216 DATA까지 진행됐으며, 아직 전체 종료·readback·START·STOP 결과가 없다. 이 실행에는 415 변경이 들어가지 않는다. 415는 실제 보드 top의 native·sink 및 클록·reset 경계를 대체하지 않고, 선택 충돌과 관측 결과는 실행 전이므로 미검증이다. 413/414의 모델 시험 PASS를 415 전체 RTL의 PASS로 합치지 않는다.

다음에는 411 종료 후 415 prefix의 실제 observer 초기 응답·선택 독점을 먼저 실행한다. 그 다음 전체 전송과 실제 run136, 실제 native session·표시·base 복구 및 observer 중재를 같은 실행으로 연결한다. 실제 ARM·IRQ·ROM 경쟁과 연속 프레임 시간, MMC4/5의 같은 경계 Quartus Lite 비용은 계속 미측정이다. Lite 전체 MAP 407의 NROM 고정 profile과 402 후보 및 MMC4/5는 서로 다른 경계이므로 수치를 빼거나 더하지 않는다.
