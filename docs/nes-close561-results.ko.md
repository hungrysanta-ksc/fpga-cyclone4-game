# 561 · 완성된 타일 묶음의 조기 공개

실기 기준은 MMC558이다. 560에서 확인한 952의 ROM 요청 마감에 맞추기 위해 FPGA의 타일 묶음 공개 시점을 바꿨다. ARM·65816·SPI 패킷과 OBJ 순서는 그대로 두었다. [560 기준 일정](nes-supply560-results.ko.md) · [561 검증 데이터](../analysis/close561-verification.json)

## 48B BG의 소유권

MMC558에서는 다음 타일이 끝나야 host가 목적지의 불연속을 볼 수 있었다. 561에서는 NES 쪽 plan decoder가 READY에 도달해 같은 세대에서 종류가 바뀌거나 슬롯이 이어지지 않으면 기존 tile mailbox에 닫기 표식을 보낸다. 이 표식은 선행 tile 데이터 뒤에서 처리된다. host는 완성된 바이트만 공개하고 mailbox 응답을 돌려준다. 그 후 다음 plan이 ROM 읽기를 시작한다. 연속 슬롯은 하나의 chunk로 유지한다. FPGA의 bank는 SNES가 token을 써서 소비를 확인할 때 반환된다. END·표시·최종 ACK는 각각 기존 경로로 진행한다.

두 클록의 위상을 달리한 Questa 시험에서 board의 tile205, mailbox, bulk206, aperture188, control194를 연결했다. BG 슬롯 119–121의 48B, OBJ 슬롯 27·31의 32B씩을 실제 aperture에서 읽었다. 후보에서는 다음 OBJ ROM을 막아 둔 동안 앞 chunk가 공개됐다. 잘못된 token 거부, 표식 전송 중 STOP, 일부 바이트를 읽은 뒤 STOP, 다음 세대의 첫 chunk와 END를 확인했다. 기준·후보 합계 10개 시험을 한 라이선스로 순차 실행했다. 이 시험의 버스 자극과 ROM 응답은 테스트벤치가 제공한다.

## 연속 일정

각 칸은 기준 → 후보다. 952의 경과 시간은 951 표시 시점을 기준으로 했다. 마지막 ACK 차이는 동일 시작 시각에서 905–957 전체를 실행한 결과다.

| 지표 | 시작 위상 1 | 시작 위상 2 |
|---|---:|---:|
| 48B BG 마지막 바이트 read (ms) | 51.261 → 41.239 | 51.345 → 41.397 |
| 48B BG 소비 token 쓰기 (ms) | 51.324 → 41.284 | 51.390 → 41.443 |
| 슬롯 39의 첫 ROM 요청 (ms) | 67.351 → 66.302 | 67.194 → 66.263 |
| 슬롯 39의 첫 ROM 허가 (ms) | 82.985 → 66.303 | 82.968 → 66.264 |
| 952 SEAL 수락 (ms) | 87.464 → 71.421 | 87.368 → 70.307 |
| 952 표시 간격 (ms) | 99.761 → 83.362 | 99.727 → 83.240 |
| 951–955 합계 (VBlank) | 26 → 25 | 26 → 25 |
| 951–955 평균 표시 간격 (ms) | 86.555 → 83.157 | 86.585 → 83.121 |
| 957 최종 ACK 단축 (ms) | 82.989 | 33.501 |

두 위상 모두 슬롯 39 요청이 560에서 역산한 66.756 / 66.740ms 마감 전에 도착했다. 952는 SEAL 전 5→4 VBlank, SEAL 이후 1 VBlank였다. 953·954는 각각 5 VBlank를 유지했고 첫 BG의 상대 ROM 허가 구간이 늦어진 화면은 없었다. 957의 마지막 tile ACK 전에 발행한 map은 3→2건이었고, 952·954·957의 최종 검사 뒤 추가 대기는 0회였다.

