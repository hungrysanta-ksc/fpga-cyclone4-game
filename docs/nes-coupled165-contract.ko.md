# NES165 RUN 버퍼 수명·실제 SNES 결합·실기 시험판

## 목표와 결과

NES165 SMB3 실기 시험판을 준비했다. 새 영상 경로의 MCU→실제 SNES 표시 ACK 결합을 통과했고, RUN 전용 버퍼로 메뉴·GBC의 RAM 여유를 회복했다. 전체 ARM 링크와 RUN/IRQ 스택 검토·기존 FPGA 배치의 ASM을 완료했다. 화면 속도·사운드·메뉴 복귀의 새 실기 결과는 아직 미확인이다.

이전 [runtime165](nes-runtime165-contract.ko.md)의 MCU 연결을 유지하면서 실기 시험 전 남은 RAM·수신 경계를 정리했다. FPGA는 [boundary165/map02](nes-boundary165-contract.ko.md)를 그대로 쓴다. 새 합성/배치/Questa는 없으며 ASM/CPF만 수행했다. 실기 절차는 [NES165 사용 안내](nes-game165-instructions.ko.md)에 있다.

## 메모리 수명과 스택

이전 arm02는 receiver18064B와 video15888B를 영구 할당해서 메뉴/GBC에도 잔여RAM5000B만 남겼다. 새 arm01은 `noinline native_session165` 안의 자동 workspace로 바꾼다. 종료 후 그 함수의 스택 프레임을 반환하고 receiver/video/io 포인터를NULL로 만든 다음 STOP·로그·메뉴로 진행한다. 종료 로그는 별도4864B 스택을 다시 사용하지만33952B workspace와 수명이 겹치지 않는다. 결과 스칼라는 runtime context에 먼저 복사한다. 별도 카트리지 SRAM/세이브 영역은 사용하지 않는다.

|항목|새 전체 ARM 결과|
|---|---:|
|firmware.stm|196028B|
|정적 RAM(.ahbram 포함)|26472 /65424B|
|RUN 밖의 스택·힙 잔여|38952B|
|버퍼 포함 보수적 RUN 호출 경로|37320B|
|SysTick/TIM2/NMI 소프트웨어+확장 예외 프레임 예약|508B|
|위 합계 이후 잔여|1124B|

실제 ELF와 `.su`의86개 도달 함수를 검토했다. 함수 포인터는 실제 binding을 명시하고, 중복된 `transfer`는 guard를 호출하는 runtime 소유자로 구분한다. printf·UART의 오류 경로와 UART newline→CR의1회 재귀도 포함한다. 라이브러리/어셈블리의 명시적 stack 사용은 코드 본문 SHA로 고정한다. 시간 실패 시 UART 대기는 bounded이고, NMI는8B와 기존0B/no-call fail-stop이다.

SysTick은 SD 상태 printf까지 176B, TIM2는 0B, NMI는 8B다. 각 예외에 FP 확장 104B와 정렬 4B를 보수적으로 더한다. USB IRQ는 진입 전에 차단한다. STM32 UART는 polling이며 SD IRQ는 활성화하지 않는다. malloc/sbrk의 실제 링크 심볼도 없다. 이 숫자는 검토된 빌드·binding·활성 IRQ 조건의 상한이며, 실제 stack high-water 계측이나 모든 기존 메뉴/GBC 함수의 형식 증명은 아니다. 메뉴/GBC에서는 영구 33952B 할당 자체를 제거했다. 다음 코드 변경 시 같은 상한을 그대로 인용하지 말고 새 ELF를 다시 검사한다.

## 실제 수신 코드 결합

test05는 실제 C runtime/receiver/converter/sink/CRC가 만든 45패킷을 Mesen의 실제 65816 수신 프로그램에 넘긴다. **ACK는 SNES가 직접 쓴 12바이트를 돌려받는다.** MCU가 응답 성공을 가정해 주입하지 않는다. native 입력은 기존 RTL 캡처 191거래, 패킷 버스는 파일 모델이다. 실제 STM32 명령 실행·전기적 SPI·FPGA/게임 실시간 동작까지 결합한 시험은 아니다.

- 정상: 실제 ACK 45개, 프레임 1개 consumed, 화면 256×239의 61184픽셀이 기준과 일치했다.
- SEAL ACK 반환 직후 시간 만료: 실제 화면은 표시됐지만 frames=0/result=1로 남는다. 다음 native 데이터를 소비하지 않고 재시도하지 않는다. 따라서 frames=0만으로 화면이 전혀 안 나왔다고 단정하지 않는다.
- 두 경우 모두 SPC A9와 패드 DOWN 표본 48회, visible 구간 DMA 금지 및 첫 표시 후 blank 없음이 기존 Lua 검사로 확인됐다. 실기 사운드나 입력 유지 판정은 아니다.

