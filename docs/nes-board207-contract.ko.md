# NES207 ROM epoch reset 경계 검증

## 작업 의미

직접 타일 전송 보드에서 남아 있던 ROM 내용 번호(epoch)의 reset 해제 문제를 해결한다.206의96개 동기화 레지스터에 있던3corner288개 negative recovery 경로행을, 기존 NES 코어의 로컬 reset을 공유하여 제거했다. 데이터 전송량이나 FPS를 높인 변경은 아니며 실제 board→C→SNES 결합 검증으로 넘어가기 위한 초기화·재시작 경계 수정이다.

SELECT **source02/epoch02/mapfit02/timing02/io02/evidence01**. 기능·전체FIT·관련클록 setup/hold·96개 reset 경로·조건부IO는 통과했다. 새 ARM/ASM/ZIP, 실제 게임·60fps 측정은 없다. 배포186/GBC164/세이브 SRAM은 유지한다.

## 변경과 수명 계약

`nes_board207.py`는 고정된206 source03에서 첫 후보를 생성한다. `nes_board207_shared.py`가 선택된 두 번째 후보를 생성한다. 기존 RTL을 직접 덮어쓰지 않는다. 최종 후보는206의89개 파일 중86개가 byte 동일하며 기존 파일 변경은 board.qsf/nes_spi_boot/nes_live_joint 세 개이고 새 source_epoch207 하나를 추가한다. clock/seed/생산 SDC/loader/direct206/batch206/bulk206/mailbox206은 그대로다.

- memory clock의 serial/Gray/exhausted는 기존 diagnostic_reset을 사용한다. STOP이나 frame ACK에서 ROM 내용 번호를 바꾸지 않는다.
- epoch_meta/epoch_sync/previous96개는 `nes_live_joint.core_release`의 NES 로컬 reset 출력을 공유한다. 새 입력은 loader_boot→source_epoch207로만 전달한다. raw memory reset이96개 레지스터에 직접 해제되지 않는다.
- 공유 reset은 cold boot뿐 아니라 STOP과 RAM 초기화 중에도 샘플링 파이프라인을 초기화한다. 재시작하면 같은 Gray 번호를 다시 동기화한다. invalid에 local_reset을 포함하고 기존 release_ready/안정값 비교/admitted를 유지한다. 동기화 중의0을 유효 epoch로 먼저 공개하지 않는다.
- source_ready는 held/admitted에서만 나온다. raw invalid를 데이터 허용에 다시 AND하지 않는다. 정지 clock에서는 무효 상태를 유지한다. local_reset 생산자인 core_release는 common_reset/raw_stop/memory_ready에 의존하며 source_ready에 의존하지 않는다. memory_ready는 NES RAM의 init_done이다.
- 변경되지 않은 mailbox는2단 request 동기화 뒤 별도 capture edge로 held payload를 받고 ACK 반환 전까지 생산자가 유지한다. chunk consume, SEAL/display ACK, frame retire의 구분은 바꾸지 않는다.

## 기능 및 실제 배치 검증

epoch02는 실제207+reset124 RTL로 기존20검사와 클록 정지/실행×reset 위상16개, 총32조합을 통과했다. STOP→재시작 시 내용 번호 유지, reload·wrap·fault·정지 중 무효화도 기존 검사에 포함된다. local_reset을 admission에서 빼는 잘못된 변형은 `COLD207 stale epoch admitted`로 거부했다. RAM 초기화와 loader 상태는 fixture이며 full loader/게임 실행이나 물리 metastability 시험은 아니다.

206의 직접 SPI/READ16/consume9프레임1968B, 부분 타일22, 취소/정지clock21, loader 비교 결과는 해당 RTL의 byte 동일성을 확인해 재사용한다. 다시 실행한207 게임 결과로 세지 않는다. 전체 loader/codec 반복은 하지 않았다.

