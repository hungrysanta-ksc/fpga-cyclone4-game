# NES248 — ARM 계획·FPGA map 검증·SNES DMA의 일정과 회로 예산

PR128 머지 `64640645e3e37adb697d0293a509d0329e4eae4e`와 원격 master 일치를 확인하고 새 `codex/nes-typed-schedule-248`에서 검토했다. 사용자 요청은 이 분담의 실제 처리 순서와 회로 여유를 함께 평가하는 것이다. **분담은 조사 대상으로 유지하지만, 현재 일정·회로 예산으로는 60fps 구현 후보를 승인할 수 없다.** 새 RTL/65816 실행이나 FIT 결과가 아니라, 실제 C 패킷 순서·기존 계측·실제 회로 포트를 결합한 조건부 일정이다.

## 무엇을 추가로 반영했는가

247 placement05의 15.525ms는 입력 COMMITTED 이후 출력 SPI와 SNES 작업을 이상적으로 겹친 값이었다. 이번에는 같은 SMB3(J) 71프레임의 실제 패킷 순서, 기존 op7의 전후 drain, map의 마지막 패킷 도착 시각, 4개 큐 credit, manifest 앞의 FIFO head 소유권, SEAL coverage 및 최종 표시 이후 retire를 분리했다. 905/906 cold는 데이터 재구성에 포함하되 다중 chunk 일정은 제외했다. 일정 비교는 warm69(907..975)다.

서로 다른 두 가지 조건을 구분한다.

- `barrier`: typed map도 기존 op7처럼 소비 완료를 기다린 뒤 다음 데이터를 보낸다.
- `queued`: map DMA 중 OAM/raw 패킷을 큐에 넣고 ACK 확인을 뒤로 옮긴다. **새 비동기 typed 프로토콜·큐 소유권 변경이 필요한 가정**이다. 기존 4개 큐 자체를 새 기능으로 계산하지 않았다.

`exact64`는 필요한 map word만 최대64B 범위로 보낸다. `gap16_64`는 간격16B 이하를 현재 map 값으로 채워 최대64B 범위로 묶는다. ARM이 정확한 gap 값을 공급하고 manifest도 실제 확장된 수신 집합과 같아야 한다. FPGA가 모르는 gap 값을 생성하는 모델은 아니다. 후자는 기존 C 패킷의 map/manifest만 Python에서 대체한 가정이며 실행된 새 ARM sender가 아니다.

## 69프레임 일정 비교

단위 ms, `최대 / 16.667ms 초과 프레임 수`. 아래 표는 기존 최종 표시 **높은 표본**을 사용한 민감도다. 새 typed DMA의 구간당 설정 비용을 0/500/1000/1500 master clock으로 바꿨으며 실측값으로 주장하지 않는다.

| 전송·소비 방식 | 설정0 | 설정500 | 설정1000 | 설정1500 |
|---|---:|---:|---:|---:|
| exact64 + barrier | 16.746 / 1 | 17.794 / 3 | 18.841 / 7 | 20.077 / 8 |
| exact64 + queued | 16.689 / 1 | 17.199 / 3 | 18.324 / 4 | 19.581 / 7 |
| gap16 + barrier | 16.935 / 1 | 17.680 / 3 | 18.425 / 5 | 19.170 / 7 |
| gap16 + queued | 16.844 / 1 | 17.086 / 2 | 17.831 / 3 | 18.662 / 6 |

설정0은 진단용이다. 새 범위 읽기·검사·DMA 설정이 공짜라는 뜻이다. exact64/queued의 설정0 최대는 표시 표본을 낮게 잡으면16.527ms, 높게 잡으면16.689ms다. 따라서 0.022ms 초과만으로 모든 구현이 불가능하다고 판정하지 않는다. 그러나 낮은 표시 표본을 쓰더라도 설정500에서 exact64는17.038ms, gap16은16.924ms다. 여기에 아래 미계측 비용이 남는다. 기존 최종 VRAM 명령에서 관측한 `8×payload` 제외 잔여는1218..1586클록이지만 **새 WRAM staging 설정의 측정치나 하한은 아니다**.

954번 프레임은 exact64에서45구간·154B 값·456B local chunk·SPI4107B다. gap16은32구간·244B 값·468B chunk·SPI4158B다. 설정500일 때954 전체는17.199→17.086ms로0.114ms 줄지만, 구간 수만 보고 얻을 것이라 예상한 절약 대부분을 추가 전송·순서 의존성이 상쇄한다. 설정이 빠를 때는 gap16이 오히려 불리하다. 최종 VRAM map DMA 목록은 두 방식 모두 기존과 정확히 같다. 952/955의 다중 VBlank 문제를 해결한 결과가 아니다.

