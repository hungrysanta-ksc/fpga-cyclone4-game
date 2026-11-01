# 544. 확정된 map의 발행 시점과 실제 VBlank

제품 기준은 MMC540이다. [543](nes-drain543-results.ko.md)의 무조건 post-map drain과 raw 행 명령 단축은 재개하지 않았다. 동일한 [5–55초 집계](../analysis/windows541-verification.json)의 ARM 대조군, 538 client04, 기존 8프레임 부트 ROM 허용표와 시작 3,000,000 / 3,178,684 master clock을 고정한다. 모델의 연속 53화면은 실제 첫 레벨 60초 플레이가 아니다. 집계 구간의 경계 검사는 별도로 수행한다.

## 기준 일정과 변경 범위

대조군 951의 입력 시작 후 첫 VBlank는 약 31.1–33.2ms다. 이때 수락된 초기 map 192B만 소비할 수 있으며 BG 전체 map은 약 35.92ms에 확정된다. 다음 VBlank 약 47.7–49.9ms에서는 map 패킷 해석에 1.25/1.40ms를 사용하고 선행 map DMA는 256/128B다. 마지막 SEAL 전 VBlank 약 64.4–66.5ms는 큐에 3–4개 패킷이 쌓여 일반 데이터 처리에 약 1.75ms를 사용한다.

957도 첫 VBlank에서 초기 map 128B만 전송한다. BG 전체 map 확정은 약 36.13ms다. 두 번째 VBlank의 map DMA는 256/384B이며 마지막 SEAL 전 VBlank는 일반 데이터 해석이 약 1.84/1.81ms를 차지한다. map 수락 ACK와 ARM이 E0에서 credit 반환을 확인하는 시각은 구분해 기록한다. ACK는 map의 실제 VRAM DMA 완료를 뜻하지 않는다.

ARM에 SNES beam 정보가 전달되는 기존 필드는 없다. 새 SPI ABI나 추정 VBlank 타이머를 추가하지 않고, BG map의 마지막 쓰기 직후 한 묶음을 조건부 발행한다. 이후 OBJ 계산/plan flush의 ROM 대기에서는 기존 `quiet_map` 공급을 재사용한다. 각 공급은 최대 3개 연속 64B 행이며 다음 조건을 유지한다.

- 기존 검사된 E0 credit을 사용하고 큐 슬롯 하나를 남긴다. unresolved bulk target이 4개 창 밖으로 밀려나기 전에는 새 발행을 하지 않는다.
- E8에서 준비된 tile이 있으면 tile을 먼저 처리한다. 새로운 고정 지연·drain 루프를 넣지 않는다.
- SNES는 원래 코드로 실제 VBlank·STOP·새 head를 검사하고 동기 DMA 완료 후에만 커서를 진행한다. 마지막 246행 검사선도 바꾸지 않는다.
- 시험 관측기가 BG 확정 시 실제 ARM map과 `resident_prepare` 시점의 map을 비교한다. 표적 장치에는 4KiB 복사나 해시 계산을 추가하지 않았다. 새 전송 identity·세대·bank ABI는 없다.

내부 C callback에 `frozen` 인자를 추가하고, planner 종료 뒤에만 활성화하던 중복 설정을 옮겼다. target RAM에 새 상태·버퍼를 추가하지 않았다. ARM05 Flash는 212,648B(+220), 여유 344B이며 BSS는 18,592B로 같다. 65816 및 FPGA는 MMC540 그대로다.

## 검증 경계

[준비기](../tools/prepare_nes_front544.py), [ARM 경계 검사](../tools/check_nes_front544.py), [공동 실행](../tools/test_nes_front544.py), [독립 재생](../tools/replay_nes_front544.py), [분석기](../tools/analyze_nes_front544.py)를 사용한다.

재현 순서는 ① 집계 대조군 `nes-hardware541/ARM02/src`에서 `--offer` 또는 `--offer --after-tile`로 소스를 생성해 479 ARM wrapper로 링크 ② 동일한 538/client04, dense519/fixture01, order520/oracle-compact01, service509-rom03으로 두 시작 시각에서 `--trace-credit --trace-rom` 공동 실행 ③ 기록한 도착 시각으로 독립 65816 재생 ④ `analyze_nes_front544.py --after-tile-arm … --decode` 비교다. 대조군의 명령 위치 재생에만 `--decode`를 켠다. 아래 [검증 수치](../analysis/front544-verification.json)에 각 실행의 firmware·trace·관측점·보드 해시를 남긴다.

