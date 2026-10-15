# NES189 출력기에서 카트리지 읽기창까지의 연결 후보

2026-10-16. PR117 `codex/nes-bulk-aperture-188`에 이어서 구현한다. [188 읽기창](nes-bulk188-contract.ko.md)의 source/CDC 미연결 부분을 보완한다. **배포186 유지, 새 실기 ZIP 없음.** [검증 JSON](../analysis/source189-verification.json).

## 작업 의미

배포184/186의 실제 `nes_native_export181`·`nes_native_fill165` 출력에 변경 없는 `nes_native_mailbox165`를 연결하고, 새 `nes_source_bulk189`가 host 도메인에서 두 읽기 버퍼에 기록한다. MCU가 SPI로 버퍼를 다시 채우지 않고 source가 직접 공급하는 경계다. 역방향 PREPARED 응답도 기존 mailbox로 NES 도메인에 전달한다.

이번 연결의 내용물은 **1813 compact/CHR 레코드이며 SNES용 타일·map·OAM·HDMA section이 아니다.** 아직 게임 수집기부터 실제 SNES CPU까지 연결한 것이 아니다. SNES 표시 변환을 어디서 얼마의 자원으로 수행할지 결정하기 전에, 이 레코드 디코더를 그대로 SNES에 옮기는 것을 다음 완료 조건으로 삼지 않는다. 왕복 제거·실기 속도 개선·60fps 달성은 미완료다.

## 데이터와 소유권

- source 클록에서 96bit 레코드를 mailbox가 인수한다. host 도메인에서는 기존 SPI payload와 같은 순서로 kind/index 2B, generation 2B, kind별 payload 1..8B를 직렬화한다. 레코드가 묶음 경계에서 잘리지 않는다.
- 188의 기본 `ALLOW_SHORT_SEAL=0`은 정확한 선언 길이만 공개한다. 189만 옵션을 켜 최대2048B 안의 **실제로 작성된 1..2048B**를 공개한다. 빈 seal은 허용하지 않는다. 다음 레코드가 남은 공간에 들어가지 않거나 END/ABORT/COMMIT을 기록하면 seal한다.
- 두 묶음이 모두 차면 source까지 backpressure가 전달된다. 공개된 바이트는 정확한 token의 consume 전까지 유지한다. source의 기존 유한 timeout도 유지하므로 소비자가 무한히 멈춰도 정상 프레임 완성을 보장하는 구조가 아니다.
- 묶음 consume는 **읽기 버퍼 해제**다. END를 읽었다고 source에 자동 ACK하지 않는다. 소비자의 검증 결과인 PREPARED를 역방향 mailbox로 전달하고, 기존 exporter가 세대를 확인한 뒤 COMMIT 또는 ABORT와 원본 lease 해제를 수행한다. 최종 화면 표시 ACK는 이보다 뒤의 별도 경계다.
- ABORT 앞의 부분 데이터는 소비자가 폐기해야 한다. COMMIT 이전 데이터의 화면 노출, generation/base 검증, 실제 section 변환은 아직 새 소비기에 구현하지 않았다.
- reset/STOP/active loss는 양방향 mailbox와 aperture의 공통 취소에 연결했다. session owner가 안정된 새 token seed를 제공해야 한다. `FFFFFFFF` 뒤에는 fault로 멈추며 자동 wrap하지 않는다. STOP/restart seed 발행기·실제 제어 레지스터 연결은 남아 있다.
- `busy`는 host serializer/수신 mailbox/공개 묶음의 보조 상태이며 클록 경계를 건너오는 중인 모든 작업의 완료 보증이 아니다. source lease나 최종 표시 ACK를 대신할 수 없다.

## 검증 결과와 한계

SELECT `probes/nes-source189/test02`, `regression01`, `evidence01`. test01의 최초3사례 결과도 보존한다. 변경 없는 배포 exporter/fill/mailbox/reset RTL을 사용했다. sealed query/PSRAM 응답과 raw SNES 버스 소비자는 합성 fixture다. 실제 PPU 게임 실행·65816 DMA·보드 mux·물리 CDC 타이밍 시험이 아니다.

| 사례 | 레코드 | 읽은 바이트 | 묶음 | 결과 |
|---|---:|---:|---:|---|
| patch0 | 88 | 763 | 2 | COMMIT1 |
| maxgroups/7 raw rows | 286 | 3,132 | 3 | COMMIT1 |
| raw query 중 fault | 102 | 924 | 1 | ABORT1, COMMIT0 |
| CHR512 타일, 소비 지연 | 8,232 | 49,627 | 26 | COMMIT1 |