### 954의 예시 일정

`exact64 + queued + 설정500`, 높은 표시 표본. 시작점은 source SPI 읽기 시작이다. source 준비/ARM 계획 실행 시간은 포함하지 않은 조건부 시간축이다.

| 구간 | 시작→종료 ms | 담당·의존성 |
|---|---:|---|
| 입력 SPI 2220B | 0→6.766 | 입력 완료 전 BEGIN/출력 계획 소비 불가 |
| BEGIN·계획/초기 제어 | 6.766→7.799 | 31B+308B SPI; ARM 연산은 별도 미계측 |
| BG/OBJ bulk 3개 | 7.799→9.611 | 각43B 명령, 기존 mark+payload 비용,40B poll; 매번 drain |
| map 패킷 2개 | 9.611→10.614 | 마지막 map 도착 전 전체 chunk 게시 불가 |
| typed 명령 59B | 10.614→10.794 | descriptor/control 확장16B 포함 |
| map WRAM DMA | 10.794→11.899 | 45×500 + 154×8클록; 고정 chunk overhead 미포함 |
| OAM/raw 전송·mark | 10.794→13.066 | 앞 DMA와 일부 겹침; 4credit 대기0.511ms 포함 |
| manifest·typed ACK·SEAL | →13.991 | manifest는 앞 SNES packet head 해제 후 검사; SEAL 190B+certificate32B+envelope19B |
| SEAL coverage | 13.991→15.040 | 1.048644ms, SEAL 뒤의 필수 tail |
| 최종 표시 표본 | 15.040→17.000 | 1.959467ms, VBlank 대기 제외 |
| retire 제어67B | 17.000→17.199 | 표시 이후 비용으로 별도 계상 |

모든 SPI byte는 prior ready4 모델과 보존 비교했다. 프레임별 계획·초기 제어의 잔여 byte는 BEGIN 뒤, 첫 tile 전에 모았다. 이는 기존 bulk 장벽에 맞춘 명시적 시나리오이며 실제 ARM timestamp trace는 아니다. poll 추가 반복·inter-byte gap은 미측정이다.

## 실제 포트에서 발견한 두 제약

### 1. aperture는 순차 쓰기만 지원한다

동결된240 보드의 `nes_bulk_aperture188.sv`는 `storage[{writer,count[10:0]}] <= byte_data`로 쓴다. 새 producer가 임의 주소로 descriptor를 되돌려 쓰는 포트가 없다. 따라서247의 `[32B header][모든6B descriptor][모든 값]` 형식은 최종 구간 수·source offset을 미리 알기 위한 두 번째 순회, 추가 버퍼 또는 random-write 확장이 필요하다. 그 비용을0으로 둔 직접 연결은 폐기한다.

이번 Python 정책 모델은 **`[6B descriptor, 해당 값] 반복 + [32B trailer]`**로 바꿨다. descriptor의 source offset은 현재 write pointer+6이므로 즉시 알 수 있다. SNES는 공개된 chunk_length로 끝의 trailer를 먼저 읽고 앞에서부터 소비할 수 있다. 기존 reader는 주소 지정 읽기가 가능하다. 2KiB 안에서 descriptor·값·trailer를 모두 계상했으며 최대1992B, warm은 모두1chunk다. 새 full-map RAM이나 추가 chunk RAM을 공짜로 가정하지 않았다.

71프레임×2범위 정책을 wire 및 trailer 경로로 각각 재구성해 **284회/1,163,264B**가 일치했다. 잘못된 목적지·source·길이·개수·중복·누락·manifest·cold coverage의 Python 반례15개도 거부했다. trailer의 count 외 binding 영역은 placeholder다. 새 epoch/token/CRC 회로나 SNES decoder를 구현·검증한 결과가 아니다. trailer 선행 읽기와 범위 설정의 실제 비용은 여전히 필요하다.

### 2. SPI packet을 해제하는 주체는 현재 SNES ACK 검사기뿐이다

