# NES139 — 최초 ROM 오류 수집과 조기 복귀

138 실기에서 전체80KiB 적재·대조·복귀는 성공했지만 ROM 오류1(CPU 소비 시점에 유효 데이터 없음)이 발생했다.139는 **같은 실행에서 최초 실패의 주소와 대기 상태를 수집하는 시험 후보**다. 원인 수정이나 화면 성공을 주장하지 않는다. 정상044 독립 복원을 포함한 [실행 안내](../docs/nes-fault139-instructions.ko.md)를 따른다.

## 변경

- 실제 `nes_rom_early`의 fault 조건을 병렬 관측 출력으로 노출한다. 기존 요청 중재·cache·오류 우선순위·READ16/168MHz·95.232ns 읽기 창은 바꾸지 않았다.
- NES 클록의 같은 에지에서 observer가64비트 최초 context를 저장한다. 코어 STOP/reset이나 다음 오류로 덮어쓰지 않는다. 재구성 시 초기화한다. 원래70 명령은 활동/오류 요약, 새71/72는 읽기 전용 context다. 엄격한 후보 식별은5B/D6다.
- MCU가 ROM 오류를 관측하면 context를 읽고 표시 대기를 종료한다. RESET 재유지→STOP→base/menu 경로를 지킨다. 알려진 sticky ROM 오류가 STOP 뒤 유지되는 것은 정상 관측 계약이며 실행 실패로 기록한다.
- `run_first_error`와 `run_stop_error`를 분리하고 기존 `run_error`는 최초 실행 오류를 우선한다. 재선택 시 보고서 상태를 초기화한다. SD는 RUN 중 접근하지 않으며 안전 복귀 뒤 TXT에 기록한다.

## context schema1

64비트 값은 TXT `fault_context_hi`와 `fault_context_lo`를 결합한다. 비트63은0,62 busy,61 pending_ppu,60 rom_ready,59 rom_response,58 cpu_sample,57 ppu_sample,56 cpu_valid,55 ppu_valid,54:47 age,46:25 pending 주소,24:0 CPU 주소다. 주소는 CPU PC가 아닌 외부 메모리 매핑 주소다. age는 서비스의 NES 클록 카운터이며 NS 단위나 CPU 사이클 수가 아니다.

SPI 응답은 명령 다음7바이트다.71은 `D6,valid,context[63:24]`이고72는 `D6,valid,context[23:0],first_rom_error,1`이다. 같은 에지의 context는 최초 ROM 오류가 등록되는 시점의 pre-edge 입력/상태다. first_rom_error는 기존 sticky 오류 경로로 다음 에지에 수집된다.50ms 이후 MCU 조회에서는 둘 다 고정되어 있으며 두 페이지의 valid/ID/오류/schema를 검사한다. [해석 도구](../tools/read_nes_fault139.py)를 사용한다.

## 검증과 한계

- 실제 MCU/FatFs/보호/메뉴 경로20사례: 정상, ROM 오류 조기 복귀, STOP 뒤 카운터 변화, 이전 식별 거절, RESET/USB/SD/RDY/공통 고장, 잘못된 context ID/valid/원인 거절, 최초 오류와 STOP 오류 동시 발생을 검사한다. 실제 TXT를 읽어 새 필드와64비트 context를 대조한다. 외부 FPGA·SD·타이머는 호스트 모델이다.
- 실제 코어/reader/observer와70ns PSRAM 모델에서 정상 RUN 후 CPU deadline을 주입했다. 최초 에지 캡처,71/72 복원,STOP 이후 유지,후속 사건 덮어쓰기 방지 등46검사/5.718ms 통과. 실제138 오류 재현이나 완전한 화면 시험이 아니다.
- 선택 fit02:13701LE,915/963LAB,5184레지스터,50/56M9K,PLL1,122실핀/가상0. 같은 클록 setup+0.108ns/hold+0.179ns. raw setup−8.454ns는 전체 타이밍 통과가 아니다.
- 현재 배치363held-data쌍×3corner와17체인 검사 통과. 새 context로 CHR 설정의 관측 fanout이 늘었으며240설정쌍은 RUN 전 설정 안정 계약으로 분류한다.115 lifecycle쌍의 기존 reset/owner 계약도 유지한다. 새 false path를 추가하지 않았다.
- reset7494행 중 음수106행은 release 체인 비동기 입력이다. 나머지 최소+0.486ns. 외부 PSRAM 읽기 여유+2.478ns는 PCB 왕복2ns를 가정한 조건부 값이다. 보드 지연 실측·MTBF 승인은 아니다. SNES 합성 샘플 예산132.144ns/160ns도 실제65816 동시 실측이 아니다.
- ARM은 실제 호출·강한 NMI·호스트와 생산 소스 일치를 확인한다. 이전138 기능 영상·소비자 근거를 재사용하며, 같은 전체 적재·영상 검증을 반복하지 않았다. 새 배치이므로 실기 결과는 별도로 받아야 한다.

초기 준비 실패도 보존한다. fit01은 생성 파일명 혼동으로 준비 단계에서 중단됐고,host02/arm01은 후보 ID의 부분문자열 치환이 CRC 상수까지 바꿔 제외했다. 완전한 숫자 토큰 치환으로 고쳤다. 호스트/ARM 도구의 샌드박스 WinError623은 기존 호스트 실행으로 해결했으며 라이선스 문제가 아니다. 자세한 선택본·해시는 [메타](fault139-verification.json)에 기록한다.

다음은139 실기의 두 TXT·메뉴 복귀·044 복원 결과를 받아 CPU 요청 충돌/응답 지연을 구분하는 것이다. 결과 없이 같은 배치를 반복하거나 읽기 시간을 줄이지 않는다. 실제 화면이 안정된 다음 입력·SMB3(J) mapper4/384KiB·오디오로 진행한다. E1/E2·8µs/양클록 정지CE9µs 미보장·124격리·source-lock4·GBC/기존NES 고정 소스는 유지한다.
