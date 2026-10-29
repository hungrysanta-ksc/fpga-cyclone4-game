# NROM471: 실기457 경로의 입력 압축·ARM 단일 복원

2026-10-29. PR134. 선택 산출물은 FPGA `compact471-04/board`, ARM `arm471-04/src`, NMI 이동 ROM `scene02`다. 지난 실기467의 FPGA457/ARM418/정적428을 기준으로 만들었으며 출력2271 client와 loader profile78은 유지했다. 전달본 설치·로그·복원은 [시험 안내](nes-nrom471-trial.ko.md)에 있다.

## 구현과 유지한 경계

- 기존 snapshot source에서 같은 map 값의 연속 구간을 6B record로 보낸다. 기존 12B 반복 record보다 작고 15bit tag/attribute를 그대로 보존한다.
- 정상 세로 scroll progression은 시작 raster와 길이를 12B에 기록한다. fineY 증가, coarseY29의 nametable 전환, coarseY31 wrap을 검사하며 raw patch·불일치 구간은 기존 표현을 사용한다. 같은 값 반복도 기존 형식을 유지한다.
- ARM은 압축 record를 기존 `logical_record` 검사·저장 경로로 한 번 확장한다. 별도 전체 프레임 버퍼와 FPGA 재확장기를 추가하지 않는다. generation·영역·순서·count·coverage·CRC 검사는 유지한다.
- 입력 BEGIN은 `2231`에서 **`2232`**로 바뀌므로 firmware와 FPGA는 함께 설치한다. 출력 client2271 ABI, 최종 ACK 뒤 retirement, STOP의 취소·base 복구 순서는 유지한다.
- 추가 압축으로 드러난 CHECK 응답 경로는 tag 하위9/상위10bit를 독립 비교하고 데이터와 함께 1 memory clock 뒤 처리한다. 예상 밖 응답 소유권 오류는 즉시 hard fault를 유지한다. STOP·reset·CHECK_OPEN은 대기 응답을 버린다.

## 같은 정적 장면의 비용

| 항목 | 457/418 | 471 | 해석 |
|---|---:|---:|---|
| source payload | 5,764B | 1,926B | 66.59% 감소, canonical state 동일 |
| source block | 25 | 10 | 실제 D1 CRC·D2·D3 수신 |
| 성공한 source 전송 최소 wire | 6,279B | 2,156B | 상태/명령 overhead 포함, 빈 polling 제외 |
| 위 wire의 2.625MHz 시간 | 19.136ms | 6.570667ms | 서비스·대기·ARM 계산 제외 |
| 실제 M4 packet 해석 명령 | 309,514 | 270,899 | 12.48% 감소, 명령 수는 cycle 측정이 아님 |
| 전체 실기 평균 | 66.807564ms | **미측정** | 종전 14.968365fps, 새 FPS는 실기 로그 필요 |

위 wire 감소12.565333ms를 종전 전체 시간에서 바로 빼지 않는다. SPI·계산 중첩과 대기 비용이 다르고 이동 장면도 부하가 다르다. 30/60fps 달성을 선언하지 않는다.

## Quartus Lite 전체 비용

| 전체 보드 항목 | 457 | 471 | 차이 |
|---|---:|---:|---:|
| LE | 14,770 | 14,740 | −30 |
| combinational | 13,637 | 13,672 | +35 |
| FF | 8,037 | 8,063 | +26 |
| RAM bits | 185,824 | 185,824 | 0 |

Lite FIT 성공. FF 증가는 source progression15개와 CHECK 응답 stage11개다. LE는 줄었지만 조합 논리 자체의 절감으로 표현하지 않는다. 실제 nominal 관련 클록 setup **+0.081ns**, hold **+0.143ns**다. 강화한5.3ns 배치 예산 setup **−0.036ns**는 남아 있다. 기존 조건부 IO 분석에서 PSRAM margin4.243ns, SNES read envelope82.412ns, SPI reply166.318ns가 나왔지만 raw reset/recovery·CDC·미제약 IO는 전체 signoff가 아니다. 보드 종류·전기적 조건을 확장하지 않는 제한 진단 전달본이다.

처음 CHECK 주소 비교 경로의 setup−0.626ns를 발견했고 응답 stage를 도입했다. 중간 선언 순서 오류와 즉시 소유권 fault 누락을 고친 뒤 선택04로 다시 합성·검증했다. 실패 결과를 보존하며 seed 탐색의 성과로 계산하지 않는다.

ARM firmware는 text201,641/data10,040/bss18,468B(기준 대비 text+1,580/bss+392)다. RUN workspace stack31,848B는 유지하고 RUN 후 보고 stack은6,912B다. 보고 버퍼는4,096→6,144B이며 최대 formatter 시험4,760B가 들어간다.

