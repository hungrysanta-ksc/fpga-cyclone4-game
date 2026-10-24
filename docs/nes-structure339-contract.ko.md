# NES339 geometry·첫 BG 공급 및 host/source 구조 예산

338 RTL + 336 ARM을 유지한다. 339는 기록 기반 전송 모델과 교체 예산 검토이며 새 RTL/ARM 실행·Quartus 합성이 아니다. 실제 부족은 제한 ROM 연속 일정 4.022994145ms, 조합 논리 1,866개로 그대로다. PR131에서 다음 구현의 통과 조건을 정한다.

## 비교 근거와 후보 선택

`tools/analyze_nes_structure339.py`가 기존 338 근거 466개를 재해시하고 905..975의 71개 원본 상태를 복원한다. 결과는 `analysis/structure339-verification.json`에 입력 해시와 함께 저장한다. Python 모델의 잘못된 영역·중복·범위 초과 213건은 거부했다. 이는 새 RTL의 STOP/CRC 시험을 대신하지 않는다.

| 전송 모델 | 71개 성공 전송 wire 합계 | 제한 |
|---|---:|---|
| 기존 N5 | 52,113B | 실행된 기준 |
| 영역별 최적 DP | 26,385B | offline 참고, 회로 구현 비용 미정 |
| 전체 영역 bounded greedy | 32,858B | 7개 프레임 회귀, 채택하지 않음 |
| map MASK/SHIFT 유지 + 나머지 영역 greedy | 26,273B | 기록 내 wire 회귀 없음, 다음 구현 후보 |

마지막 혼합 후보는 map의 기존 MASK/SHIFT와 독립 복원을 유지한다. nonmap은 4B 영역·단위 offset·literal/repeat 길이 record를 사용한다. 최대 record 243B, bank payload 248B를 유지한다. 새 tag 65..72는 기존 map tag와 분리한다. H20/BG seal10/END6은 길이를 청구한 placeholder이며 실제 새 CRC·버전·parser는 아직 없다. 기존 parser가 새 ABI를 받아들이게 해서는 안 된다.

warm907 payload 511→103B, bank 3→1, 성공 wire 564→126B이다. cold905는 wire 6,058→3,375B이며 전송만의 commit 하한은 18.674286→10.401524ms이다. 압축률은 CPU/FPGA 실행 시간이나 60fps 증거가 아니다. 현재 668B 실제 warm 입력에는 empty polling이 포함되며 생산 대기이므로 그 비용을 공짜 절감으로 빼지 않는다.

## geometry 확정 순서와 포트 소유권

map→row→exception→raster→mask→palette→counts→BG seal→OBJ→raw→최종 seal 순서를 검토한다. ARM은 검증된 BG 영역으로 generation에 묶인 private BG 준비만 수행한다. OBJ/raw 및 전체 CRC·semantic 검사가 끝난 COMMITTED 이전에는 E9/ROM 요청·출력 lease·token을 공개하지 않는다. counts의 OBJ 항목 검증도 최종 단계에 남긴다.

한 bank 안의 BG prefix는 bank 전체 수신/CRC 전에는 확정되지 않는다. 따라서 순서만 바꾸는 효과는 0일 수 있다. 별도 BG seal bank를 닫는 변형은 D4 한 번, 15wireB와 8us gap, 총 53.714286us를 추가 청구한다. 실제 ARM 수신 중 private 준비와 SPI의 중첩은 현재 실행기로 입증되지 않았다. 새 incremental receiver로 측정해야 한다.

source 입력 동안 phase RAM 512..1023은 source 소유이며 plan은 COMMIT 뒤에만 사용한다. source base의 기존 5,120B 할당 안에서 영역 padding 2B를 포함한 4,912B를 16bit word로 비교하고, q_held64를 16bit씩 소비하는 후보를 검토한다. 현재 global byte threshold/subtract 주소 선택을 영역별 query index/word cursor로 대체한다. base add/mux·serial emitter·CRC·query 의미 검사는 남고 map mask/shift 엔진도 남는다. 단순 scan 하한은 0.446364→0.223273ms지만 query/encoder/stall은 제외되어 있다. RAM M9K packing은 합성 전까지 미확정이다. 클록이 다른 host/NES FSM과 CDC를 무료 통합하지 않는다.

## 첫 BG plan과 시간 예산

현재 첫 E9는 46wireB(clear + BG 5개)다. clear + 확정 BG 하나의 18B prefix, 나머지 36B로 나누면 첫 전송은 85.333333us 빨라지지만 총 8wireB와 gap, 32.380952us가 늘어난다. 후속 낮은 slot/중복/재사용과 batch 정렬의 동등성을 입증해야 한다. BG 완료 표식은 그대로 유지한다. plan credit·DMA·IRQ 처리가 준비 작업보다 우선한다.