선택된 전체FIT: **15260LE/8360FF/962LAB/47M9K**.206 대비81LE/3LAB 증가, FF와M9K는 같다. 여유는148LE/1LAB/9M9K이며 mapper 확장까지 충분하다는 뜻은 아니다. 작은 reset 공유도 전체 배치를 바꿀 수 있으므로 단순 FF 개수로 배치 비용을 추정하지 않는다.

동일DB3corner 관련클록 최저 setup **+0.173ns**, 엄격한 기존 implementation 제약 **+0.041ns**, hold **+0.156ns**. 여유가 작지만 clock/seed/예외를 완화하지 않았다. 기존 loader state* 이름 미일치 경고는 남아 있다.

96개 각각에 대해 recovery/removal을 모든3corner에서 별도로 추출한 **576경로 모두 통과**했다. 최저 recovery+40.182ns/removal+1.612ns이며 전부 core_release의 stage2에서 출발한다. cross-clock 목록에서 사라졌다는 사실만으로 통과시킨 것이 아니다. core_release/release_ready의 stage1은 각각 대응 stage2만 구동한다.

all-corner crossclock4392행, 기존 새 경로 첫 단계45개의 대응 단일 fanout, 새 기타 데이터 경로0행. held 최대6.552ns는 빠른 수신주기11.904ns에서2ns allowance를 뺀 기준에3.352ns 여유가 있다. Gray 최대6.723ns는 NES 주기45.454ns에서2ns allowance를 뺀 안정화 기준에36.731ns 여유가 있다. Gray는 임의의 연속 변경을 안전하다고 가정하지 않는다. load_begin이 admission을 무효화하고 마지막 변경 후 로컬 release/동기화/안정값 비교가 끝나야 사용한다. raw reset을 받는 release 체인 자체와 기존 경로는 구분해 기록하며 전체 CDC/MTBF/전기 signoff를 주장하지 않는다. 새로운 timing exception은 없다.

조건부IO: PSRAM70ns/PCB왕복4ns 가정 여유 **+3.828ns**, SNES read82.199ns<270ns, SPI reply165.227ns<190.476ns. 기존 native payload reset 검사도 통과했다. 측정용1000ns overlay는 raw 경로 노출용이며 합격 slack으로 쓰지 않는다. 생산 SDC는 그대로다.

첫 후보 source01은 별도 cold_release2FF를 추가했다. 동일 기능20+32/negative 검사 및96개 reset 경로는 통과했으나 전체 관련 setup−0.073ns/implementation−0.162ns였다. 이를 채택하지 않고 기존 NES reset 공유로 구조를 바꾼source02를 선택했다. 실패 결과도 보존한다. 두 후보는 각각 전체FIT 한 번이며 loader 미세 조정/seed 탐색/클록 완화는 하지 않았다. 이전22개 archive는 불변으로 확인한다.

## 다음 작업

다음은 최소 실제 board→C203 RUN→SNES195 결합 검증이다. 일반 BG/OBJ와 부분 취소를 포함하고 exported lease/epoch→계획 SPI→실제READ16/aperture→실제65816 DMA→최종 표시 ACK→retire→다음 frame의 소유권을 한 경로로 확인한다. fixture consume나 모의 최종 ACK를 실제 C/65816 결합으로 대체해야 하며, 반복된 독립 codec/loader 시험으로 대신하지 않는다.

그 다음 정확히 짝지은 ARM/FPGA ROM/런타임 검증을 거쳐 FIRSTLEVELSCROLL 실기판을 만든다. SMB3 숫자1+A 진입, RIGHT+B 유지/A press-release로 스크롤할 때16.67ms 목표를 측정한다. collected_runs는 아직 비어 있다.199의 합성512BG17.944ms 모델도60fps 달성을 뜻하지 않는다. 남은 throughput/delta 최적화는 그 결과에 근거하며 불변 ROM tag만으로 잘못 생략하지 않는다. MMC4/5·CHR-RAM·상태저장·뮤트·프레임스킵 예산과 AV약60fps→장기play/오류·reset로그→입력 유지 순서를 보존한다.
