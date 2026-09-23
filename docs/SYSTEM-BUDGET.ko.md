# P1 자원·대역폭·blackout·지연 초기 예산 — 2026-09-23

이 문서는 P0 정적 감사와 동결 결과로 만든 **계산 기준선**이다. 재현: Python 3에서 `python -X utf8 tools/p1_budget_calc.py --snapshot /path/to/private/local-snapshot`. 스크립트는 C fit 보고서와 네 기존 endpoint JSON을 읽고 출력만 하며 ROM/시뮬레이터/FPGA를 실행하지 않는다. 이 공개 저장소에는 해당 raw 보고서가 포함되지 않는다. 계산이 모르는 bus service·frame age는 숫자를 채워 넣지 않는다.

## 내부 자원 지도

C `pin.fit.rpt`의 RAM Summary에 있는 8개 inferred memory가 **431,104비트/56 M9K**를 정확히 합산한다. Port A read-during-write는 보고상 모두 `New data with NBE Read`; 아래 dual-clock과 충돌 시 의미를 포함한 실제 core 계약은 후속 검증 대상이다.

| 블록 | 논리 폭×깊이, clock mode | 비트 | M9K |
| --- | --- | ---: | ---: |
| GBC VRAM bank 0, 1 | 각각 8×8192, dual clocks | 65,536×2 | 8×2 |
| GBC WRAM | 8×32768, dual clocks | 262,144 | 32 |
| GBC ZP RAM | 8×128, dual clocks | 1,024 | 1 |
| CGB boot ROM | 8×4096, single clock | 32,768 | 4 |
| sprite OAM high/low | 각각 8×128, single clock | 1,024×2 | 1×2 |
| next-use builder table | 8×256, single clock | 2,048 | 1 |
| **합계** | | **431,104** | **56/56** |

LE는 14,877/15,408로 531개 남는다. capture/encoder/output FIFO 및 제어는 위 fit의 별도 M9K 항목이 없으므로 logic/register 및 **외부** PSRAM/SRAM을 쓰는 것으로 파악된다. 이것이 추가 4-entry FIFO/계측/버퍼가 무료라는 뜻은 아니다. GBC ROM/cache/save/capture/audio ring은 외부 16비트 PSRAM 주소 공간을 공유하고, renderer 프로그램/페이지는 외부 8비트 SRAM에 있다. 각 물리 칩의 정확한 용량·은행 경계·충돌과 타이밍은 보드 회로·부품 규격 및 MCU mapping 대조가 남았다.

## 유입량과 조건부 쓰기 하한

- GBC source clock 33.555556MHz, source frame 기준 561,792클록 = **16.742146ms**, 약59.7295frame/s. 이 값은 현재 모델의 입력률이다. CPU 속도를 낮추거나 원본 frame을 버리는 예산은 두지 않는다.
- G13 renderer 전송은 metadata 4,484바이트 + pixels 17,280바이트 = **21,764바이트/완성 frame**. 목표 평균 output은 최소 **1,299,953바이트/s**. 정확한 RGB555를 encoder가 이 전송량으로 표현한 해당 후보에만 적용한다.
- 현재 C `frame_output_pages.sv`는 `byte_valid=0`이고 metadata/pixel 모두 word 경로다. `sram_burst_writer.sv`는 인접 2바이트 word에 14 bus clocks를 예약한다. 중단·read·DMA·guard가 **전혀 없는 가상 하한**은 10,882 words ×14 = **152,348 bus clocks**, 84MHz에서 **1.813667ms/frame**, bus 시간의 약10.83%다. 실제 SNES 사용 가능 slot이 이보다 적거나 분산되면 이를 만족하지 못한다. 평균치만으로 270ns 다음-read 계약도 증명하지 못한다. byte fallback은 8 clocks/byte이며 현재 후보의 출력 경로에는 사용되지 않는다.
- `SNES-SRAM-SLOTS.ko.md`의 200연속 비-SRAM cycle/54µs에서 400바이트(약7.41MB/s)는 **특정 모형의 연속 허가**다. 실제 반복 DMA/HDMA·CPU read·refresh 중 평균 서비스율 상한으로 사용하지 않는다.
- 외부 PSRAM은 ROM cache miss, save, MCU load, capture read/write, audio ring을 중재한다. C endpoint의 request count만으로 실제 최장 PSRAM blackout이나 tAA/tWP를 정할 수 없다. 요청/응답 latency 분포, CPU 샘플 deadline, source별 최대 대기를 수집해야 한다.

## 동결 trace의 처리시간과 누적 위험