`nes_sink_spi165.sv`에는 수신용4×256B RAM과 하나의 동기 read port가 있다. SNES 읽기와 ACK 검사가 같은 port를 나눠 쓰며, 검사를 통과한 SNES ACK만 `retired`를 증가시킨다. FPGA map parser를 붙여도 map/manifest 패킷을 자동으로 해제하거나 앞의 SNES 소유 head를 건너뛸 수 없다.

새 경계는 다음 수명 규칙이 필요하다. 아래는 요구 계약이며 아직 RTL 증거가 아니다.

| 단계 | 담당 및 완료 조건 | 해제할 수 없는 것 |
|---|---|---|
| 입력 admission·화면 계획 | ARM: geometry/slot/row 의미·현재 뱅크·최종 DMA 계획; 기존32bit epoch/base serial 유지 | 입력 미완료를 COMMITTED로 취급하지 않음 |
| map/manifest packet parse | FPGA: 봉인된 head만 읽음; 순서·CRC·frame·범위·단조 비중복·정확한256B receipt/manifest 비교 | 이 완료는 SNES staging/표시 ACK가 아님 |
| typed chunk 게시 | FPGA: tile phase가 **소비까지 drain**된 뒤 같은 aperture 사용; immutable source와32bit token 유지 | `end_sealed`만으로 buffer 전환하지 않음 |
| WRAM staging | SNES: typed kind/version·frame/token·source/destination·length/개수 확인 후 inactive WRAM DMA | consume은 chunk만 해제; source capture lease는 유지 |
| SEAL/certificate | FPGA의 정확한 receipt 결과와 모든 chunk의 소비를 frame/epoch/serial에 결합; SNES는 기존 전체 coverage 확인 | 짧은 CRC/hash만으로 manifest 집합 검사를 대체하지 않음 |
| VRAM·표시·retire | SNES 최종 표시 ACK 이후 ARM dirty/resident commit 및 source lease retire | SPI packet ACK나 마지막 DMA 시작을 표시 완료로 취급하지 않음 |

FPGA parser와 SNES/ACK checker의 read owner 선택, 내부 packet credit 반환, typed kind 확대, tile↔map producer mux, certificate와 취소 전파가 실제 추가 회로다. host/NES clock 사이 fault·lease·retire 전달도 재검증해야 한다. STOP/오류는 partial receipt/chunk/certificate와 미완료 target 유효성을 폐기해야 하며, 이전 token/epoch의 늦은 consume/ACK가 새 frame을 승인해서는 안 된다. 이전 정상 화면 보존과 재시작 cold 복구가 필수다. 생략한 bit 검사를 certificate라는 이름만 붙여 없애지 않는다.

## 회로·메모리 예산

| 항목 | 확인 근거 | 판정 |
|---|---|---|
| 전체 logic | 240 FIT 필요15898/15408 LE,1003/963 LAB | 기존부터490LE·40LAB 부족. 새 parser 비용을 추가할 여유 없음 |
| RAM 시나리오 | 24054 + program4→6KiB의2 − semantic base6→5의1 + receipt1 | **56/56 M9K**, 여유0. 동시 구현·배치 미검증 |
| receipt | 256B, read/modify/write와 manifest 순회 필요 | 전용1M9K 계상. 기존 scratch 빈 주소만 보고 공짜 공유하지 않음 |
| typed payload | 기존2×2KiB aperture를 tile 소비 후 재사용 | trailer 형식으로 추가 full-chunk RAM은 요구하지 않는 정책 모델. mux/제어는 새 비용 |
| source semantic base | 5741→4398B 모델 | 원래 encoder의 row/raster 등 실제 logic을 **대체 제거**해야 함. 축소 byte 수를 LE 회수로 환산할 수 없음 |
| 추가 raw retained base | 별도2M9K 시나리오 | 현재 합산58/56; 회수 증거 없이 동시 추가 불가 |
| ARM | 233 RUN/IRQ 여유1616B에서 추가 retained448B →1168B | 1024B gate 위144B라는 산술. 새 input parser/plan callchain/IRQ 검증 아님 |
| SNES ROM | 이전 진단5886B, 이번 새 binary 없음 | 4KiB·6KiB 고정 없음. 확장 시 FPGA 저장 RAM도 전체 예산에 계상 |

240 MAP 계층표도 같은 경계로 보존했다. 아래 값은 **combinational function/FF**이며 FIT LE가 아니다. 부모 행은 자식 포함이다.

