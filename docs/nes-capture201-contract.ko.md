# NES201 캡처와 표시 원본의 수명 분리

PR117의 후보 구현이다. 배포186, GBC164, 세이브 SRAM은 변경하지 않는다. 실제 보드에서 실행하는 새 펌웨어나 60fps 달성 결과는 아니다.

## 작업 의미

직접 타일 읽기 경로는 MCU가 계획을 만든 뒤에도 FPGA의 원본 CHR-ROM을 읽는다. 기존 exporter의 COMMIT은 MCU가 geometry/raw 자료를 준비했다는 경계이며, 최종 화면 표시 완료는 아니다. 그렇다고 표시가 끝날 때까지 수집기 전체를 붙잡으면 다음 캡처를 직렬화한다.

최종 구조는 **MCU에 내보낸 geometry와 불변 ROM의 표시 세대**를 유지하면서, 기존 FPGA 수집기에 **다음 프레임 한 개**를 모은다. 다음 프레임의 내보내기는 이전 표시의 최종 ACK와 transport retire가 끝난 뒤 허용한다. 별도 프레임 RAM은 추가하지 않았다. 이 구조는 캡처와 전송을 겹칠 기반이지만, 실제 성능 측정은 아직 없다.

중간 `test09/faults01`은 표시까지 전체 수집기를 보존하는 직렬 구조로 통과했다. 60fps 목표에 불필요한 대기를 추가하므로 **채택하지 않았다**. 최종 선택은 `test12/faults03`이다.

## 소유권과 배선

- `nes_native_frame201`은181 수집기에 정확한 시작 edge인 `capture_begin`만 노출한다. PPU 7행/257dot의 기존 시작 조건과 수집 알고리즘을 바꾸지 않는다.
- `nes_capture_lease201`은 캡처 시작에 `live_epoch`와 다음 generation을 저장한다. 성공한 exporter release에서, 이미 MCU로 복사한 geometry의 generation/epoch를 표시 원본 lease로 옮긴다. 이때 기존처럼 수집기를 해제한다.
- `nes_native_capture201`은 실제 수집기와 위 소유권을 결합한다. exporter의 `release_frame`은 이 래퍼 입력으로, 래퍼의 `effective_release`는 수집기와 기존 fill/history의 공통 해제로 사용한다. exporter의 enable에는 `export_permitted`를 연결한다.
- 표시 lease가 남아 있으면 `export_permitted=0`이다. 수집기는 다음 프레임을 끝까지 모아 보관할 수 있으나, 다음 geometry가 현재 MCU 자료를 덮어쓰는 일은 금지된다. exporter의 기존 DRAIN/IDLE을 그대로 사용한다.
- `lease_valid/captured_generation/captured_epoch`는 **내보낸 프레임**의 identity다. 새 수집기의 `owned/generation`과 다를 수 있다.192 원본 읽기와201 plan decoder에는 이 표시 lease를 연결해야 한다. 현재 수집기의 generation으로 교체하면 안 된다.
- `nes_plan_batch201`은200의 기존 1bit 재무장 mailbox를 재사용한다. NES 쪽에서 `retire_permitted`와 closed/WAIT/no queued plan/lease generation을 확인한 edge에 `retire_commit`을 낸다. 해당 edge에 이전 표시 lease를 해제하고, 기존 mailbox ACK가 host로 돌아간 뒤200 SPI가 credit을 다시 연다. 새 mailbox는 없다.
- 정상 retire는 **다음 캡처를 해제하지 않는다**. 이미 보관 중이거나 진행 중인 다음 프레임은 계속 유효하다. `reader_drained=0`이면 retire를 보류한다. 기존 C200 guard/poll 한도 이후 common STOP으로 취소해야 하며, 무한 대기 승인으로 사용하지 않는다.
- EA/E8v4와 C200의 최종 sink SEAL ACK 검사는 그대로다. SPI가 실제 PPU 표시를 독립적으로 판정하는 것은 아니다. C가 최종 ACK를 확인한 뒤 EA를 발행해야 한다.

불변 ROM만 허용한다. capture/표시 lease 중 source ready 상실, write, ROM 아닌 source, epoch 변경은 lease를 즉시 무효화하고 fault를 유지한다. capture/lease의 세대 불일치, 표시 중 새 exporter release, 잘못된 retire도 실패한다. invalid geometry/export error는 기존처럼 버리며 다음 정상 캡처를 받을 수 있다. reset/STOP은 모든 관련 endpoint에 공통 적용한다. 프레임별 core/reader/token reset은 없다.

99개의 선언된 소유권 상태 bit(두 epoch32, 두 generation16, flag3)가 있다. 실제 LE/LAB 수는 합성하지 않았으며 절감/수용을 보장하지 않는다. 저장 SRAM, 새 frame RAM은 사용하지 않는다. 전체 FIT/IO 여유 검증은 남았다.