SNES ROM의 SHA는 FPGA에 들어 있는 4096B `sink-program.hex`와 같다. 이전 runtime의 10조건/잘못된 limit 시험과 별도로 수행한 실제 sink의 서로 다른 두 프레임/STOP 시험은 재사용했다. 새 시험 횟수에 포함하지 않는다.

실행 환경 실패도 보존했다. test01은 Mesen DLL 경로, test02는 임시 portable 폴더의 동봉 .NET 누락, test03은 한글 경로의 Lua 문자열/파일 IO 문제다. ASCII 경로와 동봉 runtime으로 해결했다. test04는 같은 결합을 통과했고, ASCII 사전 검사를 추가한 최종 도구는 test05다. 사용자 Mesen 설정은 변경하지 않았다. 이 실패는 FPGA·라이선스 문제가 아니다.

## 패키지와 남은 실기 확인

검증된 map02의 전체 복사본에서 Quartus ASM/CPF와 기존 압축 형식의 roundtrip을 통과했다. 원래 61개 입력·배치 보고서·원본 DB는 바꾸지 않았다. firmware SHA는 `0093c48e10298da115c31ce9be40d5d49bf1b08fcf111ea49e2e957b43873fbb`, FPGA SHA는 `ca2b3bfefb0af3050d3434d9ad7215eadcfb4554828453e01bb2cd4ccbd35fc6`다.

private ZIP `NES165-SMB3-NATIVE-VIDEO.zip`은 새 펌웨어/FPGA, 사용자 제공 SMB3(J), 0B 표식, 기존 base/menu와 164 원본 복원 세트를 포함한다. ROM·바이너리는 Git에 올리지 않는다. 기존 164 패키지와 복원 파일은 바이트 단위로 보존했다. SD에는 직접 쓰지 않았다. ZIP SHA는 `702ca2f77e2ca6ff29846ba1b2b3877f90afb8f980efbe53da9684c13d587787`다.

기존 ROM 적재 시간은 최적화하지 않았다. 실행 구간은 6000tick이며 표시 준비/ACK 시간이 포함된다. STOP·메뉴 복귀와 최종 SD 로그는 기존 경로를 재사용했고, 이번 실기 성공은 아직 없다. 전체 IO/MTBF·남은 24개 동기화 raw 경로·클록 정지 한계는 조건부로 남겨둔다. 실기 시험 준비 완료를 완전한 타이밍/60fps/코어 호환성 승인으로 읽지 않는다.

## 재현과 다음 작업

`nes_runlease165.py`로 164 증거에서 새 소스를 준비하고 기존 ARM 빌더로 링크한다. `check_nes_runlease165.py`는 리뷰 JSON과 ELF/스택 파일을 검사한다. `test_nes_coupled165.py`에는 고정 native 캡처·기준 RGB와 portable Mesen, 새 ASCII 출력 폴더를 준다. `assemble_nes_native165.py`는 고정 boundary165 증거를 복사해 ASM/CPF만 실행한다. `release_nes_native165.py`는 선택 결과·클라이언트 일치·164 복원·압축·ZIP을 검사한 뒤 패키지를 만든다. [결과 JSON](../analysis/coupled165-verification.json)에 소스/원자료/패키지 해시가 있다. 완료한 record/audit/archive를 다시 실행하거나 수정하지 않는다.

새 NES165-SMB3-NATIVE-VIDEO 시험판으로 제목→월드맵→첫 레벨 이동·점프·사운드·화면 속도와 메뉴 복귀를 확인한다. nes-progress-165.txt/nes-game-last-165.txt 및20~30초 영상을 받기 전에는 또 다른 범용 진단이나 무변경 FPGA FIT/전체 부팅을 반복하지 않는다. 실패하면 최초native_result/receiver/sink/video/ROM 오류에 따라 실제 경로만 수정한다. AV가 확인되면 장기 플레이와 오류/물리 리셋 로그, 입력 유지 품질 순서로 진행한다. 044 복원 시험은 반복하지 않고 필요시 동봉164로 복원한다.

공개 검사에서 리뷰 JSON의 CRLF→LF 변환에 따른 해시 차이를 발견했다. 기존 CRLF 원본과 armcheck01/release01은 보존했고, JSON 값이 동일한 LF 공개본으로 armcheck02/release02를 실행했다. ELF·펌웨어·FPGA·ZIP 바이트는 모두 동일하다. 초기 record와 증거 manifest는 수정하지 않았다.
