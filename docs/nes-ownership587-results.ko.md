# 587: 검사 소유권과 실제 source 경계 재확정

## 판정

**586 위에 기존 실행기 삭제만 추가하는 안은 채택하지 않는다.** 검사 소유권은 아래처럼 통합할 수 있으나 전체 예산을 통과할 근거가 없다. MMC577과 R3 미선정을 유지한다. 이번은 586에서 정한 결정 단계이며 새 펌웨어·FPGA·FIT·실기 ZIP을 만들지 않았다.

중요한 수정은 source 입력 버퍼다. 선택 보드 MMC577은 **256B 단일 sealed block +96bit record mailbox**다. 584/586의 **입력 4packet ring은 시험 모델**이다. ARM 기능 검증은 그 범위에서 유지하지만 모델의 생산 여유·buffer credit·일정을 실제 보드 구조로 승계하지 않는다. 출력 queue와 입력 source를 혼동하지 않는다.

근거: [검증 JSON](../analysis/ownership587-verification.json), [재현 도구](../tools/check_nes_ownership587.py), [고정 manifest](../analysis/whole580-manifest.json). 선택 `check03`; 최초 `check01`도 통과했고 `check02`에서 END 경계 8조건, `check03`에서 유효한 base의 오류 후 무효화를 확인했다.

## 실제 연결과 CRC 소유자

manifest의 6개 파일 해시와 다음 연결을 대조했다.

`board.qsf → fxpak_nes_screen137_top → nes_live_joint → nes_native_export203 → nes_native_mailbox165(WIDTH96) → nes_native_spi165`

export는 NES clock에서 query/압축 record를 생산한다. mailbox는 한 record를 유지하며 host의 `record_ready`는 reset·sealed·encoding 상태와 used≤244를 검사한다. host SPI의 `buffer[0:255]`가 sealed인 동안 다음 packet을 계속 쌓는 ring이 아니다. D2 수락 뒤 used/CRC를 초기화하고 token을 증가시킨다. 별도 17bit prepared mailbox도 존재한다. 이번 증거는 고정 소스의 정적 연결 확인이며 새 elaboration/RTL 실행 결과가 아니다.

기존 `block_crc`는 host가 `pack_byte`를 저장할 때 누적하는 **압축 packet CRC**다. 새 section ABI의 expanded canonical CRC와 입력이 다르다. 다음 역할을 분리한다.

| 검사 | 생산/소비 소유자 | 유지 조건 |
|---|---|---|
| wire/body 무결성 | host sealed block CRC → ARM 수신 | body·token·길이와 동일한 sealed identity에 결속 |
| canonical expected | NES의 권위 있는 query 값 → ARM expanded 값 | 압축·inherit 여부와 무관하게 값마다 정확히 한 번, META/END 경계 고정 |
| geometry 의미·필요 tile | ARM 독립 값 검사 | source가 보낸 의미 판정을 그대로 신뢰하지 않음 |
| 실제 표시 완료 | 기존 소비·receipt·최종 ACK 경로 | 입력 COMMIT과 별도 identity, VBlank·EA 순서 유지 |

source는 run의 첫 비일치 값 또는 256개 경계에서 query index를 전진시키지 않고 flush 후 다시 읽는다. 합성 예시 `[7,7,9]`의 응답은4개, 실제 값은3개다. 같은 값257개도 응답258개다. 따라서 CRC는 `response`마다가 아니라 **정상 값 수락과 query_index 전진 사건**에 누적한다. 이 두 참조 반례는 RTL의 map-repeat 부분에서 도출한 것이며 새 RTL 시뮬레이션은 아니다.

CRC 직렬화를 넣으면 다음 query/flush를 언제 허용할지, 취소 중 pending 값을 어떻게 폐기할지 정해야 한다. source CRC accumulator·byte cursor·port·CDC·LE·cycle 비용은 아직 측정되지 않았다. host CRC를 공짜로 재사용하거나 모델 fixture의 CRC 생산을 실제 기능으로 세지 않는다.

