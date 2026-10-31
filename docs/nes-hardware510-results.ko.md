# MMC509 실기 수신 분석510

[측정 JSON](../analysis/hardware510-mmc509.json) · [509 구현](nes-service509-contract.ko.md) · [전달본](../analysis/service509-package.json) · [PR140](progress/pr-140.md).

## 판정

사용자는 실행·메뉴 복귀 정상, 프레임 개선은 느껴지지만 크지 않다고 보고했다. 로그는 **60.08초 동안 최종 표시770회, 평균12.82fps /78.03ms**다. MMC502의60.07초636회·10.59fps보다134회 많고 관측 평균은21.05% 높다. 같은 동선의 새502 로그나 영상·장면 시각은 없으므로 순수 수정 효과나 첫 레벨 전용FPS로 단정하지 않는다. 모형의5.09%와 실기 관측21.05%는 비교 조건이 다르다.

**MMC509를 최신 기능 실기 기준으로 선택하고 MMC502를 복구 기준으로 보존한다.** 적재·384KiB readback·profile7b·START·STOP·base 복구와 사용자 메뉴 확인이 일치한다. CRC/전송 실패/ROM/receiver/video 오류와trace abort는0이다. 전달 firmware의 hash는 로그에 없으므로 label/profile/ROM CRC와 제작 manifest를 연결한 판정이다. screen_frames=0은 신뢰하지 않는 구형 telemetry이고, 실제 최종 ACK 뒤 증가하는 native_frames=770을 사용한다. screen_error169는SPC 초기화 결과 필드다.

## 개선과 체감의 차이

| 관측값 | MMC502 | MMC509 | 차이 |
|---|---:|---:|---:|
| 최종 표시 |636회/60.07초|770회/60.08초|+134회 |
| 전체 평균 |10.59fps|12.82fps|+2.23fps |
| 평균 표시 간격 |94.45ms|78.03ms|−16.42ms |
| 수신 포함 DWT/표시 |22.14ms|19.88ms|−2.26ms |
| 계획·공급 포함 |31.32ms|14.30ms|−17.02ms |
| 출력 준비·SEAL·최종 ACK 포함 |40.27ms|43.17ms|+2.89ms |

약21%의 관측 증가라도 절대값은 약2.23fps이며, 평균 화면 간격은 아직78ms다.60fps의16.67ms보다 약4.68배 길다. 개선과 제한적인 체감은 모순되지 않는다.

**계획 단계의17.02ms 감소를 ARM 계산 절감으로 해석하지 않는다.**508에서 END 이후 bulk 소비 완료 대기를 SEAL 안의 진행 처리로 옮겼다. 출력 선행 공급에 따른 중첩과 단계 경계 이동이 함께 있다. callback을 뺀10ms 단위 planner 관측은 약11.21→10.99ms로 비슷하다. 이 coarse 값도 IRQ·미완료 마지막 시도와 양자화를 포함하며 CPU cycle만의 측정이 아니다.

5초 frame-start 기준 묶음은72,80,61,48,48,51,62,81,70,78,66,53회다. 묶음별로48~81회 차이가 있으나 정확한 장면별FPS나 p95가 아니다. 레벨 진입 시각을 로그만으로 지정하지 않는다.

## 남은 비용과 예산

- 가장 큰 구간은 **출력 직렬화·일반 packet 소비·DMA·최종 검사·VBlank를 포함한43.17ms**다. 전부 DMA 시간이거나 전부 마지막 ACK 대기라는 뜻이 아니다.
- 입력 D1 본문은3389.44→2930.06B/표시, 출력 E1 본문은1750.23→1691.36B/표시다. 장면이 다르므로 이 감소 전체를 압축/공급 수정만의 효과로 귀속하지 않는다.
- 조회를 포함한 wire 투영은29.99→25.41ms/표시, 조회 제외는18.02→**16.25ms**다. 후자는16.67ms보다 작지만, 모든 필수 조회·명령 공백·계산·검사·ROM·VBlank를 위한 여유는 아니다. 관측 평균이며 프로토콜의 불가능성 하한도 아니다.
- 기존 잠정12ms wire 예산에 맞추려면 조회 제외 전송에서도 약**1395B/표시**를 더 줄여야 한다.16.25ms에서 조회만 없애면60fps가 된다고 판단하지 않는다.
- quiet 계측은 CREDIT4.04/DRAIN1.69/FINAL_ACK8.17ms다. 이들은 위 단계 안에 들어 있으므로 더하거나 모두 독립적으로 회수 가능한 시간으로 보지 않는다.
- 전체 평균에서60fps까지 **61.36ms/표시**가 남는다. 단순 E8·polling·작은 FSM 반복보다 출력 실행과 전송량을 함께 줄일 구조가 필요하다.

