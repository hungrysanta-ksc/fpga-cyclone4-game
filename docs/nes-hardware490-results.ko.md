# MMC489 실기 수신 분석490

[측정 JSON](../analysis/hardware490-mmc489.json) · [PR137](progress/pr-137.md) · [489 구현](nes-output489-contract.ko.md) · [다음 순서](nes-output487-plan.json).

## 판정

사용자가 실행·첫 레벨 플레이·메뉴 복귀 정상을 확인했다. 첫 레벨의 체감 개선은 작았다고 보고했다. 로그는60.08초에 최종 표시577회, **평균9.60fps /104.12ms**다. 타이틀·맵·레벨별 완료 시각/동일 입력 재생은 없으므로 레벨 전용 FPS나485 대비 인과적 개선율로 해석하지 않는다. **489 기능 실기 성공,60fps 미달,첫 레벨 가속 미입증**이다.

| 관측값 | 이전485 플레이 포함 | 이번489 플레이 포함 |
|---|---:|---:|
| 실행 길이/완료 표시 | 60.07초/494회 | 60.08초/577회 |
| 평균 FPS /ms | 8.22 /121.60 | **9.60 /104.12** |
| 수신 포함 ms/표시 | 31.78 | **30.06** |
| 계획·타일 공급 포함 | 40.31 | **34.29** |
| SEAL·최종 ACK 포함 | 48.33 | **38.65** |
| E1 driver 전송 B/표시 | 3720.88 | **2233.34** |

장면·조작이 달라 차이를 모두489 효과로 귀속할 수 없다.485 대기13.55fps는 별도 조건이다. 단계는 실제84MHz DWT 측정이며 그 안에 driver/IRQ/대기가 포함된다. op/quiet를 단계에 더하거나 단계 차이를 순수 CPU 절감으로 표시하지 않는다. 패키지에는 로그 바이너리 hash가 없으므로489 label/profile/ABI 전달 이력으로 연결한다.

5초 frame-start 묶음 완료 수는 **73,70,53,36,41,32,41,41,42,61,52,35**다. 초반은5초당73/70회(14.6/14.0회·초),중간15~45초는32~42회(6.4~8.4회·초) 수준이다. 이는 첫 레벨 체감 보고와 양립하지만 정확한 장면 경계나 frame p95가 아니다.

## 남은 병목과60Hz 비용

- 현재 전체 driver 전송은10509.32B/표시,2.625Mbps의 wire만으로 **32.03ms**다. D0/E0/E8 상태 조회만4700.72B/표시,전체의 **44.73% /14.33ms wire**다. 실제 driver 구간은 IRQ·guard 등도 포함해 이 세 op에29.23ms/표시를 쓴다.
- 평균 조회 수는 D0114.73/E0121.42/E867.72회/표시다. CREDIT/plan 대기10.63ms,DRAIN2.06ms,최종ACK8.47ms의 quiet 구간도 관측됐다. 이21.15ms는 단계에 중첩되고 guard/서비스를 포함하므로 그대로 회수 가능한 시간으로 계산하지 않는다.
- source/ordinary/plan 본문만은3275.69+1751.76+71.69=5099.14B/표시,wire15.54ms다.60Hz의5468.75B wire 예산 아래로 내려왔지만 framing·조회·복원·CRC·ARM·ROM·VBlank 시간이 빠져 있다. 출력 byte 절감만으로60fps가 되지 않는다.
- 전체104.12ms와16.67ms의 차이는 **87.46ms/표시**다. raw만 바꾼 모델의7.83% 개선을 실기 FPS에 곱하지 않는다. 더 작은 raw 복원 루틴을 반복 조정하는 것보다 E8 공급/E0 실제 소비·credit·최종ACK와65816 packet/검사 일정을 함께 다뤄야 한다.

## 종료·검사·복구

384KiB 적재/CRC/readback,START/run,receiver/sink/window/CRC 오류0,STOP/base_restored/safe_to_reload가 정상이다. 메뉴 표시는 사용자 확인과 PREPARED_RESET_HELD/MENU_PREPARED 로그를 함께 근거로 둔다. screen_frames=0은 명시적으로 신뢰하지 않는 필드이며 완료 수는 ARM native 최종ACK 진행577회를 사용한다.

끝의 native_video_error14를 단독 무시하지 않았다. runtime result1(60초 deadline),plan error2/미발행0/END0,오류0,trace abort0,입력 commit578=완료577+1의 결합 signature다. 전달된 ARM489 실제 linked 코드에서 guard 거부→nes_plan200_emit error2→명시적 zero-slot callback→video14/중단을 실행했고,이후 SPI/표시 없음과12개 잘못된 로그 거부를 확인했다. 기존485 error13 signature도 보존한다. 이는 실제 종료 순간의 재현이나 모든14의 정상 판정이 아니다. 마지막 미완료 입력은 표시 수에 포함하지 않는다.

## 다음 작업 순서

1. **489를 현재 기능 실기 기준으로 유지한다.**485/482/476/164/467 원복·GBC/save를 보존한다. 이번에는 새 ZIP/합성·추가 사용자 시험을 만들지 않는다.
2. 같은 고정 입력으로 E8 descriptor 공급/E0 소비 credit·ACK 소유자와65816 packet 수신/독립CRC/manifest/VBlank 실행 시점을 묶어 추적한다. 불필요한 중복 조회·과도한 정지와 실제 소비 지연을 구분하고 전체 최종 표시 시간으로 후보를 비교한다.
3. 근거 있는 공급/소비 변경만 구현한다. 즉시 준비 처리를 늦추지 않고 독립 검사·credit/소비 구분·STOP·deadline·최종ACK·메뉴 복귀를 유지한다. Flash124B/136LE 여유 안에서 기존 제어를 대체한다. 현재 MCU_RDY는 external_memory_ready이며 source-ready IRQ로 간주하지 않는다.
4. 그 다음 D0 source-ready 대기와 실제 ROM grant/입력 공급을 다룬다. 대기 상수/CRC 생략이나 새 매퍼/SPI 속도 변경을 함께 섞지 않는다.
5. RTL이 달라질 때만 같은-source whole Lite를 확인한다. 의미 있는 전체 시간 개선 뒤 새 번호 전달본으로 같은 장면 실기를 비교한다.

## 보존·재현

새 레시피/분석은 `tools/analyze_nes_hardware490.py`와`tools/check_nes_hardware490_termination.py`다. 로컬 `probes/nes-hardware490/run01`에 반환3TXT를 byte/hash 보존했고 receipt/termination03을 선택했다. 초기 import/endpoint/count 가정 실패는 console01..03에 남겨 두었다. raw·ROM·개인 경로는 공개하지 않고 공개 JSON의 파일명/크기/SHA와 파생 카운터로 추적한다. 기존 패키지/모델/timing JSON은 제작 시점 그대로 유지한다. FPGA15272LE/51M9K·관련setup+0.183/hold+0.168ns,ARM Flash124B/RUN31848B,전체 reset/CDC/IO/full stack·IRQ 미승인은 변함없다.