## 검증과 한계

`test12`: 선택된184 board의 실제 collector/fill/export 인스턴스와 query mux를 추출하고201 wrapper/enable/release 배선을 적용했다. 실제 SPI2.625MHz→batch201→tile191→bulk193을 결합했다. 출력은 모델 SNES bus에서 읽고 consume한다.

- 성공한3개 export, 같은 실행 중 invalid geometry1개 폐기 후 복구, source epoch 변경1개 terminal 처리. 중간 core/session reset 없이 진행했다.
- 첫 프레임의 packed raw512색을 실제 exporter에서 비교했다. 그 lease가 유지되는 동안 다음224행 캡처를 완료했고, 다음 geometry33개를 읽어 확인했다. 이전 표시 generation은 바뀌지 않았고 두 번째 export는 retire 이전에 나오지 않았다.
- 각 표시 세대의 zero tile+END를 실제 codec/decoder/tile generator/aperture에 통과시켰다. 16B×3이0이고 token1000→1001→1002, descriptor의 generation은 현재 수집기가 아닌 이전 표시 lease와 일치한다.
- reader drain을 보류하자 E8의retiring 상태가 유지되고 credit이 열리지 않았다. drain 뒤 retire가 완료됐고, 미리 수집한 다음 프레임이 사라지지 않고 내보내졌다. 총558개 assertion 검사 통과.

`faults03`:23개 source lifetime/세대 wrap/중첩 수집/잘못된 retire/중복·조기 export/source mutation/STOP 검사 통과.

PPU 입력, PSRAM 응답, PREPARED와 최종 표시 결정은 fixture다. CPU 게임 실행이나 C+RTL+65816 전체 동시 실행이 아니다. 특히 이 결합 시험의 직접 타일 경로는 **zero tile**이며 실제 geometry에서 만든 BG/OBJ 계획의 연결은 아직 없다. 기존200의 비영 타일/READ16 검증과195의 C+65816 검증은 변경 없이 재사용할 뿐, 새 통합 통과로 세지 않는다. 기존 exporter의 CHR fill도 아직 유지되어 중복 읽기/전송 제거를 주장하지 않는다.

실패 기록: test01/06 선언 순서, test02–05 하네스의 fault 조합 되먹임과 불충분한 X 검사, test07 payload 없는 END, test08 invalid capture 즉시 해제를 허용하지 않은 하네스, test10–11 선택된184의 packed raw 형식을 이전181 형식으로 읽은 하네스. test09/faults01은 직렬 중간안. faults02는 입력을 내린 직후 delta settle 전에 확인한 하네스 오류다. 모든 실행 기록과 당시 source를 보존한다. prepare01의 encoding 이름 오류와 sandbox FLOAT 시작 실패도 실기/생산 RTL 실패와 구분한다.

## 다음 작업

1. 실제 loader/ROM 변경의 content epoch와 CHR-ROM ready/write를 연결한다. immutable image의 epoch 재사용·wrap을 금지하고 CHR-RAM은 snapshot 없이 허용하지 않는다.
2. board의 SPI/descriptor mux 및192 source에 위 표시 lease를 연결한다. exporter geometry/raw를 복사한 뒤 old receiver와 병행해 원본 CHR payload를 중복으로 채우지 않도록, **실제191 planner + C200 begin/emit/finish +195 seal/최종ACK/retire**를 production RUN에 결합한다. 성공 COMMIT까지 보존하는 MCU 자료를 다음 capture export로 덮지 않는다. enable만 연결하고 모든 기능이 끝났다고 판단하지 않는다.
3. 최소 실제 BG/OBJ joint 실행, 전체 ARM/RUN/IRQ 메모리·스택, FIT/IO를 확인하고 짝패키지로 SMB3 첫 레벨 연속스크롤을 측정한다. 새 codec/독립 FIFO 검사만 반복하지 않는다.

collected_runs는 비어 있다.199의17.944ms 합성값도16.67ms보다 길다. 이번 중첩은 캡처 대기를 줄일 구조적 여지를 만들지만 source read/plan/transfer/VRAM 전체가60fps 예산에 들어왔다는 뜻이 아니다. 숫자1+A→첫레벨확인→RIGHT+B 유지/A press-release 반복에서 동일 generation의 전체 지연·고유 표시간격을 측정한다. 오프닝/정지/ACK합계로 대체하지 않는다. persistent delta/base/bank/slot/CHR-RAM/메모리 예산도 남아 있다.

AV약60fps→장기 플레이/오류·reset 로그→입력 유지 품질 순서, MMC4/5·state/mute/frameskip 요구를 유지한다.
