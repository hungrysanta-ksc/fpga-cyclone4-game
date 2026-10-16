# NES193 생성 타일의 직접 카트리지 전송

PR117 OPEN 같은 branch. 배포186/GBC164/세이브 SRAM 유지. 새 실기판/FIT/전체 ARM 또는60fps 승인이 아니다.

## 사용자 확정 성능 기준

**실제 부하 감소는 첫 레벨의 연속 스크롤 구간에서 판정한다.** 오프닝·정지 화면·동일 타일 반복의 감소율로 대체하지 않는다. 숫자1 타일+A로 레벨 진입을 확인하고 RIGHT+B를 유지하며 A를 반복 press/release한다. 이번에 이 실제 게임 구간을 실행하거나 측정하지 않았다.

같은 실행 안에서 source/변환/전송/표시 자료를 generation으로 연결한다. 이전판과 후보는 비교 가능한 게임 상태·입력·스크롤 거리에서 비교하고, 초기 cold load/warm scroll/정지/장면 전환/raw 행을 구분한다. 원본 읽기·cache miss/hit·새 타일·전송 bytes와 실제 표시 간격을 함께 본다. 전체60초 ACK 수를 FPS로 바꾸지 않는다. 장면·오류·STOP 증거를 제외한 per-frame SD 쓰기로 시험 부하를 왜곡하지 않는다.

계획과 미측정 상태: `analysis/scroll193-measurement-plan.json`. ROM 파일 자체는 저장소나 증거에 복사하지 않았으며 사용자가 지정한 로컬 ROM의 SHA256만 확인했다. 수집된 run 목록은 현재 비어 있다.

## 작업 의미와 구현

192가 만든 SNES-planar BG16B/OBJ32B를 MCU에 보내 다시 공급하는 대신, source NES clock→작은 불변 dual-clock RAM→host clock→188 카트리지 읽기창으로 보낸다. **타일 payload의 이 경로에는 MCU/SPI가 없다.** 하지만 geometry/계획 생성·입력 codec/CDC·raw/palette/OAM/HDMA·실제 SNES 소비기는 아직 전체 경로에 통합하지 않았다.

새 `nes_tile_bulk193.sv`는32B 타일 RAM에 한 타일을 완성한 뒤34bit metadata만 기존 mailbox로 보낸다. metadata는 END/kind/generation/slot/length다. host가 전체 타일을 읽기창에 복사하고 ACK가 source에 돌아올 때까지 RAM을 덮어쓰지 않는다. RAM payload에는 reset을 넣지 않는다. 동기 host read 다음 edge에 byte를 내보낸다. 초기 타일 전체290bit mailbox 방식은 비교용 보존만 하고 채택하지 않았다.

같은 generation·kind·연속 slot은 최대2048B까지 묶는다. BG slot0의 명시적 zero tile도 BG section으로 취급한다. kind 변경/slot 불연속/2KiB 초과에서 이전 묶음을 seal하고 다음 묶음을 연다. END는 마지막 부분 묶음을 seal한다. 타일마다 payload header를 붙이지 않으며 읽기창에는 이미 변환된 tile bytes만 있다.

각188 buffer에 generation16/kind1/first-slot10 descriptor를 대응시킨다. length/token은188 소유권과 함께 유지하며 잘못된 consume token은 descriptor나 buffer를 전환하지 않는다. descriptor는 아직 host-domain 포트이며 실제 SNES control register 주소·읽기 프로토콜은 미구현이다. 따라서 control 비용이0이라는 주장은 아니다.

END의 `end_sealed`는 **모든 tile chunk가 게시되었다는 host pulse**다. consume·완전한 frame validation·VRAM 반영·최종 displayACK와 다르다. 앞으로 controller가 이를 보관하고 다른 section 및 최종 ACK와 합쳐야 한다. tile/END generation 혼합은 오류로 취소한다. 부분 타일의 index/kind/length/slot/generation 일관성을 검사한다.

STOP/reset/비활성/source fault는 mailbox와 두 chunk 소유권을 함께 취소한다. 내부 protocol 오류는 STOP/reset까지 유지하고 raw output을 차단한다. source fault도 coherent reset 경로에 포함했다. host clock이 멈춰도 raw 출력은 즉시 차단된다. 재시작에는 fresh token seed가 필요하며 FFFFFFFF 발행과 wrap을 거부한다. 공통 reset만 지원하며 endpoint 독립 reset은 허용하지 않는다. upstream/전체 controller가 유한 deadline·오류→STOP을 책임져야 하고 새 모듈 자체에 무한 대기를 해결하는 별도 runtime은 없다.