ARM05는 credit wrap, 부족한 credit, bulk target 경계, 준비된 tile, CRC/identity 오류, STOP, 불확실한 E1, 닫힌/실패한 resident, resident/video 세대 불일치의 12조건을 통과했다. 두 후보의 공통 시험기로 fresh tile과 credit 한도까지 추가한 14조건도 재검증했다. 오류 뒤 재호출은 추가 SPI/최종 확정을 차단한다. 집계는 완료 [5,40)/[40,55), 초기/종료·미완료 제외·reset을 통과했다. 메뉴 준비/해제 5조건과 marker 4조건도 통과했다. 메뉴 I/O는 모델이며 새 실물 복귀 성공을 뜻하지 않는다.

ARM04에서는 잘못된 ACK identity 이후 캐시된 credit 때문에 재호출이 E8 조회에 다시 진입했다. ARM05는 window/plan fault와 sink 상태를 첫 검사로 옮겨 이를 차단했다. 반례와 수정 후 검사를 보존한다. 이 결함은 신규 후보의 경계에서 발견한 것으로 MMC540의 실기 장애로 소급하지 않는다.

## 연속 결과

ARM05의 두 위상 53화면과 독립 재생은 통과했으나 성능 조건은 실패했다. 951의 offset320/64B 수락은 입력 시작 후 약 41.00→37.11ms, 41.03→37.08ms로 앞당겨졌다. 그러나 두 번째 VBlank의 선행 map은 위상1에서 256→128B, 위상2에서 128→256B로 서로 반대로 바뀌었다. 951 최종 대기도 0→1, 1→0으로 뒤집혔다. 새 발행이 실제로 있었더라도 소비 기회가 두 위상에서 늘어난 것은 아니다.

957은 BG 확정 시 준비된 tile을 우선 처리하므로 ARM05가 추가 map을 발행하지 않았다. 두 위상 모두 최종 대기 1회가 남았다. 같은 집계 대조군 대비 마지막 ACK는 16.650/16.623ms 빨랐지만 원본 MMC540 대비로는 동일/+0.003725ms다. 밀집 평균은 99.874565→103.197222ms, 103.196123→99.866706ms로 반대 방향이다. ARM05는 승격하지 않는다.

이 원인을 분리하기 위해 ARM06은 **이번 호출에서 새 tile E1을 실제 발행한 경우에만** 그 뒤에 map 한 묶음을 허용한다. tile은 먼저 큐에 들어가며, 단순 반복 descriptor 응답이나 잔여 pending이 3 이상이면 map을 발행하지 않는다. 새 상태·시간 지연은 없고 ARM05 대비 Flash +16B, 전체 212,664B/여유 328B다. fresh tile 뒤 STOP, 다른 generation의 tile, fresh tile로 credit 한도에 도달한 경우까지 16개 경계를 통과했다. 집계·메뉴 검사도 같은 바이너리로 통과했다.

ARM06은 두 위상 모두 53화면을 끝냈고 별도 65816 재생에서 표시·ACK 시각이 정확히 일치했다. BG 확정 뒤 951은 offset320/64B, 957은 새 tile 뒤 offset1024/192B를 발행했다.

| 같은 집계 대조군 → ARM06 | 시작 위상 1 | 시작 위상 2 |
|---|---:|---:|
| 951 map 수락 (입력 시작 후) | 41.002→37.098ms | 41.035→37.084ms |
| 951 ARM이 반환 credit 확인 | 43.049→43.050ms | 43.049→43.052ms |
| 951 두 번째 VBlank의 map DMA | 256→384B | 128→256B |
| 957 map 수락 (입력 시작 후) | 43.157→38.193ms | 43.180→38.184ms |
| 957 ARM이 반환 credit 확인 | 46.207→41.708ms | 46.207→41.710ms |
| 957 두 번째 VBlank의 map DMA | 256→256B | 384→256B |
| 밀집 평균 951–955 | 99.874565→99.866445ms | 103.196123→99.871287ms |
| 밀집 VBlank 합계 | 30→30 | 31→30 |
| 53화면 마지막 ACK 차이 | −33.271916ms | −16.644851ms |

