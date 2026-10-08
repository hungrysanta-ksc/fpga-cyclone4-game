# 082 보고서 플랫폼 단일 실행 검증

081의 실제 SD 초기화부터 FatFS/native SD 저장·재읽기와 최종 화면 문구까지 **하나의 호스트 실행으로 연결하는 목표를 달성했다.** 정상·오류 주입 667검사와 인과 대조 2개를 통과했다. 펌웨어 생산 소스는 변경하지 않았다. 실기 성공, TV 가독성, 설치 승인을 뜻하지 않는다.

## 기준과 실행 범위

PR32가 master `648d399865e6746397037ecb3bbb4e6f5c9c51fc`에 병합됐고 원래 head의 도달 관계를 확인했다. 여기서 `codex/nes-report-session-082`를 시작했다. PR31은 닫힌 대체 이전 기록이며 다시 병합할 대상이 아니다.

고정081 최종 ARM02 소스에서 실제 `report_session081`, 초기화·상태 연결, `file_init`, 전체 FatFS, native CMD17/24 함수, 080 boot/decoder, 보고서 writer와 079 checkpoint를 가져왔다. 같은 세션에서 초기화와 첫 mount를 거쳐 3072바이트 생성·256바이트 분할쓰기·sync·close·재열기·크기/전체 바이트 비교·최종 close·terminal까지 실행한다. 단계 사이에 fault나 초기화 상태를 지우지 않는다.

081의 mount 전용 sector stub과 080의 writer stub은 이번 시험에 사용하지 않는다. 실제 native 함수의 GPIO를 카드 모델이 해석한다. slow→fast 모델 전환도 드라이버의 `disk_state`가 아니라 wire에서 해독한 CMD16 응답 종료 후 다음 명령에서 일어난다. 카드 주소 해석은 독립적인 SDSC/SDHC 설정을 사용한다.

모형 경계는 GPIO/카드 저장소, ARM CRC 명령의 호스트 대체, 시간, FPGA serial/SRAM/RESET/USB다. mini 153544바이트·boot ROM 65535바이트는 기존 RLE decoder와 전 바이트 대조한다. 마지막 FF 버림과 길이를 바꾸지 않는다. 화면은 SRAM 문자열/RESET 실행 기회만 확인하며 SNES PPU나 TV 픽셀을 실행하지 않는다. 전체 MCU clock/GPIO/timer/CIC startup은 이 시험 밖이다.

## 결과

| 정상 조합 | 초기화 명령 | native CMD17 | native CMD24 | SRAM 접근 | 단계 표시 |
| --- | ---: | ---: | ---: | ---: | ---: |
| FAT16 / SDSC | 17 | 11 | 10 | 587 | 7 |
| FAT16 / SDHC | 17 | 11 | 10 | 587 | 7 |
| FAT32 / SDSC | 17 | 12 | 10 | 587 | 7 |
| FAT32 / SDHC | 17 | 12 | 10 | 587 | 7 |

최초 CMD17은 stage1의 실제 mount다. 정상은 stage2–8에서 각각 500ms 렌더링 기회를 모델링하고 stage9에서 `TXT SAVED + READBACK OK`, `/HW081000.TXT`, `Save code: 0`을 쓴 뒤 RESET을 해제한다. write 권한은 이미 회수됐고 USB 제외는 계속된다. 실제 writer의 readback 외에도 카드에 반영된 디렉터리/FAT 체인/3072바이트를 독립적으로 검사했다. 이 마지막 검사는 호스트의 저장소 검사이며, terminal 이후 펌웨어 IO를 추가한 것이 아니다.