각 위상의 53화면에서 타일, map, RGB와 최종 ACK를 대조했다. 후보의 독립 65816 재생은 9,464 / 9,462개 이벤트와 일치했다. ROM 읽기 5,616회와 VRAM DMA 114,352B는 기준과 동일하다. 이 일정은 링크한 M4 명령을 CPI 2로 실행하고 공유 SPI·IRQ·두 plan 뱅크·반복 ROM 허가 달력과 Mesen을 결합한다. 이전 tile의 host 복사, mailbox 왕복과 bank 공개에는 모델 시간을 부여한다. 실제 FPGA 전체와 ARM·SNES를 한 물리 시간축에서 계측한 값은 아니다.

## Quartus Lite와 실기 결정

동일 device·seed·SDC로 전체 FIT·STA를 실행했다. 고정 입력 파일 73개 중 바뀐 파일은 `nes_direct206.sv`와 `nes_tile_bulk206.sv` 두 개다. LE 15,164→15,256(152개 여유), 조합 논리 14,172→14,192, FF 8,394→8,398, M9K 51개다. MMC558 펌웨어는 그대로 212,908B이며 Flash 여유는 84B다.

대상 클록 경로의 setup/hold는 +0.078/+0.139→+0.079/+0.154ns였다. 표식 레지스터 입력·출력, decoder, tile, host mailbox 수신에서 각각 확인한 setup·hold도 양수였다. 전체 최악 setup은 −7.081→−6.601ns, recovery는 −8.480→−8.153ns였다. 그러나 같은 코너·같은 클록의 기존 음수 항목 중 **NES setup 3개와 PLL clk[1] recovery 3개가 악화**됐다. 예를 들어 NES setup −4.586→−4.781ns, PLL recovery −5.660→−5.948ns다. 새 음수 항목은 없고 미제약 IO 집계는 동일했다.

전체 STA에서 해당 경로의 양 끝도 추출했다. 후보의 두 slow 코너에서 NES setup 최악 경로는 ROM loader의 `phase[5]`에서 physical reader의 `request_toggle`까지다. fast 코너는 source epoch의 `gray[27] → epoch_meta[27]`이다. recovery 세 코너 모두 local memory의 `init_done`에서 physical reader의 `memory_reset[0]`으로 가는 경로였다. 표식의 전용 경로 분석과 이 기존 경로들의 결과를 구분해 저장했다.

**561은 성능 후보로 남기고 실기판은 MMC558을 유지한다.** 다음 작업은 loader START·STOP과 reader 요청의 클록 경계, init 완료 후 메모리 도메인의 reset 해제 순서를 먼저 검증하는 것이다. 같은 seed와 제약에서 해당 음수 항목, 새 표식 경로, 두 위상의 952 표시·957 ACK를 다시 대조한 후 다음 전달본을 결정한다.

## 재현

1. `prepare_nes_close561.py`로 MMC558의 보드 프로젝트를 복사해 변경 두 개를 적용한다. Quartus Lite로 `quartus_sh --flow compile board`를 실행한 뒤 기존 `timing506.tcl`을 실행한다. `report_nes_close561.tcl`은 기준과 후보 보드 디렉터리 양쪽에 복사해 `quartus_sta -t`로 실행한다.
2. 기존 FLOAT wrapper의 job에서 `check_nes_close561_rtl.py`를 기준·후보 보드에 실행한다. 선택한 결과는 rtl03이다. 첫 보드 준비에서 rtl/sys 하위 폴더 누락을 수정했고, 최종 FIT·STA는 board02에서 생성했다.
3. 560과 같은 fixture·ARM558·admit556/client01로 `test_nes_close561.py --keep-run`을 시작 clock 3000000·3178684에서 실행한다. `replay_nes_close561.py`로 각각 기준·후보의 마지막 aperture read와 consume을 추적한다. `analyze_nes_close561.py`는 네 독립 재생, 557 기준 추적, 두 보드 리포트를 함께 검사한다.
