# MMC509 전송 조합 비교 (512)

**실기 기준은 MMC509를 유지한다.** 905~916을 같은 일정에서 실행한 결과, 입력 압축은 후반 10개 표시 간격의 합을 0.030ms 줄였다. map 압축은 149.736ms 늘렸고, 두 변경을 합치면 116.445ms 늘었다. 입력 변경의 관련 클록 setup은 −0.317ns다. 새 실기 전달본으로 선택한 조합은 없다. [측정 JSON](../analysis/transfer512-verification.json) · [MMC509 실기](nes-hardware510-results.ko.md) · [이전 바이트 예산](nes-output511-results.ko.md)

## 실제 경로

**map**은 ARM의 기존 일반 패킷 생산기에서 64·128·192B map 행 묶음의 상·하위 바이트 열을 literal/repeat로 압축한다. 기존 동일 워드 RLE가 가능한 경우 그 형식을 쓰고, 압축이 원래보다 짧을 때만 opcode 9를 보낸다. 원래 범위는 기존 헤더의 expanded 필드에 둔다. E1 CRC·큐 credit·순서 검사를 통과한 뒤 65816이 토큰과 generation을 검사하고 기존 범위·중복 coverage·dirty 목록을 확인한다. 각 run의 입력·출력 경계를 확인하면서 대상 WRAM에 직접 쓰고 STOP을 확인한다. 최종 SEAL의 독립 검사를 마쳐야 VRAM DMA·VBlank 표시·최종 ACK가 가능하다.

**입력**은 FPGA의 host-clock D1 직렬화기와 ARM의 실제 수신 파서를 함께 교체했다. 블록 앞에 버전 0x51과 16비트 generation을 한 번 쓰고 각 record에는 tag와 원래 값을 쓴다. 별도 count 대신 D0가 공개한 길이, D1 전체 CRC와 record 폭을 사용한다. FPGA는 블록 안에서 generation이 바뀌면 fault를 낸다. ARM은 실제 수신 길이·token·generation·terminal 상태를 검사하고 D2 retire를 확인한다. END·취소를 분리하고 COMMIT은 PREPARED 확인 뒤 독립 블록으로 받는다. 511의 단순 포장 예측 대신 256B 버퍼·기존 제어 표식·실제 직렬화기 봉인 시점을 적용했다. [생성 코드](../tools/nes_transfer512.py)

map을 넣은 첫 ARM 빌드는 213,200B로 배포 한도보다 208B 컸다. 종료 후 로그의 16진수 출력을 공유하고 E1/E8/E9에서 중복되던 CRC 실행 코드를 기존 수신 CRC와 공유해 배포 크기로 줄였다. CRC의 검사 위치와 비교는 유지한다. 아래 map 수치에는 이 변경의 실행 비용도 포함된다. 동일 데이터를 두 방식으로 소비한 65816 비교는 따로 수행했다.

## 시간과 전송량

| 905~916 조합 | 시작→첫 표시 | 첫째→둘째 | 이후 10간격 합 | 이후 평균 간격 | 12화면 전체 SPI | 조회 제외 SPI |
|---|---:|---:|---:|---:|---:|---:|
| MMC509 | 225.499ms | 232.962ms | 931.101ms | **93.110ms** | 141,259B | 83,735B |
| map만 | 258.785ms | 266.243ms | 1,080.837ms | **108.084ms** | 148,543B | 67,739B |
| 입력만 | 225.499ms | 232.967ms | 931.071ms | **93.107ms** | 136,705B | 77,537B |
| 둘 다 | 258.783ms | 266.245ms | 1,047.546ms | **104.755ms** | 141,609B | 61,541B |