## 삭제할 표현과 유지할 검사

| 현재 조건 | 직접 section 실행기의 소유자 | 실제 삭제 가능한 부분 / 남길 부분 |
|---|---|---|
| BEGIN magic·version·예약 비트·geometry count | typed BEGIN 수락 | 구형 64bit BEGIN 재구성/재해석 삭제. map 33단위·row224·palette32/64·OBJ/exception 한도 유지 |
| epoch·serial·generation·base·token | BEGIN 및 sealed packet 수락 | 값마다 generation 비교는 수락된 immutable 문맥에서만 생략. stale/duplicate/reorder 거절 유지 |
| kind 순서·index·count·raw phase | block 수락 + 단일 cursor | 블록 전체 범위/길이 검사를 통과한 뒤 per-value 중복 index/phase 제거. block이 경계를 넘거나 중간 실패하면 문맥 폐기 |
| map/row/OBJ/exception/raster/palette bit·의미 범위 | 값 실행기 | map15bit, row group, OBJ49bit, exception 좌표<7392, raster raw slot/epoch, palette6bit 전부 유지 |
| required-tag union·512개 한도 | 값 실행기 + META_END | BG/OBJ bit union 및 tag 열거 유지. bitmap을 raw scratch로 바꾸기 전에 열거 완료 |
| raster patch 순서·개수 | META_END | slot0부터 연속·patch_count 일치 유지. section 범위 검사만으로 대체 불가 |
| geometry 완료·records/bytes·lane·raw 완료 | META_END/END | 모든 section 완료/잔여 상태를 직접 검사. old control record 호출만 삭제 |
| expanded CRC/length | 값 실행기 + META_END/END | literal/repeat/inherit 모두 동일 canonical 순서로 검사. RAM 손상 검출 생략 금지 |
| PREPARE→COMMIT | runtime의 소유권 확인 + typed COMMIT | PREPARED·generation·무payload 확인 뒤에만 COMMITTED. 입력 base 공개와 표시 bank 이력 공개 구분 |
| STOP·오류·부분 전송·늦은 완료 | runtime/source 공통 취소 | tentative/base/history 무효화와 cold 복구. 구형 ABORT record 제거가 취소 삭제를 뜻하지 않음 |
| 최종 ACK·EA·VBlank·메뉴 복귀 | 기존 출력/65816/복구 경계 | 새 입력 파서가 완료를 대신 선언하지 않음. 독립 소비 검사 유지 |

검사를 한 번으로 줄이려면 공개 packet API를 통해 들어오는 모든 caller도 동일 수락 경계를 거쳐야 한다. 부분 decode 실패 뒤 cursor·CRC가 갱신됐더라도 표시나 base 재사용으로 공개되지 않아야 한다. 이 대응표는 구현 계약이며 새 실행기가 이미 구현됐다는 뜻이 아니다.

## 제한 검증

586 ARM02의 실제 linked ELF에서 기존 `logical_record`를 실행하고 독립 Python 값 계약과 비교했다.

- 합성 값 **455개**: 6종 bit 경계·one-hot·좌표/slot 경계에서 수락/거절 일치. 수락 값 저장, 2048B required-tag bitmap, record 증가를 대조했다.
- **4개 수락 경계 반례**: 값 자체는 유효해도 generation/index/phase/state가 다르면 거절. 값 실행기로만 교체하면 놓치는 조건이다.
- **22개 control 조건**: META_END 완료·raw slot·tag count, END geometry/raw/records/bytes/lane/missing, COMMIT 상태/세대 검사.
- **2개 query CRC 참조 반례**, 고정 FPGA **6파일 해시/연결** 확인.

raw 값·canonical CRC·row 재사용·STOP·전송 취소·최종 ACK의 기존 범위는 [586 검증](nes-combined586-results.ko.md)을 유지한다. 이번에 전체 53입력·IRQ·ROM·65816·메뉴를 다시 실행하지 않았다. arbitrary parser stream 전체 동치나 새 함수 크기·속도를 증명한 것이 아니다.

