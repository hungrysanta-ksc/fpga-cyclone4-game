# P1 출력 종단·반복 표시 진단 — 2026-09-23

## 대상과 재현 범위

`g13-prefill-endpoint-seed7-hold1-v1`과 같은 출력 후보의 비공개 Questa 실행 `g13-endpoint-p1-prefill-long30-phase0-v2-dense`를 집계했다. 시뮬레이션의 26개 관련 RTL 소스 해시가 기존 full-fit manifest의 해당 항목과 일치한다. 동일 물리 타이밍 통과를 근거로 사용할 수 있는 범위는 이 해시가 확인된 후보뿐이다. 원본 로그·시험 영상·게임 자산·라이선스는 공개 저장소에 없다.

조건은 dense 55ns, host phase 0, 첫 요청 225행, 30 source frames, synthetic ROM/save/audio 경합, 실제 출력 FIFO/CDC/page owner/frontend/SRAM 핀 모델이다. source clock 주기는 29.801324ns, host bus clock 주기는 11.904762ns, source 간격은 561792 source clocks다. host는 요청/상태/invalid 재시도/설치를 모델링하지만 실제 65816 주소·read strobe/PHI2/HDMA 파형은 아니다. 실제 게임 CPU와 보드도 연결하지 않았다.

시뮬레이터 사용권은 로컬 임시 FLOAT 서버를 통해 대여했다. 이번 실행은 30프레임 종료까지 오류·경고 0건이었고, 임시 서버는 실행 뒤 종료했다. 라이선스 파일과 서버 설정 사본은 Git에 포함하지 않는다.

## 관측

| 항목 | 값과 의미 |
| --- | --- |
| 데이터·순서 | 691200 RGB555 픽셀, 출력 SRAM 유효 652920바이트 exact; 30 commit/30 publish; host 설치 31회에서 epoch 0..29를 순서대로 사용, epoch 1만 한 번 재표시 |
| 처리 기한 | frame 2 = 854748클록, frame 3 = 702729클록으로 561792 한계 초과 2회. 나머지 28개는 개별 한계 이내 |
| 지속 구간 | frame 4..29의 처리 중앙값 558312.5클록. 처리 시작 지연은 frame 0 대비 정해진 source 간격으로 계산하면 frame 4에서 최대 433849클록, frame 29에서도 340283클록 남음 |
| 표시 시점 대용치 | pipeline 처리 시작→첫 host visible 29개 epoch에서 39.184..55.721ms. 마지막 epoch 29는 설치 종료까지만 검증되어 visible 시점은 없음 |
| 초과 원인 후보 | frame 2 픽셀 FIFO 대기 356473 중 합성 DMA와 겹침 330268클록; frame 3 palette 페이지 소유 대기 74665, palette FIFO 대기 106182 중 DMA 겹침 85244클록 |

처리 시작 지연은 frame 0을 기준으로 한 **상대값**이다. 캡처 시점부터의 절대 backlog나 실제 게임 화면 age로 해석할 수 없다. 표시 시점도 합성 host의 pipeline 시작 기준 대용치다. epoch 1 재표시는 완성 화면의 재표시이며, 이번 관측에서는 source epoch 누락이나 재정렬이 없었다. 30프레임의 frame 29 지연이 양수인 만큼 이 짧은 실행만으로 backlog가 모두 해소되거나 장기 안정이라고 말할 수 없다.

## 반복 가능한 분석

로컬 로그에 `tools/analyze_endpoint_backlog.py`를 실행한다. 명령의 클록 수치는 반드시 해당 testbench에서 다시 확인한다. 도구는 raw log 경로를 출력하지 않고 집계 JSON만 출력하며, 프레임 누락, commit/publish 수 불일치, 기한 초과 집계 오류, host epoch 건너뛰기를 거부한다.

```sh
python tools/analyze_endpoint_backlog.py /path/to/private/vsim.log \
  --source-frame-cycles 561792 --source-clock-ns 29.801324 --host-clock-ns 11.904762
python -m unittest discover -s tools -p test_analyze_endpoint_backlog.py
```

비공개 원본에서 분석 도구 4개 계약 검사와 실제 로그 집계가 통과했다. 로그가 없으면 공개 저장소 단독으로 숫자를 재계산할 수 없다.

## 두 번째 설치 DMA 경계의 별도 진단

동결 renderer의 **두 번째 설치**만 대상으로 동일 크기의 one-shot native 변형 64개를 실행했다. metadata 7회와 pixel 24회 DMA 시작·끝, 독립 반복 지점 2개를 관측했고, 후반 128개 화면/2949120 RGB555 화소가 정확히 일치했다. pixel 간격의 18바이트 설정 명령과 24개 trigger를 binary로 대조했으며 잘못된 레지스터와 0길이 간격의 부정 대조도 검출했다. 비공개 결과 ID는 `g13-steady-dma-boundaries-v3`; 첫 두 실행 준비 시도는 격리 경로 검사에서 빌드 전에 중단됐다.

| 설치 구간 | metadata 전체 / 설정 간격 합계 | pixel 전체 / 설정 간격 합계 |
| --- | ---: | ---: |
| 첫 설치 기존 계측 | 10085 / 711 dot (7.05%) | 43574 / 1207 dot (2.77%) |
| 두 번째 설치 | 12476 / 785 dot (6.29%) | 37743 / 1013 dot (2.68%) |

이 수치는 native 에뮬레이터의 H/V 경과 시간이다. 첫 설치 helper 실행의 후속 위상 영향, refresh/HDMA, H/V 양자화가 남아 있으며 실제 cartridge 주소·PHI2·read strobe나 SRAM 쓰기 가능 시간을 측정한 값은 아니다.

두 번째 설치의 **각 설정 간격에서 관측한 최솟값**만 쓰고 양끝 12 dot을 계속 차단한 합성 host 민감도 시험을 했다. 첫 설치와 기존 metadata 40행/pixel 115행 envelope는 유지했다. 같은 26개 출력 RTL 소스의 prefill-only dense55/phase0/10프레임 비교에서 frame 2는 854748→847445클록, frame 3은 702729→706292클록이었다. 두 조건 모두 **기한 초과 2회**이며, 새 시험도 230400 RGB555 화소·217640 출력 SRAM 유효 바이트 exact, 10 commit/publish, host 11설치(완성 epoch 1 재표시 1회), Questa 오류·경고 0건이다. 따라서 관측된 간격만 반영해서는 이 모델의 처리량 gate가 닫히지 않는다. 변경한 FPGA HDL이 없으므로 새 full-fit은 하지 않았다.

## 다음 gate

1. 반복 설치의 native H/V 경계는 별도로 관측했다. 이제 실제 SNES 주소/PHI2/read strobe와 WRAM HDMA 개입을 확인한다. 계측된 설정 간격 전체를 쓰기 슬롯으로 취급하지 않는다.
2. 같은 후보로 더 긴 생산/소비 추적을 수행하고 capture 시점, commit, publish, install, visible을 분리 계측한다. 상대 시작 지연뿐 아니라 실제 대기량과 frame age 상한을 계산한다.
3. 보드 SPI/SNES slot/SRAM/PSRAM/DAC 계약과 STA 미제약 경로를 닫은 후에만 새 실기 후보를 판단한다. 현재 결과는 처리량 gate·제품 gate 통과가 아니다.