후반은 generation 906의 최종 ACK부터 916의 최종 ACK까지다. 전체 SPI에는 조회·observer가 포함되고 조회 제외 열에서는 D0/E0/E8을 뺀다. 결합은 조회 제외 22,194B를 절감하지만 전체 전송은 원본보다 350B 많다. map만 적용했을 때 E1 전송은 41,376→25,316B로 줄고 E0 상태 조회는 38,780→62,620B로 늘었다. 결합의 E0는 61,600B다. 입력만 적용하면 D1은 38,470→32,384B로 줄었다. 전송량 차이를 독립적인 표시 시간 절감으로 더하지 않는다.

같은 새 65816 프로그램에서 동일한 map 값을 일반 DMA와 직접 복원 양쪽으로 처리하고, 최초 패킷 읽기부터 해당 ACK까지 계측했다.

| 원래 크기 | 일반 DMA | 압축 직접 복원 |
|---|---:|---:|
| 64B | 11,482 masterclocks (0.535ms) | 27,260 (1.269ms) |
| 128B | 13,184 (0.614ms) | 39,666 (1.847ms) |
| 192B | 14,928 (0.695ms) | 52,162 (2.429ms) |

이 세 패턴에서는 반복·literal 해석과 두 바이트씩 건너 쓰는 CPU 루프가 기존 DMA보다 느렸다. 이 측정과 증가한 상태 조회가 다음 VBlank에 맞추기 어려워지는 방향을 설명한다. 실기 SMB3의 모든 map 패턴에 같은 비용을 적용할 수는 없다. [65816 시험](../tools/test_nes_transfer512_guards.py)

## Flash·RAM·보드 전체 비용

| 조합 | ARM firmware / 잔여 Flash | ARM BSS / 관측 stack 여유¹ | 65816 본문 / 추가 WRAM | 전체 LE / 조합 논리 | 관련 setup / hold |
|---|---:|---:|---:|---:|---:|
| MMC509 | 212,956 / 36B | 18,576 / 2,488B | 4,311 / 0B | 15,164 / 14,172 | +0.078 / +0.139ns |
| map만 | 212,984 / 8B | 18,576 / 2,448B | 4,581 / 10B | 15,164 / 14,172 | +0.078 / +0.139ns |
| 입력만 | 212,964 / 28B | 18,576 / 2,488B | 4,311 / 0B | 15,252 / 14,196 | −0.317 / +0.142ns |
| 둘 다 | 212,992 / **0B** | 18,576 / 2,488B | 4,581 / 10B | 15,252 / 14,196 | −0.317 / +0.142ns |

¹ 실행에서 관측한 최저 SP와 작업 공간 끝의 간격이다. 전체 IRQ 최악 stack 상한은 미확정이다. 네 조합 모두 ARM data 10,040B, FPGA FF 8,394개, 메모리 264,816bits, M9K 51/56개다. map의 65816 본문 여유는 379B이며 관측 stack은 모두 11B다. 추가 WRAM은 run 경계용 10B로, 이전 직접 페이지 scratch도 재사용한다.

변경 3개는 같은 507 핀과 SDC로 Quartus Prime Lite 25.1 전체 합성을 각각 수행했다. 원본은 같은 입력의 기존 전체 결과를 사용했다. 입력 변경이 있는 보드는 LE 여유가 244개에서 156개로 줄었다. 구현·명목 SDC의 관련 경로 판정이 일치했고, 실패한 최악 경로는 NES ROM 리더의 `owner_valid → remaining[4]`다. 배치 결과의 setup 실패이므로 해당 조합은 실기 진입 대상에서 제외한다. 전체 reset/CDC/IO 승인은 별도 조건이다.

## 검증 경계와 재현

