# 680: 실제 DMA 진행 알림과 빈 큐의 인접 map 실행

679의 E0 bit3를 실제 ARM·FPGA·65816에 연결했다. **956의 선행 DMA 기회는 늘었지만, 두 위상의 밀집 간격과 마지막 ACK를 함께 개선하는 조건은 충족하지 못했다. MMC666을 유지한다.** [결합 검증](../analysis/progress680-verification.json) · [알림 단독 대조군](../analysis/progress680-event-verification.json) · [원시 근거 보관](../analysis/progress680-archive.json)

## 구현 경계

- ARM은 678의 빈 D0 수신 예산, warm map 범위 우선, 두 bulk 슬롯·큰 plan 묶음을 유지했다. END 중 map 또는 확정된 section5 반복 패킷을 실제 drain한 뒤, 검증된 E0 진행 비트가 없으면 기존 다음 입력 callback을 **한 번만** 호출한다. 비트 대기 루프·위상별 지연·새 IRQ는 없다. E0 CRC·accepted/retired·ACK 전체 identity·STOP 검사를 통과해야 하며 진행 비트는 최종 ACK를 대신하지 않는다.
- 65816은 실제 map DMA의 반환과 명령 cursor 갱신 뒤 `$00601D←$A5`를 쓴다. DMA 전 source 종류를 스택에 보관한다. 수락 ACK, tile/raw/fill DMA에서는 발행하지 않는다. STOP 이후의 늦은 store는 FPGA가 폐기한다.
- FPGA는 기존 SNES write 동기화 경로와 152bit E0 snapshot·CRC8 순회를 재사용한다. 빈 큐·유효 ACK·검사 완료·정상 세션에서만 event를 보관하며 E1 수락, ACK staging/publish, STOP·fault·RUN 해제가 우선해 지운다. queue credit·receipt·최종 표시 상태는 수정하지 않는다.
- 알림 단독으로는 956 선행 map이 128B에 머물렀다. 늦은 VBlank에서 head/tail tile 사이의 수락된 map을 찾지 못했기 때문이다. 최종 후보는 **막힌 head tile 바로 다음 map 한 건**을 추가로 선택한다. 실제 DMA 뒤에만 부분 범위를 갱신하거나 완료된 구멍에 기존 head를 옮긴다. 새 패킷·STOP 우선과 독립 coverage는 유지한다.
- 중간 8-record 탐색은 일반 재생만 통과했다. 여덟 번째 위치의 최악 탐색 비용을 252선 후반에 보장하지 못하므로 채택하지 않았고, 고정 인접 위치 선택으로 대체했다. 탐색 횟수·위상 상수를 반복 조정하지 않았다.

## 실제 자원 비용

| 항목 | 678/기존 665 | 최종 인접 map 후보 |
|---|---:|---:|
| ARM 전체 Flash | 212,800B | **212,828B**, 한도212,992B·여유164B |
| ARM data / BSS | 10,040 / 19,544B | 동일 |
| 65816 실행 body | 5,792B | **5,948B**, 한도5,984B·여유36B |
| 65816 물리 ROM | 5,120B·여유11B | 동일 크기·**여유16B** |
| ROM 비압축 prefix | 896B | 640B, 압축 부분4,112B |
| 추가 persistent ARM/SNES RAM | — | 0B |
| DMA 수명 중 추가 SNES 스택 | — | 최대3B: source종류2B + 내부 record 이동의 DBR1B |
| 전체 보드 MAP 조합논리 | 14,355 | **14,390 (+35)** |
| 전체 보드 MAP 레지스터 | 8,386 | **8,389 (+3)** |
| 전체 보드 MAP RAM bits | 305,264 | 동일 |

MAP의 pre-fit LE는19,106→19,141이다. 이는 선택 보드의 **FIT 15,324LE·962LAB·56M9K**와 다른 수치다. 세 번째 FF는 이전에 상수였던 snapshot bit의 구현 비용이며 새 RAM·identity 저장은 없다. 순증84LE·1LAB·0M9K의 **실제 배치 예산 통과는 미확정**이다. 시간 게이트 실패 시 전체FIT/STA를 반복하지 않는679 계획에 따라 이번에는 MAP까지만 실행했다. 기존 양의 STA를 새 ROM/RTL의 STA로 옮겨 쓰지 않는다.