| warm907 일정 | 실제338 총 시간 | 60Hz 부족 | post-ROM |
|---|---:|---:|---:|
| 동일 시작·ROM 위상 | 25.051199382ms | 8.384532715ms | 3.833249ms |
| 제한 ROM 연속 | 20.689660812ms | 4.022994145ms | 3.833795ms |
| 정상 연속 | 13.410066350ms | 없음 | 기준 JSON 참조 |

제한 일정의 이전 ROM close는 source 시작에서 1.728002082ms다. 후보 성공 wire commit 하한 0.395809524ms와 첫 E9 prefix 0.062857143ms를 빼면 nonwire 허용량은 1.269335415ms다. 설계 상한은 source query/compare/seal 0.45 + ARM decode 0.10 + BG 준비 0.36 + 첫 plan/refill 0.18 + IRQ/CDC/poll 0.11 = **1.20ms**로 정한다. 조건부 여유는 69.335us, 별도 BG seal 전송을 중첩 없이 더하면 15.621us뿐이다. 모두 예산이며 실제 실행 측정값이 아니다.

post-ROM 목표 3.180ms까지 별도 0.653795ms를 줄여야 하며, 앞부분은 최소 3.369199145ms 당겨야 한다. 동일 위상에서는 각각 0.653249/7.731283715ms다. ROM 허용 구간을 실제로 넘지 못하면 요청만 빨라져도 총 시간 개선은 없을 수 있다. wire 절감이나 ROM 주기 하나를 전체 시간에서 단순 차감하지 않는다.

## 실제 삭제 범위와 전체 회로 예산

338 whole Lite MAP은 22,144LE / 17,274comb / 9,018FF / 307,808bits다. 용량 15,408comb에 대해 1,866개 부족하다. 다음 값은 예측 합성치가 아닌 통과 상한이다.

| 중복 없는 범위 | 현재 comb | 목표 상한 |
|---|---:|---:|
| host | 2,161 | 1,146 |
| validator/aperture | 1,159 | 1,160 |
| queue/SPI | 798 | 600 |
| source encoder/transport/mailbox | 1,747 | 1,100 |
| plan | 459 | 297 |
| 합계 | 6,324 | 4,303 |

범위 밖 10,950을 유지하면 2,021개 순삭제 후 whole 15,253, 여유 155개다. 새 RAM arbitration/CDC/decoder 비용을 모두 포함한다. 범위 밖 이전값 10,973을 적용해도 132개 여유다. queue/SPI + source transport/mailbox + plan을 통째로 공짜 삭제해도 1,656개뿐이므로 host/source datapath 교체가 필수다.

host는 이미 active305 record가 있으므로 이를 신규 절감으로 재계상하지 않는다. CHECK/PCAP ordinary seed/EXPAND와 metadata MREAD/MCAP RLE, parser_address/cursor/at의 중복을 하나의 checked-run 실행 경로로 대체해야 한다. 기존 byte ABI로 복원하면서 같은 주소 로직을 다시 만드는 경우는 기각한다. 독립 expected 저장, 실제 SNES read CRC/coverage/private RAM job 및 drain 후 ACK는 유지한다. 65816 소비 ABI를 바꾸면 실행 비용도 다시 청구한다.

host 1,015개 삭제와 source 총 647개 삭제는 아직 입증되지 않았다. transport/mailbox 399를 유지할 경우 encoder는 1,348→701이어야 하므로 상당히 공격적이다. FSM만 옮긴321의 +266comb, unit ABI 후 byte 복원을 남긴323의 −11comb 실패를 반복하지 않는다. whole cap을 만족하지 못하면 구조를 다시 선택한다.

## 다음 구현과 중단 조건

1. 혼합 source ABI·영역별 word query와 실제 M4 incremental receiver를 최소 경계로 구현한다. full commit 장벽, cold coverage, 잘못된 region/order/length/CRC/generation, STOP 중간 취소와 재사용을 검증한다.
2. private BG 준비 및 immutable 첫 plan 공급을 실제 SPI·IRQ·2슬롯·staging 일정에 연결한다. 첫 prefix/별도 seal을 각각 분리 측정하고 cold 비용과 normal 회귀도 기록한다.
3. host checked-run 교체에서 삭제된 로직과 새 포트 소유권을 확인한다. 독립 expected/actual 검사, 정확한 소비 완료, STOP freeze, 최종 ACK·VBlank를 유지한다. 동일 위상·연속 일정을 분리한 뒤 같은 소스의 whole Quartus Lite 비용으로 판단한다.

339에서 새 simulation/MAP/FIT/STA를 수행하지 않았다. 선택된338의 기존 fault 근거는 유지되지만 새 ABI에 전이되지 않는다. full RUN/71개 실제 연속 실행/전체65816/하드웨어 WCET/물리60fps는 미확정이다. production227/GBC164/saveSRAM은 변경하지 않는다.