| 동결된 경계 | comb / FF | 해석 |
|---|---:|---|
| source240 전체 | 2092 / 974 | query/transport/encoder 포함 |
| 그 안의 encoder240 | 1399 / 409 | 위 행과 더하면 중복. 전부 제거 가능한 비용 아님 |
| sink SPI endpoint | 679 / 424 | map 소비 주체 변경 시 고쳐야 할 기존 경계 |
| tile bulk 전체 | 465 / 512 | 아래 aperture 포함 |
| 그 안의 aperture | 195 / 247 | RAM 재사용해도 token·주소·소유권 회로는 유지 |

허용 가능한 새 회로 크기는 현재0LE라고 단정하는 문제가 아니다. **실제 대체 경계에서 기존 부족490LE/40LAB + parser/중재/인증의 추가 비용 + mapper·timing 여유를 회수**해야 한다. MAP 부분 합을 FIT 총계에서 빼거나 FF 감소만으로 이 조건을 달성했다고 할 수 없다. 후보의 실제 전체 netlist가 없으므로 새 LE/LAB 수치는 미측정으로 남긴다. RAM의 단순합도 read latency·port·동시 수명·CDC가 맞고 전체 FIT에서 확인되어야 한다.

## 결론과 다음 판단 기준

분담만 바꾸어 기존 장벽·coverage·source 경로를 그대로 유지하는 안은 시간과 면적의 공동 여유가 없다. exact64/queued/500의 높은 표시 표본은 이미0.533ms, gap16/queued/500도0.419ms를 더 줄여야 한다. 여기에 source 준비·ARM 연산·FPGA parse·SNES chunk 고정 비용·일반 metadata 복사/dispatch·RLE/MVN·ordinary DMA·추가 poll·VBlank 대기를 더해야 한다. 설정1500에서 gap16의 전체 최대 부족은1.995ms다. 이 수치들은 새 구현의 하한/WCET나 실기 FPS가 아니다.

다음은 독립 opcode/seed 최적화나 즉시 전체 FIT가 아니라 **잔존 장벽/coverage의 구조적 변경과 source 회로 대체를 한 후보로 묶는 것**이다. 예를 들어 SEAL coverage 중 어떤 검사를 ARM 계획 확정 또는 FPGA receipt 검증과 중복 없이 합칠 수 있는지 검사별로 증명해야 한다. 954의1.049ms coverage를 통째로 없앨 수 있다고 가정하지 않는다. tile control/완료 순서를 바꾼다면 실제 공유 SPI·aperture 점유, 추가 descriptor/ACK byte와 큐 교착도 같이 계산한다.

그 후보에 양의 공동 예산 근거가 생기면, 같은954/970·952/955에서 실제 typed consumer 설정/서비스와 parser 경계를 최소 실행해 미지 비용을 측정하고, source replacement+receipt+ROM을 한 전체 보드에 결합해 FIT/필요 STA/CDC/IO를 판정한다. 새 입력을 포함한 full ARM RUN/IRQ·최종 display ownership을 함께 통과해야 P2 선정이다. 그 전에는 mapper 여유·60fps·실기 패키지를 승인하지 않는다. 이후에만 FIRSTLEVELSCROLL, 실제 표시 간격/최대 공백/화면 나이와 사운드·입력·메뉴를 확인한다.

## 증거와 재현

선택 결과는 private `probes/nes-schedule248/analysis04`이다. analysis01(실제 순서만), analysis02(gap16/trailer 추가), analysis03(최종 DMA 동일성·낮은 표시 표본·제어량 불변), analysis04(모든 packet credit·source event·단일 SPI 비중첩 확인,03과 집계 동일)는 모두 PASS이며 순서대로 보존했다. 최종1104개 일정(69×2범위×2소비×4설정), 직접 입력2235개 hash,284재구성,15Python 반례다. 새 simulation/FIT/65816/ARM 실행은0회다.

[분석기](../tools/analyze_nes_schedule248.py) · [집계](../analysis/schedule248-verification.json) · [1104개 일정](../analysis/schedule248-frames.csv) · [무거운4프레임 event](../analysis/schedule248-events.csv) · [142개 chunk 배치](../analysis/schedule248-chunks.csv) · [현재 계획](nes-schedule248-plan.json).

재현: `python tools/analyze_nes_schedule248.py --out <새 private 경로>`. 기존 private247/240/233 증거가 필요하며 ROM·원본 패킷은 공개하지 않는다. 생산227·진단5886B·기능240미배치·기각241/246/2472CPU·GBC164·save SRAM은 변경하지 않았다.
