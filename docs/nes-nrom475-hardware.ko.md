# NROM475: NROM474 두 회차의 동일 장면 실기 비교

2026-10-29. 사용자가474를2회 실행했고 영상 동작은471과 같으며 메뉴 복귀도 정상이라고 확인했다. 새 영상은 받지 않았다. 원본6개 TXT는 사용자 파일명·바이트 그대로 `probes/nes-nrom475/hardware01`에 보존했다. `tools/analyze_nes_nrom475_hardware.py --raw ../probes/nes-nrom475/hardware01 --out analysis/nrom475-hardware.json`으로 재현한다. 새 빌드·합성·Questa 시험은 수행하지 않았다.

## 이번에는 같은 장면의 실기 개선을 확인했다

| 항목 | 471/실기473 | 474 1회차 | 474 2회차 |
|---|---:|---:|---:|
| RUN 관측 구간 | 60.07s | 60.07s | 60.07s |
| 최종 표시 완료 | 1178 | 1417 | 1417 |
| 전체 평균 | 19.610454fps | **23.589146fps** | **23.589146fps** |
| 완료당 평균 시간 | 50.993209ms | 42.392378ms | 42.392378ms |
| 초기5초 표시 | 78 | 101 | 101 |
| 이후5초 표시 | 대체로100 | 118–121 | 118–121 |

이동 ROM CRC0fddf31c와 FPGA471 bitstream은 동일하고 ARM이 달라졌다. 관측된 표시 처리율은 **20.29% 증가**, 완료당 평균 시간은 **16.87% 감소**했다. 정상 구간은 약20→24fps다. 이는 예전 정적14.97fps와 다른 장면을 비교한 수치가 아니다. 다만2회 평균의 일치가 모든 frame 간격·capture 누락·pixel exact·60Hz·모든 게임의 합격 증거는 아니다. runtime에서 firmware/bitstream 자체를 SHA로 읽은 attestation도 아니다.

두 회차 모두384KiB 적재/readback·verified·START·STOP·base 복구·safe_to_reload가 정상이다. CRC 오류·driver 실패 전송·입력 abort는0이다. input commit1418/최종 표시1417/EA retire1417, sent11998/retired11997이다. 마지막 미완료1packet은60초 deadline에서 취소됐고 표시 완료로 세지 않았다. 1회차 window_error2는 quiet guard 종료,2회차 window_error3은 transfer callback의 deadline guard 종료와 일치한다. 최초 runtime_result1과 run_first_error0/STOP/base/메뉴 결과를 함께 해석하며 부수 sink_error2를 RUN 중 CRC 오류로 판정하지 않는다.

## 계획 개선은 실기 비용에서도 재현됐다

아래는 DWT84MHz 누계를 완료 표시 수로 나눈 포함 시간이다. 성공한 마지막 phase까지 집계하므로 시작/종료·취소된 phase의 나머지가 조금 남는다. IRQ·service·SPI·대기를 포함하며 순수 CPU나 개별 frame WCET가 아니다.

| 포함 구간 | 471 | 474 1회차 | 474 2회차 |
|---|---:|---:|---:|
| 수신·복원·입력 대기 | 16.056860ms | 18.398726ms | 20.673433ms |
| BEGIN·계획·FINISH | 13.629809ms | **6.085214ms** | **6.068296ms** |
| SEAL·drain·표시·최종ACK | 20.788756ms | 17.290037ms | 14.914326ms |

계획·준비 포함 구간은 **55.35–55.48% 감소**했다. 기존10ms 집계의 planner 경로에서 emit callback을 제외한 값도10.738540→약3.105152/3.048694ms로 줄었다. offline M4 계획 함수 명령 수 감소와 방향·크기가 맞지만 cycle을 명령 수에서 추정한 결과가 아니다. group39704개 중38286개(96.43%, 프레임당28개 중27개)가 정확히 재사용됐다. 입력·계획·출력을 함께 바꾼 전후 비교이므로 전체 향상의 인과 기여율을 한 변경에 독점적으로 배정하지 않는다.

1회차 coarse 수신 누계는 bin2603tick/profile2602tick으로1tick 차이가 있다. 나머지 phase는 일치하고2회차는 모두 일치한다. 별도 getticks 경계의 양자화 차이이며 숨기거나 동일하게 강제하지 않았다.

## 조회 수 감소와 실제 대기 감소는 구분해야 한다

| 항목, 완료 표시당 | 471 | 474 1회차 | 474 2회차 |
|---|---:|---:|---:|
| E0 호출 | 133.46회 | 63.22회 | 54.65회 |
| E0 wrapper 시간 | 14.692643ms | 6.896196ms | 5.960847ms |
| quiet 대기 | 없음 | 6.961251ms | 5.838691ms |
| E0+quiet | 14.692643ms | 13.857447ms | 11.799538ms |
| D0 호출 | 14.12회 | 36.84회 | 58.84회 |
| 수신 step 중 payload 없는 poll | 전체123 | 전체32347 | 전체63519 |
| 전체 wrapped SPI 시간 | 25.445332ms | 19.243260ms | 19.946495ms |
| 전체 wire 하한 | 16.204255ms | 12.411404ms | 12.427130ms |

