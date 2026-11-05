# 610: ARM 발행 일정과 CHR 캐시 제어 교체

OBJ bulk 뒤에만 map을 겹치는 ARM 후보는 두 위상 모두 952 표시 6→5 VBlank·밀집 합계 24→23 VBlank·마지막 ACK 단축·957 최종 대기 0회를 함께 만족했다. 실제 source 경계는 171 LE 줄었다. 다만 기존 BG 캐시 적중과 보드 통합 비용을 아직 함께 검증하지 않았으므로 MMC577 실기 산출물을 유지한다. 전체 보드 FIT·STA나 실기 FPS 결과로 읽지 않는다.

## 952에서 발견한 발행 공백

609의 952에서 `end_enter`부터 END 수락까지 두 위상 모두 5.360 ms가 걸렸다. E8에 준비된 bulk descriptor가 12번 나타났고 4개의 bulk 명령을 제출했지만, 이 구간에 일반 map은 발행하지 않았다.

`poll()`은 준비된 bulk를 먼저 제출하거나 같은 token의 반복 응답을 확인한 뒤 `flags=4`를 돌려준다. 기존 `drive554()`는 `flags==0`일 때만 `quiet_map`을 호출한다. 따라서 bulk를 제출한 뒤 실제 일반 큐 credit이 남아도 확정 map을 공급하지 않았다. 입력이나 CRC 검사를 생략할 문제가 아니라, 검증된 준비 상태에서 두 출력 종류를 발행하는 순서의 문제다.

새 후보도 bulk 제출과 E9 가능 여부를 먼저 확인한다. 이후 실제 `nes_window532_room()`으로 최소 한 슬롯을 남기며 map을 발행한다. 선행 bulk 뒤 세 개 이상을 발행했다면 `complete485()`의 대응 ACK 확인을 거친다. 독립 CRC·identity·token·STOP 검사를 우회하거나 큐 크기를 늘리지 않았다. 65816의 새 패킷 우선·246번 검사선·최종 ACK·메뉴 코드는 608 대조군과 같다.

## ARM 후보와 전체 링크

| 후보 | 발행 규칙 | 전체 firmware B | Flash 여유 B | 결과 |
|---|---|---:|---:|---|
| 609 기준 | 기존 credit, bulk 뒤 map 미발행 | 212,976 | 16 | 대조군 |
| 모든 명령 직렬화, arm03 | 이전 일반 패킷 ACK 뒤 다음 발행 | 212,972 | 20 | 마지막 ACK 회귀로 제외 |
| map 뒤 직렬화, arm04 | 마지막 명령이 map이면 큐가 빌 때까지 대기 | 212,992 | 0 | 밀집 합계는 개선되나 마지막 ACK 회귀로 제외 |
| 모든 bulk 뒤 map, arm05 | 준비된 bulk 제출 뒤 남는 credit 재사용 | 212,992 | 0 | 위상 1의 957 최종 대기가 늘어 제외 |
| OBJ bulk 뒤 map, arm06 | BG 뒤 기존 순서 유지, OBJ 뒤 credit 재사용 | 212,992 | 0 | 공통 일정의 시간·957 조건 통과, 보드 채택 보류 |

arm04/05/06의 ELF는 text 202,949 B·data 10,040 B·BSS 18,592 B다. firmware 길이에는 패딩도 포함했다. 새 정적 RAM이나 수신 버퍼는 없다. 초기 map 직후 강제 drain 구현 두 건은 213,000 B로 Flash를 8 B 초과해 연속 실행에 넣지 않았다. Flash 0 B 여유는 링크 통과일 뿐 제품 확장 여유가 있다는 뜻이 아니다.

첫 두 직렬화 후보는 952의 SEAL 뒤 DMA를 줄였지만 전체 파이프라인을 늦췄다. 이 방식의 간격·상수 조절은 더 반복하지 않는다. 모든 bulk 뒤 map 후보는 밀집 표시와 마지막 ACK를 함께 줄였으나 957의 조건을 위반했다. 마지막 후보는 프레임 번호나 특정 ROM 주소 없이 이미 독립 검증한 descriptor의 BG/OBJ 종류로 구분한다.

## 두 시작 위상의 연속 표시 비교

각 행의 두 값은 위상 1 / 2이며, ACK 차이는 공통 609 일정 대비다. 모든 후보는 같은 53화면과 114,352 B DMA를 완료했다.

| 후보 | 952 표시 VBlank | 밀집 951–955 VBlank 합계 | 밀집 평균 ms | 마지막 ACK 차이 ms | 957 최종 대기 |
|---|---|---|---|---|---|
| 609 기준 | 6 / 6 | 24 / 24 | 79.840 / 79.857 | 0 / 0 | 0 / 0 |
| 모든 명령 직렬화 | 6 / 6 | 27 / 26 | 89.921 / 86.593 | +648.256 / +631.786 | 0 / 0 |
| map 뒤 직렬화 | 5 / 5 | 23 / 23 | 76.564 / 76.526 | +66.179 / +66.237 | 0 / 0 |
| 모든 bulk 뒤 map | 5 / 5 | 23 / 23 | 76.521 / 76.470 | −17.985 / −16.670 | 1 / 0 |
| **OBJ bulk 뒤 map** | **5 / 5** | **23 / 23** | **76.516 / 76.534** | **−49.917 / −16.670** | **0 / 0** |

