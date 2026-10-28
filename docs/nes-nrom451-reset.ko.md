# NROM451: sink admission 로컬 reset 후보

450에서 확인한 sink의 idle 입력 동기화·admission 레지스터 5개에 기존 host 로컬 reset을 사용하도록 격리 후보를 만들었다. 외부 버스의 즉시 취소 게이트는 유지하고 reset deassert는 host 클록에 동기화한다. 제품 RTL을 바꾸거나 후보를 설치하지 않았다.

현재 queue의 독립 시험에서 16개 위상, RUN 취소, 이전 SPI/write 완료 전 admission 차단, 클록 정지 중 취소와 재시작을 통과했다. 이어 447의 실행 중 NES board RTL → 실제 227 RUN C → 실제 FPGA queue/tile → 65816 표시·최종 ACK → EA retire → 실제 run136 STOP을 후보 보드에서 재실행해 33개 패킷 ACK와 46,592개 화면 픽셀이 일치했다. loader/PSRAM은 시드이며 ARM 및 물리 시간은 모델이다. Questa 공동 시험 0 errors·기존 84 warnings. 기존 181 전체 수명주기 시험은 구버전 queue 내부 `sealed` 참조로 컴파일되지 않았고, 이를 현재 `used`로 바꾸면 후보와 기준 모두 오래된 status CRC 가정에서 동일 실패했다. 실패 기록을 유지하며 그 시험은 PASS로 계산하지 않는다.

동일 EP4CE15F17C8·Lite 25.1·seed 1의 전체 보드 FIT는 기준 14,751 LE/13,607 comb에서 후보 15,041 LE/13,613 comb로 증가했다. FF 8,029와 RAM 185,824bit는 같다. QSF에 나열된 HDL·SDC 66개 중 변경한 sink 파일만 달랐으며 QSF의 Quartus 마지막 버전 메타데이터가 달랐다. 관련 경로 표본에서 목표 5개 종단의 음수 recovery가 빠져 13개에서 8개로 감소했지만 전체 raw recovery 최악은 −8.824ns에서 −9.672ns, raw setup 최악은 −6.970ns에서 −6.504ns였다. 서로 다른 경로가 최악일 수 있고 표본 추출은 전체 signoff가 아니다.

**판정: 후보 보류.** 290 LE를 더 쓰고 전체 raw recovery 및 미제약 IO가 남아 이 변경만으로 실기 관문을 통과하지 못한다. 다음에는 남은 reset 종단과 실제 assertion/해제 소유권을 함께 다루며, 회로·경로 변화와 raw 및 관련 경로를 같은 기준에서 측정한다. 재현 입력 및 결과는 `analysis/nrom451-reset.json`, 원시 자료는 `probes/nes-nrom451`에 있다.
