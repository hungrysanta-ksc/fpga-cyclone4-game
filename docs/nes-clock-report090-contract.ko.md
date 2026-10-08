# 클록 관측·TXT 통합090 계약

090는 단일 제품 함수 `report_session090()`에서 초기 mini → 화면 표식 → CF87 구성089 → 관측088 → RAM 보고서 → mini 복귀 → 실제081 SD 초기화/FatFS →084 연속 공간 검색 → 저장/닫기/재읽기/비교 → 최종 화면을 실행한다. main에 연결한 전체 STM32F401 펌웨어를 링크했다. 실기 실행·배포 패키지는 아직 아니다.

## 결과와 화면

`/HW090nnn.TXT`에 `CLOCK ACTIVE`, `CLOCK ABSENT`, `CLOCK UNSTABLE`, `NO CLOCK PROGRESS` 중 하나와 initial/sample1/sample2의 원시16바이트, 순번·count·window·divisor·flags·시각·시도 횟수를 기록한다. ACTIVE는 클록 활동 관측이며 주파수나 전기 타이밍 승인으로 해석하지 않는다. CLKIN 8MHz는 기존 설계 가정이다. count와16분주/800만 cycle을 이용한 실제 주파수 환산은 CLKIN 실측 근거 전까지 승인하지 않는다. NO_PROGRESS는 정상/부재 판정을 할 수 없다는 결과다. 첫 안정 snapshot을 얻지 못하면 initial도0일 수 있다.

문자열은3072바이트 RAM 한도에서 실제 길이만 저장한다. 과거084 반복 알파벳은 포함하지 않는다. 기존084의3칸 여백·최대26자 화면 규칙을 재사용하며 결과는10행, 파일명11행, 저장 결과8행, 코드13행이다. STEP1A 관측→1B 초기화→1C mount→1D 공간 검색→기존2–8 쓰기 단계다. 관측 중에는 RESET을 유지하므로 화면 갱신을 약속하지 않는다. TXT 파일 존재만으로 쓰기 완료를 판단하지 않는다. `TXT SAVED + READBACK OK`, Save code0와 전달받은 TXT를 함께 확인한다.

## 처리 예산과 오류

초기 부팅부터 공간 검색까지 기존60초/100만 회 scope 하나를 쓴다. writer의 명시된 진입에서만 기존10초/10000회 쓰기 구간으로 전환하며, checkpoint마다 예산을 다시 시작하지 않는다. 오류 뒤 scope/fault 초기화·후속 SD/SRAM·재구성·재시도를 하지 않는다. 관측 오류는 NO_PROGRESS로 바꿔 저장하지 않는다. 건강한 IO에서 재읽기 내용 불일치이면 Save code7로 표시한다. shared fault가 발생하면 TXT/최종 화면을 보장하지 않는다.

| 호스트 세션 | writer 진입 전 공유 검사 | writer 검사 |
| --- | ---: | ---: |
| ACTIVE/ABSENT/UNSTABLE, FAT16 | 739341 | 60 |
| 같은 결과, FAT32 | 739342 | 60 |
| NO_PROGRESS, FAT16 | 931395 | 60 |
| NO_PROGRESS, FAT32 | 931396 | 60 |
| NO_PROGRESS, FAT32 cluster3–11999 사용 중 | 955390 | 60 |

마지막 경우 잔여44610회는 해당 모델의 여유다. 모든 SD 파편화/용량/지연을 보증하지 않는다. 모델 시간은 정상11.32초, NO_PROGRESS12.82초이며 실제 ARM CRC/IRQ/GPIO/SD/TV 소요 시간은 아니다. SysTick까지 멈추는 기존089 반례는 여전히 유효하다. 공유 한도에서 차단하며 저장을 약속하지 않는다.

## 검증 범위

최종 host02는94검사다. 네 관측 결과×FAT16/32×SDSC/SDHC16경로, dense FAT32, 정상 두 FAT 세션의 모든 native 명령 위치, 선택한 SRAM 실패 위치와 마지막11위치, checkpoint·표식 지연 실패, 잘못된 CF87응답/구성 상태/DONE/지연, 카드 제거/초기 응답 오류, 재읽기 불일치/쓰기 금지, tick wrap 및 formatter의 모든 부족한 버퍼 크기와 경계 canary를 검사한다. 모든 하드웨어 실패를 전수 검사했다는 의미가 아니다.

호스트는 실제 production090/089/088 C, 기존 실제 SD init·FatFS·native CMD17/24·writer·mini/decoder·runtime을 사용한다. 핀/카드/CRC assembly primitive/시간/SRAM은 모델이다. menu-return C는 보고서에서 쓰는 정확한 runtime prefix를 추출했으며 사용하지 않는 메뉴 복사 함수는 제외한다. 구성 바이트510856개는 RBF와 비교했다. 이번090에서 모든 구성 bit나 RTL을 새로 재생하지 않았으며089의 별도 bit 검증을 구분한다. 네 인과 대조는 reader 생략, reader fault 지우기, readback 비교 제거, RESET rehold 누락을 검출한다. 별도 TXT parser는16파일의 raw/decoded 값을 비교하고4변조를 거부하며 initial 미획득을 처리한다.

전체 ARM196248바이트의 main 호출, 플랫폼 순서, 두 mini 호출, 네 표식, 일곱 writer checkpoint, strong mount bridge를 disassembly에서 검사했다.11개 실행 소스는 호스트와 byte-identical이고 menu runtime prefix도 일치한다.13개 기존 native 입력은084와 동일하다. 고정089 RLE59700바이트가 firmware에 정확히 한 번 포함됐으며 새 ASM/fit/STA/Questa는 없다. ARM 명령을 실기에서 실행한 검증은 아니다.

## 다음 완료 조건

1. 새 GPIO 모델은 SPI MODER/CR1의 물리 핀 전환을 전부 검증하지 않는다. CF87 관측 종료 후 mini 재구성에서 실제 STM32 핀 설정/CS/SPI idle/RESET 소유권을 이어서 대조하고 필요한 오류 대조를 추가한다. 같은084 부팅 함수를 썼다는 이유만으로 CF87 왕복 실기 승인을 선언하지 않는다.
2. 이196248바이트 firmware와 고정 CF87/mini의 정확한 해시, 원본044 복원 파일, 복사 위치·화면별 대기/실패 대응·전원 차단·수거 TXT 절차를 묶은 report-only trial/source 패키지를 새 경로에 만들고 검증한다. 완료 전 SD 설치 안내나 실기 준비 완료로 표현하지 않는다.
3. 사용자의 새090계열 관측 TXT/화면으로 RESET-held reference availability를 판단한다.084 저장/복원/menu/GBC 통과는 이미 확정됐으므로 같은 저장시험을 다시 요청하지 않는다. 이후 CF86 외부 메모리/async assertion/common-cause 정책과 최신MCU/전체80·96KiB 세션을 별도로 진행한다.

구현·시험 재현 도구는 `nes_clock_report090_prepare.py`, 기존 `build_nes_report079_arm.ps1`, `test_nes_clock_session090.py`, `check_nes_clock_report090_arm.py`, `test_nes_clock_text090.py`, `verify_nes_clock_report090.py`다. 각 작업은 새로운 출력 폴더를 사용한다. 원본084/089 및 완료090 동결 근거를 변경하지 않는다.