- 12개 generation의 실제 exporter record를 원본과 후보 SPI RTL에 공급했다. D1 응답과 CRC·POP·ACK·짧은 READ·잘못된 token·reset을 확인했고 후보에서는 혼합 generation도 거부했다. 옛 일정 도구는 원본 블록을 최대 길이로 채웠지만 기존 FPGA는 여유 공간과 제어 표식에서 더 일찍 봉인한다. 905는 원본 RTL 15블록, 새 RTL 14블록이다. 최종 비교에서는 각 D1 거래의 길이를 RTL 응답과 대조하고 전체 payload도 각 실행 형식의 일정 입력과 일치시키므로 이 차이가 비용에 포함된다. [SPI 시험](../tools/test_nes_transfer512_spi.py)
- 같은 입력·시작 masterclock 3,000,000·같은 ROM 위상에서 링크된 Cortex-M4의 planner·serializer·SysTick과 65816 소비기·DMA를 실행했다. 공유 SPI는 2.625MHz, CPI는 2, driver 오버헤드는 기존 실기503 평균, ROM은 부팅 때 실측한 8개 창의 반복이다. source 준비와 SPI 응답·큐·bulk 공급은 모델이다. 네 실행 모두 ROM 배정 3,280회, 일반 큐 최대 4개, bulk 뱅크 최대 2개 조건을 지켰다. 새 로컬 파이프는 요청번호·요청시각을 대조하고 미래 retire/ACK 공개를 기존처럼 차단한다. [일정 실행기](../tools/test_nes_transfer512_schedule.py)
- 각 조합에서 396개 출력 패킷의 논리 내용과 lane 내부 순서, token·바이트·generation을 검증했다. bulk와 일반 패킷의 중재 순서는 달라질 수 있으며 frame별 공유 sequence가 연속인지 따로 확인했다. 12개 RGB 화면이 원본과 바이트 일치했고, VRAM DMA 36,144B, VBlank 안의 표시와 최종 ACK 12회, EA 12회가 일치했다. ACK 시각은 비교 결과에 따라 달랐다.
- 실제 65816에서 정상 64/128/192B 복원, 중간 STOP, 잘린 literal/repeat·잔여 바이트·잘못된 section·범위·정렬 등 11조건을 통과했다. 실제 결합 ARM에서 잘못된 포맷·record·generation·token, 조기 COMMIT, STOP 뒤 token wrap 재시작, CRC 11개 길이, 로그 포맷과 credit 대기/IO 오류를 검증했다. [ARM 시험](../tools/check_nes_transfer512_arm.py)
- 결합 ELF의 base-only STOP·메뉴 cleanup 경로에서 정상 복구는 safe return 1, programmer·DONE·busy·token 실패는 모두 0이었다. 프로그래머 및 보드 응답은 모델이며 새 후보의 실물 SD 실행이나 메뉴 화면을 관측한 결과는 없다. 마지막 실기 확인은 MMC509의 12.82fps와 정상 메뉴 복귀다. [복구 시험](../tools/check_nes_transfer512_recovery.py)
- 개인 작업공간 `probes/nes-transfer512`에 build03, ARM-input-02, ARM-map-03, ARM-both-03과 실행 증거를 보존한다. Temp의 선택 일정은 original04/map04/input03/both03이다. 원본·map의 03은 옛 블록 포장의 민감도 비교이고 실기 경계 표에는 04를 쓴다. 선택 로그 271개는 같은 폴더의 selected-evidence.zip와 selected-inventory.json에 있다. ZIP SHA-256은 `049b265fb72bc2105962d9724295117669e1e5dea931d6dff6b0b1d706e490b0`이다. spi01/spilegacy01, guards01/pairs01, fit-{map,input,both}-01 및 507 원본을 사용한다. [전체 결과 검증기](../tools/analyze_nes_transfer512.py)

## 다음 작업

범용 map run을 65816에서 바이트 단위로 복원하는 경로와 입력 generation 공유 단독 경로는 보류한다. 먼저 MMC509의 대상 뱅크가 이미 가진 map 행과 실제 전송되는 행을 바이트로 대조한다. 재전송을 없앨 수 있는 양과 이를 확인하는 RAM·시간을 함께 계산하고, 가능성이 있는 범위만 기존 literal DMA를 유지한 채 동일 일정에서 검증한다. STOP 때 무효화되는 이력과 최종 ACK 뒤 확정되는 이력을 구별해야 한다.
