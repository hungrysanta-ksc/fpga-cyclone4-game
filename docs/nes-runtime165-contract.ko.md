# NES165 MCU 영상 루프 연결과 전체 링크

## 목표와 결과

165 새 영상 경로를 실제 MCU 게임 루프에 연결하고 전체 ARM 링크를 통과했다. 수신→변환→SNES 표시 ACK 후 다음 프레임을 처리한다. 로그 스택은4864→768바이트로 줄였고, 정적RAM60424/65424바이트·여유5000바이트다. 명시적 RUN 호출 경로의 스택 합계3120바이트는 전체 IRQ/메뉴 경로 승인이 아니다. FPGA는boundary165/map02 그대로이며 새SD·실기·60fps는 아직 미확인이다.

이 작업은 진단 항목을 늘리는 대신 FPGA 영상 데이터를 실제 SNES 화면으로 보내는 MCU 배선을 완성하는 단계다. 아직 실기 속도가 개선됐다는 증거는 아니다. PR109의 [선택 FPGA](nes-boundary165-contract.ko.md)를 그대로 사용한다. 새 FPGA 합성·배치·Questa 실행은 없다.

## 실행 계약

`nes_native_runtime165`는 caller-owned receiver18064바이트와 video15888바이트를 사용한다. COMPLETE에서 PREPARED 승인을 보내고 COMMIT을 받으면 변환·패킷 전송을 한다. SNES의 generation/sequence/serial이 일치하는 SEAL ACK 이후에만 consumed와 표시 프레임 수를 갱신한다. MCU에서 두 후보 표를 읽어 비교하지 않는다.

실제164의 `nes_run136.inc`를 재료로 만든165에는 새 루프가 들어갔다. ROM ID74, 상태73의E6/version2, observer70의E5, nativeD0의D6, sinkE0의F6를 각 담당 단계에서 엄격하게 확인한다. 기존6B를 호환 ID로 허용하지 않는다. SPI1의2.625MHz와 SS 간격·CF86/CSS/NMI 보호는 유지한다. 1..259바이트 엔진은 기존 검증된149 엔진에서 파생하며 helper 이름만 분리한다.

- SPI 거래 전후와 sink ACK 대기 중에 시간/오류 guard를 실행한다. guard의 observer SPI는 바깥 거래가 끝난 경계에서만 호출한다.
- 100Hz `getticks()`의 unsigned 차이6000으로 시간을 제한한다. 변환·전송 시간이 포함되며 기존1200회×50ms 대기 방식이 아니다. 실제 발진/틱 주기의 정확도는 실기에서 확인한다. 반복4194304회와 ACK65536회는 정지 방지 상한이며 시간 단위가 아니다.
- observer는5tick 간격으로 확인한다. SNES client의 패드·SPC와 FPGA DAC는 그대로다. 이 작업이 버튼 유지·사운드·표시 속도를 새 실기에서 검증했다는 뜻은 아니다.
- protocol/CRC/불확실한 ACK에는 재전송하지 않는다. 시간 만료·데이터 오류는 기존 reset-before-STOP 회수로 진행하며, CF86 하드웨어 가드 실패는 기존 fail-closed 정책을 유지한다. RUN 중 SD 기록은 없다.
- `native_result`:0실행 중,1시간 만료,2서비스 중단,3전송 실패,4수신 오류,5표시 오류,6반복 상한,7잘못된 인자. 첫 원인을 보존한다. 결과1도 frames=0이면 정상 표시 통과가 아니다.
- 정상 종료 후 frames/generation/transactions/wire bytes 및 receiver/sink/video 오류를 기존 최종 로그에 추가한다. SD 쓰기와 메뉴 복귀는 실제 실기 확인 전이다. 물리 리셋에 의한 새 로그 기능은 아직 추가하지 않았다.

## 메모리와 검증 범위

| 항목 | 선택 arm02 결과 |
| --- | --- |
| 전체 firmware.stm |196052바이트 |
| 정적 RAM |60424/65424바이트 |
| 스택·힙이 공유할 잔여 RAM |5000바이트 |
| receiver / video 또는 종료 로그 |18064 /15888바이트 |
| runtime context |100바이트 |
| save_report 함수 스택 |4864→768바이트 |
| 명시적 RUN 호출 경로 합계 |3120바이트; 전체 상한 아님 |