| 시험 | 관측 범위 | 최대 처리 clock / 561,792 | FIFO peak | 해석 |
| --- | --- | ---: | ---: | --- |
| nominal prefill | 10 synthetic RGB frames, real output RTL/모형 host | 535,928 / 561,792 = 0.954 | 26 | 개별 deadline 통과. 무한 연속 증명 아님. |
| dense phase 0 | 같은 10 frames, 높은 경합 | 854,748 / 561,792 = 1.521 | 28 | 최악 292,956클록(약8.73ms) 초과, 2회 초과. |
| dense phase 700000 | 같은 10 frames, 다른 위상 | 852,474 / 561,792 = 1.517 | 30 | 최악 290,682클록 초과, 2회 초과. |
| first DMA gaps | 첫 설치에만 일부 slot 허용 | 854,748 / 561,792 = 1.521 | 28 | 첫 frame 7,103클록 개선됐지만 뒤 2/3 frame은 동일. 반복 설치로 일반화 불가. |

위 모든 수치는 `results/g13-endpoint-*/verification.json`과 `g13-prefill-audit.json`의 기록이다. 10 commit/10 publish 및 제한된 RGB/SRAM exact가 기록돼도 원본 frame 누락·재정렬 없음과 장기 backlog 상한을 입증하지 않는다. `561792` 초과는 개별 변환 deadline 실패이고, 실제 원본 frame drop 및 완성 화면 재표시는 서로 다른 계측값이다. 시간 초과 두 회가 곧 실제 frame drop 두 회라는 식으로 환산하지 않는다.

기존 SNES **SRAM 오디오 ring 폐기** 분석은 frame-DMA+guard가 background transaction을 600,023 bus clocks, 약7.143ms 막고 그동안 469 audio samples/1,876바이트가 도착함을 보여준다(`AUDIO-SRAM-DELAY.ko.md`). 현재 제품 후보는 audio ring을 **PSRAM**으로 옮겼다. 이 blackout 수치는 SRAM 공유 경로가 왜 위험한지 보여주는 경계 사례이지 현재 반복 G13 frame 설치의 전체 service trace는 아니다.

## backlog·표시 지연 증명에 필요한 측정

1. 같은 후보에서 source frame ID와 첫 픽셀 시각, capture complete, encoder request/response, output FIFO enqueue/drain, SRAM commit, page publish, SNES upload_done, 실제 DMA/HDMA 완료, 표시 frame ID를 단조 clock/epoch와 함께 기록한다. 첫 설치와 정상 반복 설치를 따로 집계한다.
2. 매 source frame 끝의 미처리량 `Q[n]`, 구간 생산량 `A[n]` 및 서비스량 `S[n]`으로 `Q[n+1]=max(0,Q[n]+A[n]-S[n])`를 계산한다. phase sweep에서 장기 기울기가 0 이하인지, queue peak가 각 실제 buffer 소유권/용량 안에 있는지, complete frame age가 유한한지를 본다. FIFO peak 26/28/30은 capture 내부 순간값이며 전체 system backlog가 아니다.
3. steady SNES bus에서 `PHI2`, 주소, `/RD`, `/WR`, `/ROMSEL`, DMA/HDMA, refresh, SRAM grant, WE/OE/DIR 및 PSRAM client grant/response를 같은 timeline에 둔다. 최장 연속 blackout, slot 길이 분포, 각 frame당 실제 서비스 바이트를 낸다. 첫 설치 one-shot gap 계측을 반복 구간의 가용 시간으로 대체하지 않는다.
4. 최소 수백~수천 source frame의 예비 실행은 GBC/SNES 주기 beat 및 가장 긴 DMA/HDMA burst/위상 이동을 덮는 기간을 계산한 뒤 정한다. 숫자만 채우는 장기 pass로 끝내지 않고 backlog slope와 최대 age, epoch 무누락·순서, 완성 화면 재표시 횟수를 별도로 판정한다.
5. P2 변경은 M9K 추가 0개를 기본 예산으로 하고, 필요한 RAM은 기존 블록 packing 재배치/대체 기능 제거 또는 외부 메모리 중재 비용을 제시해야 한다. LE 531개는 상한이 아니라 fit 변동을 포함한 작고 불확실한 여유다. 모든 변경은 같은 source/constraint hash에서 fit 및 부하 시험을 재측정한다.

## 현재 판정과 다음 gate

연산 지연, 출력 SRAM service, PSRAM 중재, 소유권/epoch, host 모형 오차 중 **어느 것이 지배 병목인지 미확정**이다. 양수 slack·nominal 10-frame exact는 P1 통과가 아니다. 다음 한 가지 증거는 먼저 확장 UCP/board 계약(P0)을 닫고, 실제 반복 설치 주소·strobe/refresh/HDMA timeline을 확보하는 것이다. 하드웨어 관측이 필요하면 쓰기 pulse·OE/DIR contention 및 save 백업·rollback 조건을 만든 좁은 진단으로만 제안한다. 새 bitstream이나 실기 ZIP은 이 문서로 승인되지 않는다.