## 전체 예산과 중단 근거

| 항목 | 확인 값 / 의미 |
|---|---|
| 586 이미지 |213852B, 한도212992B보다860B 초과 |
| 기존 `logical_record` |1136B. **전부 삭제하고 대체 코드를 0B로 가정해도** 산술상276B만 남음 |
| 미구현 Flash |직접 control/값 의미검사, 출력 이력/planner/독립 손상검사. 실제 크기 미정 |
| static + native frame 뒤 RAM |4572B, caller/callee/IRQ 최대치 제외 |
| 추가 raw shadow·stale mask·scratch |2297→2300 정렬 +140+8 =2448B; shared RX는 이미 포함돼 중복 과금하지 않음 |
| 나머지 RAM |2124B, 호출/IRQ·identity·손상 검사 상태를 아직 포함하지 않은 산술 잔여 |
| 제품 FPGA 여유 |148LE/5M9K. 새 source CRC·base/history·block 생산·CDC의 순비용 미측정 |
| 새 전체 처리 시간 |미측정. 4packet 모델의 공급 일정을 단일 block 보드에 적용 불가 |

276B는 linker 재배치까지 검증한 절감량도 아니고 새 실행기 예산 승인도 아니다. 기존 의미 검사의 크기만큼 무료 공간이 생긴다는 주장은 배제한다. C 전체가 불가능하다는 증명은 아니지만, **현 adapter 구성의 국소 삭제만으로 C 전체를 선택할 수 없다는 결정**은 확정한다.

## 다음 한 단계

전체 C 확장은 보류한다. 다음은 **MMC577에서 입력 교체 범위를 줄인 설계의 비용 확인**이다. 공통 진행 응답·출력 history를 동시에 추가하지 않고 기존 D0/D1/D2/D3 및 출력 실행을 기준으로 둔 채, 586 section/row 형식의 직접 ARM 수락/값 실행과 실제 NES source/host record 생산을 함께 교체할 범위를 잡는다. 새 codec/padding 변형은 만들지 않는다.

먼저 pinned `export203 → mailbox → spi165`에서 삭제할 압축 record/주소/진행 제어와 유지할 sealed block·CRC·PREPARE를 표로 분리하고, 단일 block backpressure·query 중복 읽기·canonical CRC·취소 drain의 cycle/RAM port 예산을 계산한다. ARM도 구형 packet/logical 제어를 삭제한 **순 링크 비용**을 목표로 하되, source 생산 비용이 빠진 ARM 단독 통과를 선택 근거로 삼지 않는다. 예상 상한이 없으면 또 펌웨어를 만들지 않는다.

입력 단독은 전체60Hz 달성안으로 부르지 않는다. 수신 감소로 남길 수 있는 출력/표시 예산을 전체 표에 환원하고, 충분하지 않으면 더 넓은 역할/지원 범위 변경을 결정한다. 소스/receiver가 같은 경계를 설명한 뒤에만 한 번의 bounded prototype을 허용하며 R3·보드 FIT는 아직 승인하지 않는다. 이번에 확인한 단일 block을 고정 기준으로 하고 ring 추가는 신규 RAM·제어 비용으로 계산한다.

제품 README·MMC577 산출물·GBC/save는 변경하지 않는다. 다음 전달본도 사용자 설치 방식·고유 파일명·RESTORE 제외·5–40/40–55초 집계를 유지한다.

## 재현

`tools/check_nes_ownership587.py --arm <586 ARM02/src> --board <manifest의576 board01> --out <private check.json>`

기존 Python 환경의 Unicorn/pyelftools를 사용한다. 도구는 실제 ELF와 source hash를 기록하고 합성 값만 시험한다. private `probes/nes-ownership587/check01.json`부터 `check03.json` 및 실행 log를 보존한다. 제품 source/ROM 본문·license·바이너리는 공개하지 않는다. 다른 PC에서는 manifest에 맞는 private 산출물을 복원해야 하며 clean-clone 전체 재현이 끝났다고 주장하지 않는다.