OBJ 조건 후보의 952 실제 표시 간격은 98.422→81.804 ms / 98.438→81.798 ms다. END 수락 전 bulk 4개에 map 3개를 겹쳐 보냈고, 선행 DMA는 528→576 B, SEAL 뒤 DMA는 2,160→2,112 B였다. END 수락 자체의 소요 시간은 5.360→6.153 / 5.939 ms로 늘었지만, 그동안 확정 map을 함께 처리해 전체 일정을 앞당겼다. **952 최종 검사선은 여전히 248번이고 마지막 VBlank 대기 1회는 남는다.** 전체 표시 간격이 줄었다는 사실과 최종 대기 제거를 혼동하지 않는다.

957에서는 BG bulk 뒤 map을 끼워 넣지 않았다. 선행 DMA 640 / 656 B, SEAL 뒤 1,888 / 1,872 B, 최종 검사선 245 / 244번으로 두 위상 모두 최종 대기 0회다. 954는 5 VBlank와 최종 대기 0회를 유지했다.

첫 두 화면을 제외한 51개 표시 간격의 평균은 69.846→68.867 ms / 69.819→69.492 ms였다. 최대는 98.422→83.347 ms / 98.438→83.470 ms다. 밀집 구간만 좋아지고 전체 마지막 ACK가 늦어진 map 직렬화와 구분했다. 608 팔레트 단독 대비 마지막 ACK도 −49.696 / −49.633 ms이지만, 아래의 기존 BG 적중 한계 때문에 이것을 기존 실기 보드에 대한 확정 순이득으로 해석하지 않는다.

같은 후보의 전체 실제 SPI는 485,334 / 486,154 B, 실행 ARM 명령은 77,591,061 / 77,740,619개, 실제 SysTick 호출은 386 / 387회다. 다음 동일 뱅크 캡처까지 이전 EA 이후 최소 32.829 / 32.810 ms가 남았다. 실제 E0 점유는 최대 4, bulk는 최대 2슬롯이었다.

## 실제 source 경계의 교체

`nes_source_tile192`의 기존 `nes_chr_cache192`를 `nes_chr_cache610`으로 바꾸고, 기존 `nes_tile205`와 실제 `nes_native_arbiter165`까지 연결했다. EXTERNAL_PLAN=1과 같은 EP4CE15 대상·포트 경계를 사용했다. 캡처 공급·해제 포트를 두 대조군 모두 노출해 회로를 비교했다.

| 같은 source 경계 Lite MAP | LE | 조합 논리 | FF | RAM bit |
|---|---:|---:|---:|---:|
| 기존 한 줄 캐시 포함 source | 1,244 | 1,066 | 316 | 0 |
| 현재 캡처 조회·miss 공통 소유자 | 1,073 | 953 | 205 | 38,400 |
| 차이 | −171 | −113 | −111 | +38,400 |

한 줄 캐시의 16 B 저장·byte-valid·tag·epoch 중복 저장과 hit/miss 완료 제어를 교체했다. ROM 주소·세대·오류 검사는 새 miss 완료 경로에 남았고, source의 lease/immutable 검사와 tile의 응답 검사는 유지했다. 캡처에서 공급한 OBJ는 NES core가 물리 ROM을 읽는 동안에도 공급되며, miss만 기존 중재기를 기다린다. 새 tile 시작과 STOP drain 완료에는 여전히 물리 reader의 idle이 필요하다.

실제 source 시험에서 cached OBJ·누락 OBJ·BG·core ROM 경쟁, 출력 backpressure, STOP 즉시 출력 차단, 진행 중 miss의 drain, 잘못된 주소·세대 차단을 통과했다. 기존 609의 두 뱅크 소유권·동시 캡처·클록이 멈춘 동안 짧은 STOP 시험은 그대로 보존한다. RAM read-during-write 경고는 캡처 중인 뱅크와 조회하는 sealed 뱅크를 분리하고 같은 sample의 디렉터리 read/commit을 다른 edge에 두는 소유권 조건 안에서만 허용한다.

기준 보드 여유 148 LE에 동일 경계 차이 −171 LE를 대입한 산술 여유는 319 LE다. 새 RAM은 M9K 5개에 해당하며 기존 여유 5개를 모두 쓴다. **보드 캡처 포트·lifecycle 연결 비용, 배치와 STA는 포함하지 않았으므로 전체 FIT 통과로 판정하지 않는다.** 609의 별도 캐시 229 LE를 추가로 더하거나 기존 보드의 캐시 337 LE를 따로 빼지 않았다.

## 검증 범위와 남은 대조 조건