원본 MMC540과 직접 비교하면 ARM06의 밀집 평균 변화는 −0.003594/+0.001043ms이고 VBlank 합계는 30/30으로 같다. 마지막 ACK는 원본 대비 −16.621571/−0.017879ms다. **951은 두 위상 모두 선행 DMA를 128B 확보했다. 957은 수락과 credit 모두 빨라졌지만 마지막 대기 1/1회가 남았다.** 두 위상 모두 마지막 SEAL 전 VBlank에 map DMA는 없었다. 밀집 표시와 마지막 ACK를 함께 줄이는 승격 조건에 미달하여 MMC540을 유지하고 ZIP을 만들지 않았다.

ARM06은 대조군보다 SPI −2,116/−960B(E1 바이트 동일), ARM 명령 −904,990/−489,257개, SysTick −3/−2회다. 2슬롯 한도, 관측 최저 SP 0x2000f878, 첫 BG 상대 ROM 구간, 독립 검사, 952·954 최종 대기 0회가 유지됐다. 각 실행에서 ROM 읽기 5,616회·VRAM DMA 125,488B·53화면 RGB와 실제 map/tile 소비가 대조군과 같았다. 고정 53개 캡처에서 얻은 결과이며 실기의 5–40초/40–55초 FPS 실측이 아니다.

## 보존 및 비용

별도 대조군 재생에서 실제 CPU의 header 진입·data 분기·범위 검사·주소 설정·payload·수락·ACK 위치를 기록했다. 도착 시각과 CPU trace는 그대로이며 아래 시간은 **마지막 SEAL 전 VBlank 안에 들어온 부분만** 합산한 값이다. 열의 두 값은 시작 위상 1/2다.

| 세대 | 처리한 head | header 읽기·분기 | payload 처리 | head 선택·범위·주소·수락·ACK | 선행 DMA |
|---|---:|---:|---:|---:|---:|
| 951 | 6/6 | 0.698/0.550ms | 0.502/0.657ms | 0.548/0.543ms | 0/0B |
| 957 | 3/4 | 0.294/0.408ms | 1.301/1.090ms | 0.249/0.315ms | 0/0B |

957의 1,100B zero repeat는 이미 64B 단위 고정 source DMA를 사용한다. 반면 957의 66B zero repeat와 951의 동일 바이트 194B repeat는 짧은 반복 명령(op4)이라 실제 `repeat1814` CPU 루프에 들어간다. 둘을 같은 병목으로 취급하지 않는다. 다음 독립 후보는 이 두 op4 사례에만 기존 고정 source DMA를 재사용할 수 있는지 검증하는 것이다. 서로 다른 두 바이트의 반복은 기존 복원을 유지하고, 64B마다 STOP 확인·범위/중복 검사·수락 뒤 credit·마지막 표시 ACK를 유지해야 한다. SNES 본문 여유는 11B이므로 기존 분기 교체 비용도 포함한다. 아직 절감량을 성과에 넣지 않는다.

FPGA 변경이 없으므로 기존 MMC540 전체 Lite FIT 15,164LE·14,172 조합 함수·8,394FF·264,816 RAM bit·51 M9K, 관련 setup +0.078ns/hold +0.139ns를 재사용한다. 전체 setup −7.081ns/recovery −8.480ns가 남는 기존 제한 실기 기준을 변경하지 않으며 새 합성·회로 절감을 주장하지 않는다.

콜백 활성화만 한 ARM02/run1·2는 921까지 표시한 뒤 중단했다. 기준 951·957의 BG 확정→END 사이에는 E8 조회가 없어서 이 방식으로 해당 구간의 추가 map을 공급할 수 없음을 확인했기 때문이다. 부분 실행을 53화면 성공으로 집계하지 않는다. 최초 ARM01의 임시 드라이브 권한 오류, patch02의 중복 문자열 검출과 불완전 ARM03 빌드 실패, guards01의 시험기 포인터 너비 오류, ARM04/guards03의 재시도 반례와 중단한 offer1·2도 보존한다.

새 소스·ARM 빌드·원시 실행·부분 실패·독립 재생·검증 JSON은 로컬 probes/nes-front544/archive01/evidence.zip에 보존했다. 6,523개 항목을 압축 해제해 각각의 SHA256을 대조했다. ZIP SHA256: 162e78db348562c43826b007ab7e4e2844ab5a0623a981ce93ef23b10681d5ad.