## 검증

SELECT `test04/faults02/evidence01`. `test03/faults01`은 큰 tile mailbox 초기안의 통과 결과이고 최종 선택은 아니다. test01은 시험벤치 include 선언 순서 오류, test02는 소비 완료 계수 타이밍과 이전 시험의 불필요한 stall 필수 조건 때문에 실패했다. 실패/중간 기록을 그대로 보존했다.

- 변경 없는192/191/실제 배포 arbiter·READ16과 최종193·188을 연결했다. 원본은70ns PSRAM pin fixture, 계획과 기대 byte는191의 변경 없는 실제186 C 변환기에서 가져왔다.
- 8개 합성 장면97계획/1840B가 raw 카트리지 read pin에서 일치했다. BG/OBJ kind, 시작 slot, generation, length, token도 비교했다. 장면별1~2묶음이다.
- 512회 같은 원본을 연속 출력 slot에 배치한8192B pressure 시험은4개의2048B 묶음으로 정확히 전달됐다. 두 buffer를 찬 채로 유지하여 source까지 backpressure가 전파되고 이후 동일 bytes로 재개함을 검사했다. 이것은 scrolling 성능 시험이 아니다.
- 모든9개 결합 사례에서 잘못된 token consume를 거부하고 mapped 주소 이외에서 비구동을 확인했다.32 host clocks/byte의 raw bus fixture이며 실제65816 DMA 실행은 아니다.
- 8개 취소/오류 시험: 잘못된 첫 index, 타일 중 generation 변경, frame 내 generation 혼합, END generation 불일치, 부분 타일 STOP 복구, host clock 정지 중 STOP·fresh restart, source fault 취소·복구, token 소진.
- source clock21.477MHz/host84MHz/memory168MHz, 결합 시험 phase3.5ns다. 모든 CDC 상대 위상·물리 metastability·board IO/STA를 검증한 것이 아니다. RAM ownership 규약과 비교 결과만 승인한다.

## 자원·성능 한계

초기안은256bit tile staging과290bit mailbox의 held/received를 사용했다. 최종안은32B RAM과34bit metadata mailbox다. mailbox payload 레지스터 폭은580→68bit로 줄였지만, 이것을 전체 LE 절감으로 표현하지 않는다.32B RAM의 실제 M9K 추론·LAB·routing/timing은 미합성이다.

기존18642M9K+188 예상4+193 tile store 예상1=47/56은 회계 추정일 뿐 FIT 결과가 아니다.192의 cache/191 tile buffer 및 추가 제어 논리를 포함한 전체 LAB 검증도 남아 있다. 기존24LAB 여유에 단순 추가가 가능하다고 가정하지 않는다. 불필요해지는 이전 payload 경로와의 교체 범위도 합성 전 명확히 해야 한다. 저장 SRAM은 사용하지 않는다.

193 payload에는 개별 tile header가 없지만 descriptor/plan/control/raw 등 전체 비용은 아직 측정하지 않았다.192의 source2046B/frame 낙관적 읽기 한계도 사라지지 않는다. 안정된 source content/plan key 재사용·delta·capture overlap과16.67ms 전체 예산을 유지한다. 이번 증거의 성능 개선율과 실기 FPS 값은 명시적으로 미측정이다.

## 다음 작업

1. 현재 host descriptor 포트를 실제 control decoder로 연결하고, 기존 SNES client가 chunk를 WRAM/비활성 VRAM으로 읽어 section을 완성하도록 붙인다. transport consume와 최종 frame/display ACK를 분리한다. raw·palette·OAM·HDMA 및 STOP·음성·입력 서비스는 기존 의미를 유지한다.
2. production plan 입력/codec/CDC와 content epoch producer/frame-start latch를 연결한다. CHR-RAM에는 별도 snapshot/version이 필요하며 MMC4/5 호환성을 미리 승인하지 않는다. geometry metadata까지 MCU 왕복이 제거된 것은 아니다.
3. 최소 경로의 자원·포트·16.67ms 전체 예산을 확인한 후 FIT/IO·짝패키지 실기로 넘어가 **첫 레벨 연속 스크롤**을 측정한다. 그때 원본 읽기/전송량 감소와 고유 표시 간격을 함께 판정한다. 반복 타일의 cache 효과 수치를 대신 사용하지 않는다.

일반 FIFO/관측기 확대, 긴 무변경 boot/FIT,186/044 반복을 우선하지 않는다. AV 약60fps→장기플레이/오류·reset 로그→입력 유지 품질.186/GBC164/save SRAM/완료 증거와 향후 save/load·mute·frameskip 요구를 보존한다.