회로와 실행물은 그대로다.507 Lite15164LE/14172comb/8394FF/264816bits/51M9K, 잔여244LE·5M9K와 관련setup+0.078/hold+0.139ns를 재사용한다. ARM509 firmware212956B/Flash36B/BSS18576B다. 이번 분석에 새 firmware·ZIP·합성·Questa는 없다.

## 종료 경계와 수집 이력

771회 입력·commit 중770회만 최종 표시됐다. 마지막 요청은 SEAL 명령 자체가 아니라 **section5 raw modeA81B 일반 packet**(offset1505, sequence17, serial771, generation857)이다. 이미4개가 미소비 상태여서 credit을 기다리던 중 runtime deadline1/window2/sink2로 끝났다. 마지막 표시 시각59.95초, 전체60.08초이며 STOP/base 복구는 성공했다.

실제 전달 ARM03 ELF에서 같은 ordinary header와4credit 상태를 실행했다. 정상·guard deadline·post-transfer deadline·실제IO 실패·CRC 오류5조건을 구분하고, 관측 guard 경우1/2/2·pending4·flags7을 재현했다. 실패에서는 새E1 전송·새 표시 확정이 없고 재호출도 추가SPI를 내지 않는다. 변조된 로그18종을 거부했다. **SPI/시계는 모형이므로 물리 마지막 순간의 재생은 아니다.** 기존502의SEAL/pending1 예외를 넓혀 오류2를 일괄 면제하지 않았다.

보존된12개 capture 전이는 거부6/회복6이며 fetch/compact/raster/ROM 오류 필드는 모두0이다. 거부 candidate mask0/회복24는 이전502와 같은 형태지만, 전체 원인·거부율·손실시간이나 모든 거부가 정상 공백이라는 증거는 아니다. generation857−commits771을 손실 프레임 수로 계산하지 않는다.

## 다음 작업 순서

1. 검증된509를 유지한다. 변경 없는 부팅·전체FIT·ROM20frame 시험을 반복하지 않는다. 실기 관측을 모형에 맞추기 위해 시작 위상을 조정하지 않는다.
2. **43.17ms 출력 구간을 기존 실제65816 계측과 연결해 일반 packet 처리/복원·독립 검사·DMA·최종 검사·VBlank로 분리한다.** 기존 숨겨진 대기를 다른 단계로 옮긴 것을 계산 절감으로 중복 기록하지 않는다.
3. 입력·출력 본문과 packet framing을 함께 줄일 후보를 비교한다. 잠정12ms wire/16.67ms 전체 예산, 실제 ARM·공유SPI·IRQ·ROM·4credit/2bulk bank와 삭제할 제어·RAM·Flash를 포함한다. 출력 개선만으로 끝나지 않는 수신19.88ms도 함께 본다.
4. 같은 입력·시작 시각의 연속 비교 후 의미 있는 후보만 고유 이름 실기로 전달한다. 독립 검사·STOP·최종 ACK·VBlank·메뉴 복귀를 유지한다.505 고립 prefix DMA와 E8/polling/phase/seed 미세조정은 새 근거 전까지 동결한다.

## 보존·재현

원시3TXT는 `probes/nes-hardware510/run01`에 원본 byte/hash로 보존했다. receipt.json,termination01/result.json,analysis02.json이 선택 근거다. 분석01의 coarse planner 명칭을 수정해 마지막 미완료 시도 포함을 명시했으며 수치와 원본은 보존했다.

`check_nes_hardware510_termination.py --arm <service509/ARM03/src> --raw <run01> --out <fresh>`와 `analyze_nes_hardware510.py --receipt <nes-hardware510> --baseline <nes-hardware503/run01> --out <fresh-json>`으로 재계산한다. 기존502 분석 결과도 같은 parser로 재대조했다.509 제작 시점의 hardware_verified=false는 불변 스냅샷으로 남기고 실기 판정은 이510 문서/JSON을 따른다.
