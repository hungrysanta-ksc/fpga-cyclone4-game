# NROM453: 클록 감시의 메모리 준비 해제 경계

452의 최악 raw recovery 경로는 `clock_guard|ref_qualified`가 준비 신호를 통해 reader의 `memory_reset[0/1]`까지 직접 이어진다. 086에서 사용한 원칙에 따라, 기존 `memory_release`의 비동기 assertion과 메모리 클록 동기 release를 유지하고 `external_memory_ready`에서 중복 `guard_allow` 직접 항을 제거한 격리 후보를 만들었다. clock guard fault 래치·startup 대기·reader reset·실제 제품 RTL은 변경하지 않았다. 두 클록이 모두 멈추는 경우의 한계도 그대로다.

전체 보드 RTL과 모델 PLL·시드된 PSRAM/verified 상태에서 기준 NES 클록과 메모리 클록을 각각 정지했다. 기준·후보 양쪽에서 감시 fault 이후 ROM CE/OE/WE 해제, RUN 및 core 정지와 클록 복귀 뒤 자동 재무장 금지를 확인했다. 두 시험 0 errors, 기존 board 초기화/포트 경고 84개. 클록 정지 검출과 비동기 차단의 실제 전기적 지연·메타안정성은 모델 시험으로 승인할 수 없다. 첫 `stop01`은 준비 디렉터리에서 `sys/iir_filter.v`가 빠져 컴파일 실패했고 보존했다. 이 누락 사본의 FIT는 무효다.

누락 없는 452 fit02와 같은 corrected SDC·QSF·장치·Lite·seed로 후보를 재배치했다. QSF의 66개 입력 중 `nes_live_joint.sv` 하나만 다르다. 452→453은 14,741→14,779 LE, 13,607→13,628 comb, FF 8,029와 RAM 185,824bit는 동일하다. 같은 STA 질의에서 `ref_qualified→reader|memory_reset[0/1]` recovery 경로는 452의 3코너 각 2개에서 후보 0개로 바뀌었다. 단일 경로 소멸은 전체 CDC 통과가 아니다. raw recovery 최악은 −11.467→−8.468ns로 개선됐고 raw setup은 −6.568→−6.670ns다.

후보 전체 보드의 실행 중 NES core RTL → 실제 227 RUN C → FPGA queue/tile → 65816 에뮬레이터 → 최종 ACK·EA retire → 실제 run136 STOP도 통과했다. 패킷 ACK 33회, 타일 DMA 32B, VRAM 4,128B, 체크무늬 46,592픽셀과 STOP 뒤 observer 유지가 일치했다. 이 시험은 loader·PSRAM verified 시드, host C 및 RPC 실행기 간 시간 모델을 사용하며 실제 ARM·IRQ·하드웨어·60fps 증거는 아니다. Questa 0 errors, 기존 초기화/포트 경고 84개다.

**판정: 보류.** 420과 동일한 제한 관련 클록 분류에서 후보의 실제 동기 setup `loaded_bytes[8]→raw_causes[4]`가 −0.494ns다. 452 기준의 관련 setup +0.102ns와 비교해 실기 관문을 만족하지 못한다. 후보는 IO와 나머지 reset도 signoff하지 못했다. 잘못된 경로를 false path로 가리지 않으며, 452 제약 후보와 기존 배치도 실기 승인하지 않는다.

원시 자료는 `probes/nes-nrom453`에 보존한다. `analysis/nrom453-timing.json`은 동일한 420 분류 및 입력 해시다. FPGA 설정·base/menu 복구, 실기와 60fps는 미검증이다.