첫 arm01은 링크됐지만 기존 로그 스택에 호출자를 더하면 잔여 공간을 넘겼다. arm02는 게임 종료 뒤 수명이 끝난 video와4096바이트 로그를 union으로 공유한다. 오류 스칼라는 별도 context에 먼저 보존하므로 메뉴 복귀 전후의 반복 로그에도 변환 버퍼를 읽지 않는다. receiver/로그를 카트리지 SRAM에 두지 않는다. `.data/.bss`뿐 아니라8992바이트 `.ahbram`과 링크 주소까지 포함했다. 초기 armcheck03의 두 섹션 합계13992바이트 여유 계산은 **폐기**했고, `__heap_start`→`__stack` 실제 주소 차이5000을 사용한다.

test04는 실제 C receiver/converter/sink/SPI CRC/runtime을 함께 실행했다. 기존 RTL 캡처191거래를 읽고 synthetic sink의45패킷/45응답으로 한 프레임을 완성했다. 정상·tick wrap·ACK 중 시간 만료·stale SEAL·전송 실패·서비스 실패·native CRC 오류·ACK 상한 및 idle 시간 만료/반복 상한10조건과 잘못된 limit를 확인했다. 이 시험의 sink ACK는 모델이다. 이전 실제 SNES의227패킷 검증은 재사용했으며 이번에 실제 MCU+FPGA+SNES를 함께 실행한 것으로 세지 않는다.

실제 전체 ARM ELF에서 새 함수의 연결, START→display enter→runtime→display leave 순서, strict ID, 강한 NMI와15stores/0calls fail-stop, GPIO 매핑을 확인했다. 원본1393개 준비 입력 중7파일 변경/13파일 추가다. GBC 소스·기존164 설치물·별도 세이브 SRAM은 유지한다. 다만 전역 RAM 증가가 일반 메뉴/GBC의 스택 여유에도 영향을 주므로 **전체 인터럽트 중첩·라이브러리·다른 메뉴 경로의 스택 승인은 미완료**다. 3120바이트 부분 합계를 전체 안전 보장으로 사용하지 않는다.

test01/armcheck01의WinError623은 sandbox DLL 실행 오류다. 호스트 실행으로 해결했으며 라이선스 문제가 아니다. armcheck02는Windows CRLF 파서 오류였고 ELF 변경 없이 수정했다. armcheck04/test04가 최종이다. 실패 원자료·arm01은 그대로 보관한다.

## 재현과 다음 작업

`tools/nes_runtime165.py --evidence <164 evidence> --out <새 ASCII 폴더>`로 준비한다. 기존 `build_nes_game149_arm.ps1`과 고정 mini로 전체 링크한 후 `tools/check_nes_runtime165_arm.py`로 검사한다. 빌더에 남은149 출력 이름은 역사적 이름이며 실제 VERSION은165다. `tools/test_nes_native_runtime165.py`는 고정 native 거래 캡처와 host GCC/ARM GCC를 받는다. [결과 JSON](../analysis/runtime165-verification.json)에 소스·ELF·원자료 해시가 있다. 완료한 private record/audit/archive는 재실행하거나 수정하지 않는다.

runtime165/arm02의 실제 RUN/오류/STOP/메뉴 복귀와 SysTick·라이브러리·일반 메뉴/GBC를 포함한 스택 여유를 먼저 확인한다. 필요하면 수명이 겹치지 않는 MCU 버퍼 공유로 해결하며 세이브 SRAM은 사용하지 않는다. 이어 실제 SNES ACK와 MCU 시간/오류 서비스의 최소 결합 시험만 수행하고, 선택 boundary165/map02와 쌍을 이룬 SMB3(J) 첫 레벨 시험판을 만든다. 변경 없는 FPGA 재배치·전체 ROM/부팅/A-B/044 반복은 하지 않는다. 60초는 tick 기준6000이며 장기 플레이/물리 리셋 로그는 AV 실기 확인 후 진행한다.

새 SD 패키지가 없으므로 사용자에게 현재165 빌드 파일의 설치를 요청하지 않는다. 조건부 IO/남은24 reset 동기화 경로/MTBF 한계도 이전 계약대로 남는다.
