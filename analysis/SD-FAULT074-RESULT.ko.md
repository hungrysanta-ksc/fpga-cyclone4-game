# SD 저장 중 검은 화면의 원인 관측 — 074

## 작업 목표

사용자는073 실행 뒤 HW004000.TXT가0바이트이고 화면이 없었다고 보고했다. 파일 원본/영상은 이번에 받지 않았다. 기존073의 호스트 저장 성공을 실제 카드 성공으로 확대할 수 없다. 공유 오류 뒤 화면을 갱신하지 않는 보호는 유지하면서 다음 실기에서 최초 오류 종류와 중단 단계를 회수한다.

## 작업 내용

0바이트 파일은 디렉터리 생성이 반영되고 내용/메타데이터 완료 이전에 중단된 상황과 부합하지만, 정확히 어떤 명령에서 실패했는지 증명하지 않는다.073에는 native fault가 나면 RESET/USB를 유지하고 화면 출력 전에 차단하는 경로가 있다. SD 명령 응답·CRC·busy·파일시스템 예산 등은 현재 관측으로 구분되지 않는다.

074는073을 별도 디렉터리에 materialize하고 collector 식별자/출력 파일을 SDINFO074-BASE069/HW005nnn으로 바꾼다. writer에 FatFS 호출 **이전** 단계 표식을 넣고 전용 nes_diag_platform 구현을 바꾼다. 실제 FatFS/native SD/guard/runtime11개 입력 해시는073과 같다. 기존072/073 공개 소스와 동결 자료, GBC152/기존NES334는 보존한다. CMD24,CRC 샘플,예산,재시도 정책을 추측으로 변경하지 않았다.

처음 공유 오류가 기록될 때 오류 번호와 당시 단계를 한 번 고정한다. MCU GPIO LED만으로 시작 표식→Read 오류 횟수→Write 단계 횟수를 반복한다. 관측 callback에서 UART 출력도 제거해 오류 기록 자체가 UART 대기에 의존하지 않게 했다. 차단 루프는 RESET/USB를 유지하며 SD/SPI 접근이나 RESET 해제가 없다. SysTick LED 소유권과 동작 종료 시 LED 상태 복원을 유지한다. SysTick/CPU 정지까지 감당하는 독립 감시로 주장하지 않는다. 초기 legacy 부팅은 범위 밖이다.

최종 실제 소스로 수집52/저장23/플랫폼6/TXT29 검사가 통과했다. 실제 런타임과 LED 구현을 연결해9오류×9단계×tick wrap2=162경우의 펄스 수·시작 표식·주기·최초원인 보존·RESET/USB·상태복원을 확인했다. 최초 오류에서 기록하지 않고 BLOCKED까지 미루는 변형은 잘못된 단계 펄스 assertion에서 실패한다. 실제 FatFS/쓰기 가드의 FAT16/FAT32 통합40개도 새 writer로 통과했다. **카드 명령/응답/전송은 여전히 RAM 모형이며 물리 SD 파형 검증은 아니다.**

별도 ARM 전체 링크에서 main→sdinv_run, report 권한 true/false2호출, called write_report의 단계7호출, 실제 SysTick→led_error→nes_diag_led_tick와 보호 차단을 확인했다. firmware133332바이트 SHA `031725700f3e9c58abc1001f9d53cdbe89a1587e5e552a77951434d136953271`. 펌웨어 단일 파일 패키지와 대응 소스·[실행 안내](../docs/SDINFO074-RUN.ko.md)를 준비했다. 새 RTL/FPGA/fit/Questa/ASM은 없다.

동결1519파일 manifest `2be1006b6365414d2246e1dc38655126e3f2b00405871422f1f7a9626d37165b`. 첫 audit의 objdump 한국어 경로 UTF8 해석 실패와 두 번째 audit의 helper 호출 위치 가정을 보존한다. 공개 verifier만 수정하고 같은 동결 ELF에서 write_report disassembly를 별도 audit-addendum으로 추가했다. 원시 archive·패키지·대응소스는 바꾸지 않았다. 따라서 대응 소스 ZIP의 초기 verifier 대신 현재 공개 verifier와 명시된 addendum으로 검사한다.074 최종 audit와 과거073 audit 모두 통과했다.

## 작업 결과

**공유 오류를 보호 상태에서 외부 관측할 경로와 재시험본 준비는 달성했다.073 저장 실패의 근본 원인 규명·수정과074 실기 성공은 미달성이다.** LED 출력도 실제 사용자 관측은 아직 없다. 새 실행의 LED60초 영상과 HW005nnn.TXT/파일크기를 받아 오류 분류·최초 단계를 확정하는 것이 다음 목표다. LED가 외부에서 안 보이면 추가 분해를 요구하지 않고 별도 관측 방법을 검토한다.

Ready/Read/Write 영상에서 기록된 오류에 맞춰 실제 하위 송수신이나 예산을 좁혀 수정한다. 기존 HWINFO002의 성공한 legacy 저장과073 CMD24를 차등 조사하되, legacy 무제한 대기·공유 오류 이후 SD 재접근으로 돌아가지 않는다. 실제 카드의 response/data/CRC/busy 경계를 검사하지 않은 RAM 전송 모형을 그 근거로 인용하지 않는다. 원본 사본 firmware.before-sdinfo072.stm과 독립 백업을 그대로 유지한다.

NES 쌍071/MCU069/FPGA068, 준비도5완료6부분1미완료와 설치 보류는 변함없다. 실물 TXT 수집 뒤 실제 메뉴 분류·독립 복원·외부 전기/클록 조건은 별도 완료해야 한다.
