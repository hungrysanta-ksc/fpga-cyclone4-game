# 557. E8가 알려주는 쓰기 권한과 마지막 OBJ 실행 시각

954에서 E9를 한 번 더 빨리 발행하는 ARM 후보를 시험하다가, 이전 연속 일정이 보드보다 늦게 다음 묶음의 입력을 허용한다는 점을 확인했다. **556에서 계산한 77 / 24µs를 보드의 E9 발행 마감으로 사용하지 않는다.** 이 문서의 비교는 동일한 입력·ARM·65816을 두고 모델이 바뀐 효과와, 모델을 고정하고 펌웨어만 바꾼 효과를 나눈다.

## 보드의 쓰기 권한

- 보드의 `nes_direct206`은 `nes_plan_batch206.host_idle`을 `nes_plan_spi200.plan_idle`에 연결한다. E8은 첫 command 바이트가 끝날 때 상태를 snapshot하고, E9도 그 경계에서 쓰기 권한을 래치한다. ARM은 CRC·수락 개수·fault·bulk descriptor를 검사한다. tile이 준비되어 있으면 먼저 처리한다.
- plan RAM에는 번갈아 쓰는 512B 뱅크 두 개가 있다. 호스트가 한 뱅크를 mailbox에 넘기면 다른 뱅크에 수신할 수 있다. 두 번째 묶음이 대기 중일 때는 NES가 앞 묶음의 **마지막 descriptor를 CHECK**해서 mailbox ACK가 호스트에 돌아와야 다음 뱅크를 넘긴다. 마지막 tile의 완료는 그보다 뒤일 수 있다. END 실행과 최종 표시 ACK는 각각의 실제 완료 조건을 계속 따른다.
- 기존 결합 모델은 `not todo and not flight`에서만 E9를 받았다. E8도 SPI 호출 시작에 샘플했다. 새 일정은 실제 두 뱅크의 소유권, mailbox 왕복, READ·CAPTURE·CHECK 순서와 command 바이트 샘플을 반영한다. 이번 53개 캡처는 검증한 short 형식만 사용한다. SPI 외의 드라이버 비용, tile·ROM 서비스, CDC 위상은 여전히 모델의 가정이다. [일정 구현](../tools/test_nes_banks557.py)

## 실제 FPGA RTL 대조

MMC551과 같은 보드 소스에서 SPI endpoint·plan RAM·mailbox·도메인 reset의 해시를 확인하고, 설치된 Questa Starter 한 좌석으로 순차 실행했다. 954에서 사용한 32 / 121 / 43B E9 패킷의 plan 수는 4 / 15 / 5개다. 첫 tile을 보류한 채 두 번째 뱅크 수신, 그 상태에서 허용 전 세 번째 E9 거부, 마지막 CHECK 후 tile 완료 전에 다음 뱅크 수신, 순서대로 23개 tile plan과 END 소비, 대기 중 공통 reset 취소를 두 클록 위상에서 확인했다. [보드 테스트벤치](../tests/nes-functional/plan_credit557_tb.sv) · [RTL 실행기](../tools/check_nes_end557_rtl.py)

별도 재생에서는 수정한 일정의 954 SPI 시각과 ROM 응답 기반 tile 완료 시각을 동일 RTL에 입력했다. 원본·재확인 후보 × 두 시작 위상 × 드라이버 비용을 SS 해제 전/후로 배치한 두 경우를 대조했다. 각 재생에서 E8 상태 8회와 E9 수락 개수, 응답 CRC, plan 순서와 END가 일치했다. 이 시험에서 chunk descriptor 입력은 비워 두었고, 실제 bulk 처리와 최종 ACK는 결합 실행·65816 독립 재생에서 검증했다. 전체 게임 코어의 ROM·PPU 동작이나 실기 FPS를 이 RTL 재생으로 측정하지는 않았다. [시각 재생](../tools/replay_nes_banks557_rtl.py)

## 무엇이 시간을 바꿨나

모델만 바로잡고 동일한 556 결합 ARM·65816을 실행하자 954에서 뱅크가 열린 시각은 직전 표시 뒤 40.135 / 39.852ms였다. ARM은 그 뒤 2.379 / 2.377ms에 마지막 E8을 샘플했고, 이는 직전 E9 이후 유일한 E8이었다. 이미 쓰기 가능했고 대기 bulk도 없었다. 최종 E9는 42.837 / 42.551ms에 수락됐다. 실제 최종 OBJ의 첫 ROM 요청은 66.853 / 66.848ms였다. 그 사이 약 24ms는 먼저 수락된 plan을 실행하는 데 쓰였다.

| 동일한 시작 위상 1 / 2 | 954 SEAL 전 경과 VB | 954 표시 간격 VB | 밀집 951–955 합계 VB | 밀집 평균 ms |
|---|---:|---:|---:|---:|
| 이전 단일 묶음 모델 · 556 | 5 / 5 | 6 / 6 | 28 / 28 | 93.175 / 93.172 |
| 두 뱅크 모델 · 같은 556 | 4 / 4 | 5 / 5 | 26 / 26 | 86.555 / 86.585 |
| 두 뱅크 모델 · 즉시 E8 재확인 | 4 / 4 | 5 / 5 | 26 / 26 | 86.555 / 86.592 |