- 같은 실제 M4 ELF·SysTick/IRQ·SPI 발행과 Mesen의 실제 65816 수신·독립 검사·DMA·VBlank·최종 ACK를 905–957의 53화면에 연결한다. 두 시작 클록은 3,000,000 / 3,178,684다. VRAM DMA 114,352 B와 RGB 일치를 확인한다.
- ROM 허용 구간은 고정된 실제 측정 calendar를 주기적으로 재생한다. ARM CPI 2와 평균 SPI driver 비용을 포함하지만, 전체 NES/PSRAM RTL 동시 실행이나 실기 FPS 측정은 아니다. 입력·캡처 데이터는 로컬 고정 자료를 재생한다.
- 새 캐시의 OBJ 조회에는 기존 609와 같은 8 master clock을, BG miss에는 추가 dispatch 1 master clock을 부과한다. 실제 source의 `nes_clk`는 보드의 SNES master clock이다. 952의 기존 trace 지점은 dispatch 전이므로 분석기에서 1 clock을 명시적으로 보정하고 grant/response는 실제 기록과 그대로 대조한다. 기존 609 재분석 결과가 같음을 확인했다.
- 이전 한 줄 캐시의 48회 적중은 BG의 912·931·939 각 16회다. 새 OBJ 캡처는 이를 대체하지 않는다. 609 공통 일정의 이 장면들 첫 BG ROM 대기는 위상 1에서 5.659 / 4.575 / 7.369 ms, 위상 2에서 5.834 / 4.537 / 7.196 ms다. 이를 순손실로 단순 합산할 수는 없지만 무시할 크기도 아니다. 이번 공통 시간 모델은 대조군과 후보 모두 이 48회를 ROM 공급으로 계산하므로 ARM 발행 후보끼리 비교할 수 있지만, 기존 보드 대비 캐시 교체의 순시간 이득은 아직 확정할 수 없다. 다음 보드 후보에서는 이 BG 이력을 보존하거나, 이 적중을 실행하는 대조군과 비교해야 한다.
- 저장 뱅크 재사용은 이전 세대 EA 이후, EA는 해당 최종 표시 ACK 이후인지 전 거래에서 확인한다. 실제 bulk 최대 2슬롯과 E0의 sent/retired를 실제 PUSH·65816 ACK 시각에 대조한다.
- ARM guard는 bulk 먼저 제출, STOP/잘못된 ACK 차단, 최종 표시 ACK 없는 EA 거부를 검사한다. 별도 실제 prelude 시험으로 새 명령·END·tile·STOP·잘못된 E8 CRC·모호한 E1 응답을 검사한다. 메뉴 경로와 실기 산출물은 바꾸지 않았으며 새 하드웨어 메뉴 시험을 한 것은 아니다.

## 재현

1. 고정된 planner607 recent01 전체 ARM을 `prepare_nes_pace610.py`로 복제한다. 기본/`--map-only`/`--bulk-map`/`--obj-map`을 각각 분리하고 `build_nes_trial577.ps1`로 전체 링크한다. 각 결과의 firmware 해시와 raw build/size 로그를 유지한다.
2. `guard_nes_pace610.py`는 직렬화 후보, `guard_nes_offer610.py`와 `check_nes_prelude554.py --cutoff`는 bulk 후보에 사용한다. OBJ 후보의 guard에는 `--obj-only`를 추가한다.
3. frozen cdc576-board01에 `check_nes_replace610.py map --variant reference/replace`를 각각 적용한다. 실제 source 시험은 같은 생성기의 `sim --variant replace`를 기존 Starter FLOAT 래퍼로 실행한다. 마지막 선택 결과는 reference01/replace02/sim10이며 앞선 실패 시험을 덮어쓰지 않았다.
4. `test_nes_obj609.py --bg-dispatch-clocks 1`에 같은 608 client03·601 samples·ROM calendar·driver503·plans·capture를 넣고 위 두 시작 클록으로 실행한다. `budget_nes_pace610.py`가 actual ELF/client·trace·RTL·MAP·guard 해시를 묶는다. map 뒤 직렬화에는 `--map-only`, bulk 후보에는 `--bulk-map`을 사용한다.

최종 수치와 채택 여부는 [기계 판독 근거](../analysis/pace610-verification.json)에 연결한다. 실기 5–40초·40–55초 집계와는 구분하며 새 전달본을 만들지 않는다.

## 다음 한 단계

OBJ 조건 ARM과 608 팔레트 단독을 유지하고, **기존 BG 한 줄 이력의 보존을 포함한 실제 보드 캡처·해제·source 연결**을 한 경계로 검증한다. 새 경계의 추가 상한은 산술 319 LE·추가 M9K 0개이며 ARM Flash는 이미 한도여서 새 ARM 기능을 더하지 않는다. BG 적중을 실행하는 공정한 대조군으로 912·931·939와 952·957을 함께 확인하고, 이 조건을 통과한 RTL에 한 번의 전체 Lite FIT·STA를 적용한다. 독립 검사·STOP·새 패킷 우선·최종 ACK·메뉴를 유지하며, 단순 발행 간격이나 위상 상수를 다시 조절하는 실험은 보류한다.

[전체 링크·guard](../analysis/pace610-builds.json) · [직렬화 제외 근거](../analysis/pace610-serial.json) · [map 직렬화 제외 근거](../analysis/pace610-map.json) · [모든 bulk 조건 제외 근거](../analysis/pace610-bulk.json)