## 기능 증거와 한계

| 검증 | 선택 결과 | 범위 |
|---|---|---|
| 실제 board/source SPI | `compact471-core01` PASS | 정적 10block CRC·D2·D3·STOP, canonical1,404record 일치 |
| old/new native C 및 실제 M4 | compare02/M4-final01 PASS | 전체 state 일치, 전송 토큰 차이는 비교에서 제외 |
| decoder guards | guards-final01 PASS | 잘못된 count/gen/header/raw9개, scroll wrap7개, CRC와 callback 취소2개 구분 |
| CHECK serialized | check04 PASS | 149check/18negative/16ordered ACK/96반복 query, 1clk 지연·취소·소유권 |
| clock stop | stop04 PASS | reference/NES·memory 중단 각각 sticky 보호, PLL/PSRAM 모델·적재 상태 seed |
| 이동 ROM 자체 | scene04 PASS | NES frame60/61/100/140의 scroll57/58/97/137, 매 frame1px, A 유지·해제 |
| 실제 연결 회귀 | **live03 PASS** | NMI ROM의 실제 NES/source→native ARM C→queue/tile→65816 DMA/VBlank→최종 ACK→run136 STOP |
| 메뉴 복구 ARM machine code | recovery-final 5종 PASS | 정상 safe return, program/DONE/busy/token fault는 unsafe 차단; 외부 장치 응답 모델 |
| programmer·post-fit client ROM | program01/eda01 PASS | BI3를 RBF와 바이트 비교, 기본 post-fit netlist의4096 ROM byte/reset vector 확인 |

live03은30 ACK/4,144 VRAM bytes/2 VRAM commands/최종1commit을 확인했다. 종료 observer는350527→350772 뒤 정지하며 independent 막대 pixel mask가 맞았다. 입력은 실행 중 NES에서 실제 SPI로 받았고 geometry fixture는 host에 공급하지 않았다. ARM은 native C, 65816은 Mesen, PLL/PSRAM·초기적재는 모델이다. 전체 ARM CPU·전체 적재·60초 연속 실기 시간을 한 simulation으로 입증한 것은 아니다. 빈 D0 테스트 RPC는65536 실제 RTL clock씩 진행하며 제품 polling 변경이 아니다. 작은 raster bench의 미연결 port 경고12개와 live 기존 경고84개도 성공 결과와 함께 보존한다.

66개 QSF 입력과 live03 source hash, 핵심7개 C source와 최종 ARM source, M4가 읽은 최종 firmware hash를 묶어 확인한다. 보고용 scene CRC 추가는 host live 핵심 C와 무관하다. post-fit EDA는 routed DB 복사본에서 수행했으며 RBF bit 추출이나 실기 readback 증거가 아니다.

## 새 실기 계측과 다음 순서

기존10ms 통계를 보존하고 DWT cycle 계측을 추가했다. D0–D3/E0/E1/E8/E9/EA/70/73/OTHER 각각 호출·전송 byte·64bit cycle 합·최대값을 기록한다. observer/screen의 직접 SPI도 포함한다. RECEIVE/PLAN/SEAL phase와 opcode 시간은 중첩되므로 더하지 않는다. `cost_counter_available=0`이면 cycle 기반 해석을 하지 않는다. IRQ·guard·wait를 포함하는 각 호출 interval은32bit wrap 차분, 합은64bit이며 기존 DWT/DEMCR 설정을 RUN 뒤 복원한다.

1. NROM471 이동 장면 실행·A·60초 STOP·메뉴 복귀·재실행과 새471 로그를 확인한다.
2. ROM만 기존428 정적 장면으로 바꾸어 동일 장면의 FPS·miss/repeat·phase/opcode 비용을469와 비교한다. 로그의 scene CRC로 둘을 구별한다.
3. 남은 실제 비용 순서대로 progress-aware polling과 ARM changed-group/raster 준비·capture/VBlank 중첩을 검토한다. 입력 압축만으로 전체 개선을 추정하거나 연구 경로를 일괄 교체하지 않는다.
4. 제한 mapper0의 지속 개선 뒤 같은 게임 T2와 MMC4/5 latch/tag/ROM 경쟁 T3로 확장한다. 현재471 결과는 MMC4/5와60fps의 합격 증거가 아니다.

정확한 산출물·비용은 `analysis/nrom471-verification.json`, ZIP 구성은 `analysis/nrom471-package.json`, 로컬 raw 증거는 `probes/nes-nrom471/validation01` 및 `validation02`에 보존한다. 이전467/164 복원 파일은 전달본에 바이트 동일하게 포함한다.