954에서 두 뱅크 모델의 원본·후보 모두 첫 E8이 ready여서 추가 확인 분기를 탈 이유가 없었다. 53번째 ACK는 재확인 후보가 330 / 0 master clock(약 0.015 / 0ms) 늦었다. 후보는 Flash를 212,908→212,948B 늘리고 여유를 84→44B로 줄였다. 따라서 이 ARM 변경은 선정하지 않는다. 두 후보 모두 952·954·957 최종 대기 0회와 957 map 세 패킷 선행을 유지했다. 953은 두 위상 모두 5 VB였다. 556의 Quartus Lite 전체 보드 결과를 그대로 사용한다. 변경한 FPGA RTL이나 65816이 없기 때문이다.

## ARM 후보와 검증 범위

후보는 END가 이미 갖춰지고 다른 payload·map 공급 기회가 없을 때, busy로 확인한 E8 직후 같은 retry 안에서 **한 번만** E8을 다시 읽는다. 두 번째 응답도 같은 STOP·CRC·개수·빈 descriptor 검사를 거친다. 계속 busy면 기존 대기를 실행하고, E9는 준비 응답 뒤에만 발행한다. 1회 retry 예산에서 ready/busy·개수·예약 필드·early END·CRC·경쟁 bulk를 주입해 수락 여부를 확인했다. [ARM 변경](../tools/prepare_nes_end557.py) · [두 번째 응답 시험](../tools/check_nes_end557_arm.py)

재현 시 556 ARM01/src 및 client01, 489 원본 plans·capture, 231 raw·geometry, 555 tile fixture, 503 SPI 비용, 509 ROM 달력을 사용한다. 기존 일정은 `test_nes_end557.py`, 수정 일정은 `test_nes_banks557.py`에 `--keep-run`과 시작 클록 3,000,000 / 3,178,684를 준다. 65816은 `replay_nes_admit556.py`로 각 실행의 PUSH를 독립 재생한다. [비교기](../tools/analyze_nes_end557.py)

## 실기 전달 후보 MMC558

실기에서 동작한 MMC551의 ARM과 65816을 같은 두 뱅크 일정에 연결해 비교했다. 556 결합 경로는 재확인 polling 없이도 954 표시 6 / 6→5 / 5 VB, 밀집 다섯 화면 합계 28 / 28→26 / 26 VB였다. 평균은 93.057 / 93.050→86.555 / 86.585ms, 53번째 최종 ACK는 349.885 / 366.310ms 단축됐다. 952는 두 위상 모두 6 VB로 남는다. 첫 BG의 상대 ROM 구간이 늦어진 프레임은 없었다. 53화면의 RGB와 map·tile 내용, ROM 읽기 5,616회, VRAM DMA 114,352B, bank별 독립 검사와 최종 ACK를 비교했다. 이 표는 새로운 실기 FPS가 아니다.

MMC558은 556 결합 ARM에 시험 식별자·로그명만 바꿔 링크한 전달본이다. ELF 함수와 주소가 전부 같고, 이미지의 라벨·헤더 CRC를 검증했다. Flash 212,908B·여유 84B, BSS 18,592B다. 보드는 이미 FIT·STA한 556 client의 동일 SOF를 사용한다. MMC551과 조합 논리·FF·RAM 사용량 및 전체 STA 요약이 같고, 관련 setup/hold 최소 slack은 +0.078 / +0.139ns다. 전체 setup/recovery 최악값 −7.081 / −8.480ns는 기존 제한 실기 기준에 포함된다. 각 타이밍 뷰의 두 행은 동률의 endpoint 선택이 달랐으며, corner·양쪽 clock·검사 종류·slack·delay 전체의 다중집합은 일치했다.

5–40초·40–55초 기록, 메뉴 분기, 정상·program·DONE·busy·token 오류의 base 복구 경로를 라벨 빌드에서 점검했다. ZIP 안의 파일은 다시 읽어 해시·구성과 이름을 검증했다. 시험 ROM과 RESTORE는 포함하지 않는다. [MMC558 설치와 회수할 로그](nes-mmc558-trial.ko.md) · [보드·펌웨어 검증](../analysis/trial558-verification.json) · [ZIP 해시](../analysis/trial558-package.json) · [전체 비교](../analysis/end557-verification.json)

초기 RTL 준비 중 작업 파일 인자, END fixture 길이 및 시간 상수 폭을 수정했고, 시각 재생은 각 실행 폴더에 Questa 라이브러리를 생성해 완료했다. 선택 기록은 rtl04 / timed02다. 개인정보·라이선스 파일을 제외한 로컬 보관본 `probes/nes-end557/archive01/evidence.zip`의 3,538개 원본을 대조했다. SHA256은 `b2bd16cd47cd225189aefea9bb9dc10baaeb6f44dc6681cf203b893b1cf71cdf`다.
