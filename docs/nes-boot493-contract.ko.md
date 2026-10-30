# NES493 — 492 실기 부팅 실패와 분리·복구 관문

> **후속 실기494:**493은부팅·메뉴복귀정상,60.07초575표시/9.57fps다. 이전4899.60fps와지속가속은미확인이다. [현재 분석·다음 순서](nes-hardware494-results.ko.md)·[실기 근거](../analysis/hardware494-mmc493.json)를먼저읽는다. 아래의미확인/다음관문은493 제작당시기록이다.492 단일원인은미확정이며새word 경로는계속보류한다.

[실기492 실패](../analysis/boot493-hardware492.json)·[493 연결 검증](../analysis/boot493-verification.json)·[493 manifest](../analysis/boot493-package.json)·[설치/원복](nes-mmc493-trial.ko.md)·[PR138](progress/pr-138.md).

## 실기 판정

사용자가492 실행 실패·메뉴 복귀 정상을 보고했다. game ROM393216B 적재/CRC/readback,profile7b,START·STOP/base/safe_to_reload는 정상이다. 표시 시도는5020ms이고boot_reason5/boot_ticks500/44410poll로5초 준비 시간초과다. native_frames/transactions/wire/trace commit과12개 phase bucket이 모두0이다. **SNES 표시 클라이언트 ready를 확인하지 못한 수신/계획 전 실패**이며 성능/FPS 자료가 아니다. native_result2를 실행 중 transport 실패로 바꿔 해석하지 않는다.

screen_stage0과flag48→58은 관측값이다. untrusted telemetry/pin snapshot만으로 CPU가 어떤 명령에서 멈췄는지,실제로 아무 명령도 실행하지 않았는지 확정하지 않는다. 원래 strict 성능 파서는 이 실패 실행을 거부한다. ready 조건·timeout·CRC를 완화하지 않는다.

## 확인한 것과 미확정 원인

489와492 각각의 generated5120B Quartus MIF는 생성 ROM과 byte가 모두 같다.492 제작 시 기존5124 bus·실제CPU/픽셀·함수동일성·programmer 검증은 기존 근거대로 보존한다. 그러나 이것은 실물 초기 부팅의 증명이 아니었고492는 그 관문을 통과하지 못했다. 잘못된ROM바이트·M4 plan 로직·물리 IO·초기조건 중 하나를 단일 원인으로 확정할 증거는 없다. FPGA profile만으로 사용자가 설치한 프로그램 ROM hash를 실물에서 읽어 검증한 것도 아니다.

이번 실패 시점에는 새 plan 조회/word 복원 실행이 시작되지 않았다. 부팅 초기 경계부터 분리하며,초기화 실패를 fps0/성능 회귀율로 기록하지 않는다. 실제 menu 복귀는 사용자 보고와STOP/base/MENU_PREPARED 기록을 함께 근거로 둔다.

## 493 선택

493은 **실물에서 정상 동작한489 ZIP의 FPGA BI3를 byte/hash 그대로 추출**해 이름만 바꿨다. SNES 프로그램과 FPGA 배치·회로·loader/버스도489 그대로다. 새로 fitted한491/492 FPGA와 word DMA/MVN은 보류한다. 실패한492는 복원 대상에 포함하지 않는다.

ARM은491 query 변경을 유지하되493 label만 바꿨다.781 linked함수 주소·크기·명령과STM3 header 뒤 payload가 label 외에 같다.489/491의71개 canonical frame 일반/SEAL **2020packet이 byte 동일**해 같은ABI4891 소비 경계를 확인했다. 첫 BG·full/finish flush,credit/실제 소비 구분·독립검사·STOP·최종ACK·VBlank·base/menu는 유지한다.493의 실제 부팅·성능은 아직 미확인이다.

| 항목 | 493 |
|---|---|
| FPGA/SNES | 정상489와BI3 byte 동일,원래4311B body/5120B program |
| whole Lite | 15272LE/14078comb/8392FF/264800bits/51M9K,136LE·5M9K 여유 |
| 관련 setup/hold | 구현+0.183/+0.168ns,nominal+0.224/+0.168ns;기존489 근거 재사용 |
| ARM | firmware212844B,Flash148B,추가global0B,RUN31848B |
| 새 합성/Questa/programmer | 동일 바이너리·동일 함수·호환packet 근거를 재사용 |
| 성능 판정 | 신규493 실측 없음;491 word 복원 모델7.25%를493에 적용하지 않음 |

새 FPGA를 수정했다고 주장하지 않는다. 원래 검증된 부팅 경로로 되돌리면서ARM 변경을 분리한 구성이다. 전체 reset/CDC/IO/full stack·IRQ signoff는 여전히 미완료다. 실제 기준은489의9.60fps/실행·메뉴 정상이다.

## 다음 관문

전원을 끈 상태에서493 내용물 전체를 설치하고 첫 화면과메뉴 복귀/493로그3개를 확인한다. 우선 부팅 복구가 목표라 별도 성능 반복 실행은 요구하지 않는다. 정상이라도492 단일 원인 확정으로 승격하지 않는다. 실패하면493 로그와 정상489 복귀 상태를 비교해 ARM 초기 경계를 추가로 분리한다. 실제 부팅 회복 후에만 전체시간/IRQ·ROM 경쟁 최적화를 재개한다.

로컬 `probes/nes-boot493`의 raw492/receipt/candidate01/ARM01/assembly01/trial01/parser02을 선택했다. raw3TXT를 원본byte/SHA 보존하고공개JSON에 파일명/크기/hash와판정만 기록했다. 패키지493은489/485/482/476/164/467 원복과base/m3nu를byte/hash 보존하고상용ROM/save를제외한다. 정당한491 ARM/원본489 ZIP·ELF·고정입력 의존성은 [재현 범위](../cores/nes/REPRODUCING.ko.md)를 따른다. GBC/save를 보존하며불필요한 full 적재/합성/기존 정상경로 재실행·라이선스 smoke는 반복하지 않는다.