667검사의 구성은 정상4, FAT16/32 모든43 native 응답 위치 오류, 6종 native 고장, 정상 CRC를 가진 readback 변조1, 모든587 SRAM 접근 오류, checkpoint timer7, 부팅 이후12 화면 readback 변조, 누적 표시 예산1, tick wrap1, 초기화 고장3, 쓰기금지1, 카드없음1이다. 첫 공유 오류 이후 RESET/USB 보호·쓰기권한 회수와 재진입의 추가 SD/SRAM IO 금지를 확인했다. 고장 주입 로그의 CRC mismatch/CMD17 timeout은 예상한 음성 시험 출력이다.

readback 내용 불일치와 카드 쓰기금지는 공유 IO 고장과 구분한다. 내용만 틀리면 실제 writer가 code7로 반환하고 정상적인 실패 문구를 보여 준다. 공유 SD/SPI/timer 고장은 추가 화면 IO 없이 보호 종료한다. 파일 크기 또는 0바이트만으로 원인을 판정할 수 없다.

인과 대조는 실제 writer의 `memcmp` 제거 시 `TXT SAVE FAILED` 검사에서, 실제 checkpoint의 RESET 재유지 제거 시 첫 정상 세션 검사에서 각각 실패했다. 변경된 것은 대조용 사본뿐이다.

## 증거와 재현

최종 normal-04 / no-readback-compare-04 / no-reset-rehold-04. 동결 302파일 manifest SHA `14023cb52e2239380743a891a2795d73e32bccab8657ce343d8b8df1f2692112`. 메타데이터는 [report-session082-verification.json](report-session082-verification.json), 검증기는 [verify_nes_report082.py](../tools/verify_nes_report082.py)다. 081의 기존 3374파일 증거 검증도 통과했다.

첫 normal-01의 호스트 `file_status` 헤더 누락, normal-02의 논리 code7을 공유 고장으로 오인한 테스트 기대 오류, 이전 normal-03의 633검사 결과를 함께 보존했다. 생산 코드 결함으로 분류하지 않는다. 완료한 동결 스크립트 재실행과 044–082 archive 수정은 금지한다.

`tools/test_nes_report_session082.py --evidence081 <고정081/evidence> --gcc <host-gcc> --out <새폴더>`를 사용한다. `--mode no-readback-compare`와 `--mode no-reset-rehold`도 각각 새 폴더에서 실행한다. 검증기는 `--evidence <082/evidence> --evidence081 <081/evidence>`를 받는다. 개인 고정 입력이 필요하므로 공개 clone만으로 독립 재현된다고 주장하지 않는다.

후보는 여전히 **SDREPORT081**, 132320바이트, SHA `5931eec90956022104b8aa42851525b52b3f3a805d50a48ca71c33357357649d`다. 해시가 같은 081 ARM 빌드/호출 증거를 재사용하며 새 ARM 실행·RTL·Questa·fit·ASM·실기·설치 패키지는 없다. 082라는 별도 펌웨어를 만들지 않았다.

## 남은 일과 다음 목표

P1은 부분 완료이고 준비도는 4완료/7부분/1미완료를 유지한다. 단일 플랫폼 실행의 공백은 닫았지만 사용자 0바이트 TXT의 원인은 여전히 미확정이다.

다음은 초기화/mini 실패의 외부 관측, 총 시간·결과 해석표, 정상044 설치·복원표를 완성해 보고서 전용 P3를 판단하는 것이다. 현재 순서는 SD 초기화 뒤 mini이므로 초기 SD 고장은 검은 화면일 수 있다. mini를 먼저 준비해 SD 초기화 전 표식을 남기는 순서를 검토하되 RESET/USB/첫 오류 보호를 풀거나 fault 이후 출력하지 않는다. 순서를 바꾸면 바뀐 생산 함수와 최종 ARM을 다시 검증한다. 500ms의 모델 대기는 실물 가독성 보증이 아니다.

CF68 PSRAM 진단의 외부 IO/P2·동일 쌍/P3, 전체 NES 4LAB 여유·영상/입력/오디오/P5/P6는 별도다. 같은 파일·LED·분해·PC USB·부품 질문을 되풀이하지 않는다.