별도 decoder로 압축 ROM의 실행 body 완전 복원을 확인했다. 실제 첫 packet poll은7,072,032 master clocks로 기존6,588,866보다 **22.496619ms 늦다**. 두 시험 시작7,288,416/7,467,100 전에는 준비되지만 cold 비용은 증가했다. 이를 warm 성능 절감과 상쇄하거나 부팅 공짜로 계산하지 않는다.

## 두 시작 위상 판정

최종 인접 map 후보는 두 위상 각각53화면, 총106화면의 독립 출력·최종 ACK를 통과했다. 알림 단독 대조군도 별도106화면을 실행했다. 아래 Δ는 MMC666 대비이며 음수가 개선이다.

| 항목 | 위상1 | 위상2 |
|---|---:|---:|
| 956 선행 map, 678→680 | 128→512B | 128→512B |
| MMC666의 956 선행 map / tile | 640 / 16B | 512 / 0B |
| 밀집951–955 평균 Δ | −0.046784ms | −0.054662ms |
| 밀집951–955 VBlank 합계 | 15회 유지 | 15회 유지 |
| 957 마지막 ACK Δ | **+0.010430ms** | **−0.213062ms** |
| 911 SEAL / 업로드 진입 선 | 186 / 212 | 187 / 213 |
| 952 표시 간격 | 3 VBlank | 3 VBlank |
| 957 최종 추가 대기 | 0회 | 0회 |
| CPU 진행 store / host 수락 / E0 실제 관측 | 89 / 69 / 6회 | 86 / 68 / 4회 |
| SPI 총량 Δ, 678 대비 | +4B | −8B |
| SPI 총량 Δ, MMC666 대비 | −1,352B | −1,308B |

951 공개선≤246, 같은53개 plan bank의 내용·크기, 두 bulk 슬롯, 678의 첫7블록 수신 예산도 유지했다. 다른 화면의 VBlank 증가나 최종 추가 대기도 없다. 그러나 첫 위상 마지막 ACK는678과 같은67,517,582 master clocks이며 MMC666보다224 clocks 늦어 **동시 개선 실패**다. 수십 µs의 평균 변화와 같은15 VBlank를 실기 FPS 개선으로 부르지 않는다.

알림 단독은 밀집 평균−0.059132/−0.058574ms, 마지막 ACK+0.004563/−0.213994ms이며 첫 위상911 업로드가215선이라 탈락했다. 추가 map 선택을 결합하면911 마감은 회복하지만 첫 위상 마지막 ACK는 여전히 줄지 않는다.

956의 추가384B는 실제 빈 큐에서 실행된다. 첫 위상에서 패딩 ACK66,081,510 뒤 map DMA가66,085,520에 시작한다. 입력 callback 시작66,087,939보다 앞이므로 **입력 복원과의 중첩 성과가 아니다.** 새 callback37/38회 모두 D0만 수행하고 D1 입력 블록은0개다. 진행 비트는 advisory이므로 host가 수락한 횟수와 ARM이 관측한 횟수도 다르다.

956 첫 위상 표시는678보다약0.189ms 빨라졌지만 여전히MMC666보다약0.180ms 늦다. 최종 업로드에 남은 map512B와 tile이 있기 때문이다. 957은 선행map1,664B·tile16B가 기존과 같고384B map은 최종 업로드에 남는다. SEAL이 빨라져도 같은 마지막 VBlank의 표시·ACK로 모여, 956의 절감량을 마지막 ACK에서 그대로 빼면 안 된다.

비교는 같은 map·tile 이미지, map/OBJ 작업량, 큰 plan bank 내용, 실제 링크 ARM·65816을 사용했다. SysTick 코드는 실행하지만 CPI2·SPI driver 비용·반복 ROM 허용 달력은 모델이다. 진행 전달8 host clocks는 보수적 일정 할당이며 실기 지연 측정값이 아니다. NES/PSRAM 전체 RTL 동시 실행이나 실제 FPS로 해석하지 않는다.

## 안전·오류 경계

