# NES417: 공동 readback 진행과 observer 위상 시험 준비

411은 393,216B DATA를 모두 기록한 뒤 독립 readback ACK 299,008까지 진행했다. 이 수치는 확인한 시점의 진행 지점이며 전체 readback, FINISH, START, STOP, base 복구 PASS를 뜻하지 않는다. 현재 411은 412/415의 실제 프로그래머·observer/screen을 포함하지 않고 host C와 PSRAM 기능 모델을 쓴다.

`tools/test_nes_nrom417_phases.py`는 승인된 FLOAT wrapper 아래 415 prefix를 시작 위상 0·11·23·35·46ns로 각각 실행하고 결과와 bench 해시를 저장하도록 준비한 runner다. SPI 2.625MHz에서 initial identify observer와 256B DATA, MISO 선택 충돌 assertion을 시험하도록 구성했다. 411이 단일 seat를 사용해 이 runner는 **아직 실행하지 않았다**. 위상 표본은 전체 CDC/STA 검증이 아니며 prefix에서 START 이후 screen·STOP·base는 검증되지 않는다. 실제 native display, SNES bus/65816 final ACK와 실제 base token/menu 복구도 따로 연결해야 한다.

402의 M4/SPI/IRQ/ROM 결합 fixture는 warm 최대 34.048237ms 및 Lite 전체 MAP 20,199LE/16,508조합 논리이나 CPI1 및 일부 65816 envelope의 한계가 있다. MMC4/5 실제 mapper·경쟁 및 같은 경계 전체 Lite 회로 비용은 미측정이며 407의 고정 NROM MAP 절감을 그들에게 적용하지 않는다. 전체 60fps와 실기는 미입증이다.
