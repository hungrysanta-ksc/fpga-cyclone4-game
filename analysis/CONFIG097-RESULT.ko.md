# NES097: 실제 구성 이미지와 메뉴 복구 함수 통합

동일086 fit03에서 ASM/CPF로 실제 CF86 파일을 만들고, 최종094 코드로 CF86·사용자 base 구성과 메뉴64KiB 분류/복사/보고 수명주기를 연결했다. 호스트176경우와 대조5개가 통과했다.

PR46 병합 `a005137040bf77e9d18a79971eb2c84adcbb2117`에서 시작했다. [검증 계약](../docs/nes-config097-contract.md), [메타데이터](config097-verification.json), [현재 인계](../cores/nes/HANDOFF.ko.md)를 함께 읽는다.

## 이번에 완료한 범위

| 항목 | 파일 바이트 | 해제/비교 바이트 | 출처 |
| --- | ---: | ---: | --- |
| CF86 진단 구성 | 219453 | 510856 | 동결086 fit03 복사본의 새 ASM/CPF |
| 기본 FPGA 구성 | 168440 | 214981 | 이미 받은 사용자 원본 그대로 |
| 메뉴 | 65536 | 65536 | 이미 받은 사용자 원본 그대로 |

새 RBF SHA는 `6d916f4235fcd0d4d725059f0a2f4317ea49e3637c04a53db0b8ced85cb220c1`, 압축 파일 SHA는 `6ebad40acadf9978b150391a786ecaf89a0e753989e088a10db8839c03ac4805`다. 이전 fit의 db와 incremental_db를 모두 manifest로 확인한 뒤 별도 ASCII 디렉터리에 복사했다. 원본은 변경하지 않았고 ASM/CPF는25.1std.0 Build1129에서 오류·경고0으로 끝났다. 새 map/fit/STA는 수행하지 않았다.

현재 NES decoder에 맞는071 encoder를 사용해 **추가 EOF 표식을 넣지 않았다.** 관측용089 decoder가 마지막 표식을 버리는 방식과 구분한다. 새 진단 구성은 원본 RBF의 모든 바이트와 일치한다. base는 수신한 압축 파일을 현재 decoder로 해제한 전체214981바이트를 비교했으며, 기존 padding을 보존했다. base 파일과 공개 HDL 소스의 동일성을 새로 증명한 것은 아니다.

## 호스트 통합 결과

80KiB/FAT16/SDHC와96KiB/FAT32/SDSC에서 각각88경우, 총176경우다. 정상·tick wrap·READY 지연 성공6경우와 고장 주입170경우를 포함한다. SD132경우는 구성/기본 구성/메뉴 분류/메뉴 복사/보고 단계의 첫·중간·마지막 표본이다. R1 CRC·응답 timeout은 두 명령, 읽기 CRC·데이터 시작 timeout은 CMD17, 쓰기 end-bit·busy는 CMD24에 맞춰 주입했다. 모든 명령 위치의 전수 검사는 아니다.

최종094 ARM과 같은 실제 FatFS/native20함수/checked 구성/READY/진단 세션 코드를 실행했다. 실제 메뉴 분류와64KiB 복사·모든 SRAM 바이트 재읽기 비교, prepared/released 및 TXT 저장 함수를 같은 흐름으로 연결했다. 정상 각 경우에서 구성2회, 전체 ROM 비교·ACK·FINISH·STOP, 메뉴256쓰기, 보고 native5쓰기, 모델 RESET 해제·IRQ 복구를 확인했다. 보고 파일의 `verified=1`, `base_restored=1`, `PREPARED_RESET_HELD`를 확인했다. 해제 후 `RETURN_READY_RESET_RELEASED` 상태는 원래 코드대로 UART 출력이며 SD에 덮어쓰지 않는다.

정상 제품 구간의 모델 SD 명령은80KiB1532/96KiB1634개다. 제품 수명주기 종료 후 시험 코드가 수행하는 별도 TXT 재읽기3명령은 이 수에서 제외했다. 보고 재읽기 성공을 실제 제품 기능이나 실기 결과로 표현하지 않는다. 모델 시간은11587/13868tick(100Hz)이며 MCU 실측/WCET가 아니다.

오류 때 추가 SD 명령·클록·ROM SPI·구성 출력을 차단하고 RESET/IRQ 보호 및 재진입 거부를 검사했다. CF86 세션이 정상 종료된 뒤 메뉴에서 생긴 오류는 CF86 FAILED가 아니라 공유 메뉴/SD 오류와 pending 상태로 보호한다. `menu_ok=false`는 공유 IO 오류와 구분한다. CRC 검사·RLE 길이·메뉴 CRC·SRAM 비교·보고 쓰기 권한을 바꾼 대조5개는 각각 예상 assertion에서 실패했다.

## 남은 범위

**실제 구성 파일 생성 및 하위 코드·메뉴 함수 통합 목표는 달성했다. 전체 main 복귀 검증은 부분 완료다.** 메뉴 순서는 호스트가 연결했고 SRAM·구성 핀·SPI 응답·SD 핀/CRC primitive·시간은 모델이다. memory.c에서는 active 분류 블록만 추출했으며 전체 `load_rom()`과 `main()`을 실행하지 않았다. RESET 해제 후 고장 재hold도 호스트 시나리오이므로 실제 main 조건문의 실행 증거가 아니다. SNES 메뉴 화면은 렌더링하지 않았다.

현재097 실제 파일을 그대로 사용해 main pending-menu의 RTC·설정·상태·CIC·SRAM/SPI/UART/타이머 호출과 RESET 해제 전후 오류 처리를 연결한다. 그 뒤 동일 최종 ARM/FPGA/정확한044 복원 쌍과 외부 IO·공통 클록 고장 조건을 확정한다. 실제 main의 관측·종료 경계가 확인되고 외부 IO 및 두 클록 동시 정지의 승인 범위가 정리되기 전에는 이 구성 파일을 실기 설치 패키지로 전달하지 않는다.094 ARM은 기존180928바이트/SHA `70aa72fa1a70a90d501bac386ff4d159f46a12a48e15f0880c95f6fd78d208da`이며 새 ARM/생산 C/RTL/Questa/실기 시험은 없다.095의 조건부 RTL 검증과097 모델 시간을 같은 증거로 합치지 않는다.

084 저장·화면·044복원·메뉴/GBC,092 클록 활동/TXT/복원 성공은 유지한다. 준비도4완료/7부분/1미완료, 설치 승인false, SMB3(J) mapper4/384KiB 첫 게임 목표도 유지한다.

비공개 동결 `probes/nes-config097/evidence/` 1025파일, manifest `7b60fe8e4240f46073d12a16fc2a32bb9fb807c25346d7a3f65cf0fd5e4f3e40`. normal01의 종료 후 legacy readback stub 실패, suite02의 CMD24에 읽기 CRC를 주입한 모델 기대 오류와 정상/대조 원시 로그를 보존했다. 생산 코드 오류로 오인하지 않는다. 공개 clone만으로 재현 가능한 증거라고 주장하지 않는다.