네 사례 모두 모든 읽기 바이트를 독립 인코딩 결과와 비교했다. 정상 두 사례는 과거 actual SPI transaction의 dummy/CRC를 제외한 payload와도 정확히 일치한다. 레코드 배열도 이전181 시험과 같다. CHR512 사례는 두 슬롯이 찬 상태의 host 대기157,143클록과 source valid/ready 대기64,761클록을 실제 발생시켰다. 이 수치는 시험 부하이며 실기 대기시간/FPS가 아니다.

각 묶음에서 틀린 consume token이 데이터를 해제하지 않음을 확인했다. END 뒤 잘못된 generation13 PREPARED가 원본 lease를 해제하지 않고 올바른 generation12에서 완료되는 것도 확인했다. fault 사례는 부분 raw 자료를 COMMIT하지 않는다. 이번 새 결합의 STOP 중 모든 mailbox 위상을 전수 시험했다고 주장하지 않는다.

188 기본 동작 회귀는 변경 없는 기존 SNES bus와 함께 주소 위상0/3.5ns 각28,049바이트·196,590검사를 통과했다. 기존 full/backpressure/cancel/조기 seal/범위 밖 접근/reset/STOP/정지 클록 중 취소/ROM·control·packet 주소 공존을 포함한다. 반복 owner 검사가 많으므로 검사 수를 독립 사례 수로 해석하지 않는다.

승인된 Starter FLOAT 래퍼로 실행했으며 원시 로그를 보존했다. 기존186 배포2799파일·실기11파일·187 회고8파일·188 후보142파일의 해시가 그대로다. 새 전체 ARM, FIT, STA, ASM, 펌웨어, 실기 패키지는 없다. GBC164/세이브 SRAM을 변경하지 않는다.

## 60fps 관점에서 다음 결정

CHR512 시험은8192개의 CHR 바이트만으로도 kind6 레코드49,152B가 된다. 전체49,627B는 기능 경계 시험에는 유효하지만 효율적인 최종 표시 형식이 아니다. 직렬 SPI를 병렬 읽기로 바꾸더라도 **6B/CHR-byte 오버헤드와 SNES 표시 변환 비용을 그대로 남겨선 안 된다.** synthetic worst case를 SMB3 스크롤 실측으로 해석하지 않는다.

1. 현재 compact/CHR 의미를 유지하면서 CHR 연속 묶음 및 SNES-ready section 공급 위치를 결정한다. FPGA에서의 변환·작은 snapshot/streaming·안정된 패턴 슬롯 후보를 자원/포트/16.67ms 전체 예산으로 비교한다. 반복 레코드 디코딩을65816에 단순 이식하거나 MCU가SPI로 같은 바이트를 재공급하는 것으로 왕복 제거를 선언하지 않는다.
2. 실제 소비기가 최종 형식을 WRAM으로 bulk 읽고 bank/section 검증·최종 표시 ACK·음성/입력 서비스·STOP을 처리하게 한다. descriptor/control 주소와 board mux도 이때 확정한다. 현재 후보 창 `$40:0800..0fff`는 배포 연결 전이다.
3. 같은 generation의 첫 레벨 연속 스크롤 source와 변환 결과를 확보한다. 사용자 절차: 숫자1 타일에서 A → 레벨 상태 확인 → **RIGHT+B 유지, A press/release 반복**. 이번에는 이 조작/새 스크롤 캡처를 실행하지 않았다.
4. 실제 자원과 처리량이 성립한 후보만 FIT/IO/짝패키지로 연결해 최소 실기 확인한다. 일반 FIFO 시험 확대·무변경 긴 cold boot·186/044 반복을 먼저 하지 않는다.

RAM payload는 기존188의4096B를 재사용하며 이번에 두 번째 payload RAM을 더하지 않는다. serializer와 양방향 mailbox의 제어/FF 비용은 미합성이다. 42+4=46M9K는 단순 산정이며 잔여24LAB 안에 들어간다는 보장이 아니다. CHR-RAM 내용 세대, mapper bank·fetch 시점 mapping, MMC4/5/state/mute/frameskip 여유를 최종 형식과 함께 고려한다. 목표 순서는 **실기 약60fps·사운드 → 장기 플레이/오류·리셋 로그 → 입력 품질**이다.