E0는52.63–59.05% 줄었지만 일부를 quiet와 입력 D0 대기가 대체했다. E0와 quiet는 서로 다른 구간이지만 quiet 안에는 observer/screen service SPI가 들어갈 수 있으므로 quiet를 전체 SPI 시간에 다시 더하지 않는다. 이번 E1/E9 계측 분류는 정상이고 OTHER는0이다.

두 회차 사이 D0는31172회 증가하고 E0는12151회 감소했다. D0+249376B/E0−243020B/E8+740B/D1+216B로 native wire 차이7312B가 정확히 설명된다. D1은 두 회차 모두14180회, 약6.097ms/표시이고 ROM·프레임 수·실제 plan/출력 수는 거의 일정하다. 입력과 ACK의 대기 시각이 바뀌어 phase별 비용이 이동했는데 전체1417표시는 같았다. **NES capture/SNES VBlank/시작 위상에 따른 일정 효과가 남았다는 근거**이며 어느 위상 하나가 원인이라고 단정할 동시 timestamp는 없다.

credit quiet는 전체10회, 약0.000923ms/표시뿐이다. 지금 자료로4credit 저장 부족을 주 병목이라고 보거나 queue 수·기존 FPGA 본체 교체부터 다시 시작하지 않는다. FINAL_ACK quiet는4.311/3.199ms, 일반 drain quiet는2.650/2.639ms다. quiet 최대 관측353.43us는 nominal128us에 IRQ/service가 포함될 수 있다는 기존 설명과 맞는다.

## source 소유권을 실제 코드로 다시 확인했다

471/474의 `nes_capture_lease201`은 **이미 export COMMIT에서 collector를 해제하고 다음 한 프레임을 capture**한다. 이전 표시의 immutable ROM lease가 살아 있는 동안 다음 export는 `waiting_display`에 막히며 EA retire 뒤 허용된다. collector 시작은 사용 중이 아닐 때 NES scanline7/dot257이다. `nes_live_joint.sv`의 실제 exporter enable도 이 export_permitted에 연결되어 있다. 이4개 source의 hash가 선택한 FPGA66input 명세와 일치한다.

따라서 “다음 capture 겹침을 새로 도입”한다는 계획은 사실과 다르다. 기존 중첩에서 capture 완료·export 허용/생산·ARM 수신 시작·SEAL·최종ACK가 언제 발생하는지 먼저 같은 일정으로 확인해야 한다. geometry/ROM lease/최종ACK의 경계를 풀어 소유권을 덮거나 이미 존재하는 기능을 새 절감으로 계산하지 않는다.

## 다음 순서와 남은 목표

1. **474를 새 실기 기준으로 고정한다.** 두 회차·원본471/473·설치본474·복원물을 보존한다. FPGA 회로/제약은 변경되지 않았고 ARM Flash 파일 후미380B/RUN frame 뒤 산술 RAM4984B의 예산도 그대로다. 새 계측을 무조건 추가하기 전에 공간을 검토한다.
2. **실제474 M4의 수신·CRC·record 처리 비용을 먼저 profile한다.** 입력 wire와 payload는 안정적인데 수신 전체18–21ms가 남았다. 기존 수신은 단일 복원이므로 이중 복원을 가정해 삭제하지 않는다. 실제 PC/함수·검사 경계를 분리해 줄일 hot path를 선정하고 canonical bytes·CRC·coverage·cold/STOP을 유지한다.
3. **기존 capture/export/표시 중첩의 준비 시각을 한 일정에서 확인한다.** D0 empty/collector 완료/export 허용·source 생산/SEAL·최종ACK를 분리한다. 먼저 기존 RTL·실제 ARM 경로의 trace로 원인을 검토하며, 필요할 때만 제한된 계측/수명 변경을 선정한다. 단일 ARM receiver를 이전 표시 중 덮는 변경은 자동 허용하지 않는다.
4. **입력 hot path와 일정의 실제 이득이 있는 후보만 다음476으로 연결한다.** ARM 크기·RAM·SPI·guard·전체 처리 비용을 함께 비교한다. FPGA를 바꾸면 같은 source의 Lite 전체 FIT/timing을 다시 판정하고, 유지하면 재합성하지 않는다. 실제 설치본은 같은 이동 ROM·독립 검사·STOP·최종ACK·메뉴 복귀와 새 번호/로그/원복을 갖춰야 한다. 같은 smoke를 이름만 바꿔 전달하지 않는다.

30fps 평균33.333ms에는 **추가9.059ms/표시**,60Hz 평균16.667ms에는 **25.726ms/표시**를 줄여야 한다. 이는 평균 격차이며 WCET 합격 예산이 아니다. 30fps 중간 목표와60Hz/capture 무손실/p95/VBlank·전체 CDC/IO·같은 게임·MMC4/5는 계속 열려 있다. 이번에는 같은 장면의 실기 효과가 관측됐지만 아직 목표를 달성한 것은 아니다.
