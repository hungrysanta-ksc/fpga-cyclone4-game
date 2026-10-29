# NES416: observer 실행 준비 및 실제 표시 경계

415 생성기에 `--run`을 추가했다. 기본값은 기존과 같이 DLL·RTL 컴파일만 수행하고, `--run`은 승인된 FLOAT wrapper에서 실제 256B prefix 시뮬레이션을 요청한다. `wiring03`에서 수정된 기본 경로의 DLL·RTL 컴파일은 통과했다. **`--run`은 아직 실행하지 않았다.** 411이 단일 Starter seat를 사용 중이며 다른 시뮬레이터를 찾지 못했다. 415 prefix는 256번째 DATA 후 중단되므로 실행해도 시작 전 observer 응답과 기록만 확인하며 screen·RUN·STOP·base를 검증하지 못한다.

속도 조건을 확인해야 한다. 227 `nes_run_observer134.sv` 주석과 `nes-sink-board165-contract.ko.md`의 기존 시험은 observer SPI를 250kHz 이하로 기술한다. 실제 227 `nes_game149_spi.inc`는 84MHz SPI의 BR=4(2.625MHz)를 사용하고 415 fixture도 2.625MHz다. 이것만으로 2.625MHz 동작 실패가 입증된 것은 아니다. 그러나 250kHz 시험을 2.625MHz 보증으로 재사용할 수 없으므로 실제 clock·CS와 위상별 observer/status 응답, MISO 독점, reset/STOP 유지, CDC/STA를 별도로 검증해야 한다. 기존 227 실기 기록은 새 NROM fixture의 위상·타이밍 signoff가 아니다.

실제 표시 경계는 227 `native_session165`의 preflight, `nes_display_enter146`, postflight, `native_boot172`, `nes_runtime165_begin/step`, display leave 및 STOP과 `nes_live_joint`, `nes_sink_bridge165`, SNES 버스·65816 소비·final ACK를 포함한다. 기존 222 host 시험은 session 제어·오류 분기를 실행하지만 runtime·SPI/reset은 모델이다. 213 C 프레임 재생도 FPGA와 SNES ACK가 모델이다. 415에는 이 전체 표시 경로가 연결되어 있지 않다.

실제 base 복구 역시 412의 programmer C와 synthetic RLE·GPIO/DONE 모델만으로는 완료가 아니다. 실제 재구성 모델 또는 보드, base SPI token, 메뉴 복사·SNES release 및 IRQ 복원까지 같은 세션에서 확인해야 한다. 새 장치 모델을 실제 하드웨어 결과로 표시하지 않는다.

411의 마지막 확인은 339,968/393,216 DATA였으며 아직 완료·readback·START/STOP 결과가 없다. 이 시험은 415/416 observer와 412 실제 프로그래머를 포함하지 않는다. 402 live06의 8,858,219 ARM 명령, SPI 53,011B, ROM 71,964쌍 및 warm 최대 34.048237ms는 해당 fixture의 실제 M4·SPI·IRQ·ROM 결합 결과지만 CPI1과 65816 header/view/HDMA envelope가 포함된 제한 결과다. 914/915 VBlank가 부족했고 전체 Lite MAP은 20,199LE/16,508조합 논리다. 227 실기 465ACK/60.06초와 직접 개선률로 비교하지 않는다.

후속 확인에서 411은 393,216 DATA 쓰기를 마치고 readback ACK 16,384까지 진행했다. 아직 전체 readback·START/STOP PASS가 아니다. 415 생성기는 초기 SPI 시작 위상을 `--phase-ns` 0..46으로 지정할 수 있게 확장했고 17ns fixture `wiring04`는 DLL·RTL 컴파일만 통과했다. 각 위상 시뮬레이션 및 선택 중재 assertion은 실행 전이다. 이 시작 위상 변화가 물리적 CDC·STA 전체 검증을 대체하지 않는다.

MMC4 mapper10은 live latch와 실제 ROM 경쟁이 아직 연결되지 않았다. MMC5 mapper5는 기존 13bit tag 대비 최대 CHR에 16bit가 필요하고 합성 split 스트레스는 예외 3,808개로 현 한도 128개를 초과했다. 이는 선택 자극의 반례이지 실제 mapper별 전체 시간·회로 측정이 아니다. 동일 workload·ROM 위상·ARM/IRQ/SPI/65816/VBlank·독립 검사·STOP/final ACK 및 mapper별 전체 Lite MAP/FIT/STA가 필요하다. 두 mapper의 추가 시간·회로 비용은 null로 유지한다.