- 실제 보드 bus/endpoint RTL 두 위상에서 SPI snapshot CRC, event와 E1의 같은-edge 경합, credit wrap, ACK staging, STOP/RUN 취소, 잘못된 identity/CRC와 최종 ACK를 검사했다. ROM 내용만 다른 최종 보드에서도 해당 bus/bridge/endpoint 소스 hash는 같다.
- 실제 ARM10개 새 조건과 기존18개 handoff 조건, 빈 STATUS/실제 입력 credit9조건을 통과했다. final ACK 없이 retire·재시작할 수 없음을 유지했다.
- 최종 65816에서14개 인접 map 경합을 통과했다. 1,344B 중1,152B 부분 전송·64B 전체 완료 뒤 **남은 명령의 주소/길이 multiset**과 실제 VRAM을 비교했다. 새 패킷·STOP 선착/전송 중 도착, 부분 전송 뒤 cold 전체 복원, 독립 누락 검사를 포함한다.
- 별도4개 검사/최종 표시 STOP 취소와 이전 화면 보존을 통과했다. 252선 h1104의 실제1,152B DMA는259선 h1084에 끝났다. beam latch가252선 h1150인 늦은 경우에도 마지막 write는261선 h788로 VBlank 안이었다. STOP·새 패킷이 먼저 오면 DMA0B다. 시험용 caller 대기 후 원래 프로그램 전체 바이트를 확인하고 실제 beam·DMA를 실행했다.
- 전체 ARM의 base/menu 복구5조건 및 기존 marker4조건을 확인했다. 실제 SD 설치·물리 메뉴 복귀 재시험은 하지 않았으며 새 전달본은 없다.

## 시험 연결 오류의 처리

첫 `joint1/2`는 실제 CPU의 `$601D` write를 기록했지만, 파일 RPC를 대체한 named-pipe 어댑터가 progress 배열을 누락했다. ARM에 비트가 도착하지 않은 **유효하지 않은 통합 대조군**으로 분리했다. 이후 pipe의 여덟 번째 필드와 strict reply 검사를 함께 고쳤고, 실제 CPU write→host event→CRC가 있는 E0 응답을 연결해 새 폴더에서 재실행했다. 초기 숫자를 통합 성공으로 계산하지 않는다.

`scan1`은 기존 head/tail 전용 관측기의 단언에서 중단됐다. 관측기를 유일한 live map의 소유권·수락 바이트 검사로 확장한 뒤 원본 출력과 다시 비교했다. 중간 실패·잘못된 RPC 연결·미선택8-record 후보를 원시 근거와 함께 보존했다.

## 다음 순서와 중단 기준

이번 결과에서 **진행 비트 연결 성공, 678 대비 선행 DMA 회복, MMC666 대비 종단 개선**은 서로 다른 판정이다. 첫 두 가지가 세 번째를 보장하지 않았다. 관측 기능만 실기 제품에 넣지 않는다.

1. 선택본은MMC666, 후속 비교 재료는678 수신 수정과680 실제 이벤트/고정 인접 map으로 고정한다. 이번 코드를 곧바로 새 시험판으로 전달하지 않는다.
2. 956에서 추가 map DMA 뒤 새 tile이 들어오는 시각과 남은512B, 957의 최종 업로드에 남는384B map을 실제 ARM 준비·credit·큐 우선권·ROM 구간으로 나눈다. 956을 앞당겨도957의 같은 VBlank에 흡수되는 부분을 분리한다. MMC666이 이미 수행한956 map640B+tile16B를 새 절감으로 계산하지 않는다.
3. 확정된 후속 생산 작업을 재배치해 **911 마감과 마지막 ACK를 함께** 줄일 수 있는 범위·순비용을 먼저 정한다. 빈 D0 반복·고정 대기·map 청크/위상 상수·더 긴 scan 탐색은 보류한다. 추가 상태나 진행 조회는 Flash164B·body36B·기존 전체 회로 여유 안에서 원래 제어의 삭제까지 설명해야 한다.
4. 같은 바이너리의 두 위상에서 모두 통과한 후보에만 전체 Lite FIT/STA를 진행한다. 그 뒤에만 새 설치본/로그 이름으로5–40초·40–55초 실기 비교를 준비한다.

재현 도구는 [생성기](../tools/prepare_nes_progress680.py), [고정 인접 선택](../tools/nes_progress680_scan.py), [연속 일정](../tools/test_nes_progress680.py), [분석기](../tools/analyze_nes_progress680.py)다. 실제 입력·바이너리·raw trace·합성 report는 private archive manifest와 hash로 연결한다. 라이선스/서버 wrapper 로그와 사용자 ROM은 Git에 넣지 않는다.
