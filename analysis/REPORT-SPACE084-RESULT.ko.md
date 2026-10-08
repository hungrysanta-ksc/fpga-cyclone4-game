# SDREPORT084: 사용 중인 FAT 탐색과 화면 여백 수정

083 실기에서1A→1B→2→3 화면과 STEP3 고정, 사용자 보고 HW083000.TXT0바이트 및 좌우 글자 잘림을 확인했다. 사용 중인 FAT 앞부분을 탐색하다 writer10000poll을 소진하는083 조건을 재현했다. 084는 파일 생성 전 읽기 전용 공간 탐색·1C 표식·좌우 여백을 추가했고, 통합809·timer5·인과대조5·ARM·시험/044복원 ZIP 검증을 통과했다. 실제 SD 원인과084 저장·가독성·044복원/메뉴/GBC는 미확인이다. 준비도4완료7부분1미완료, CF68/NES 설치 미승인을 유지한다.

## 실기 입력과 재현

사용자 영상은50.37초이며 추출한8초 프레임은STEP2,10·40·49초 프레임은STEP3다. 첨부 사진은1A/1B/2/3과 왼쪽 글자 잘림을 보인다. 전체 영상의 모든 프레임을 판독했다고 주장하지 않는다. HW083000.TXT0바이트는 사용자 보고이며 TXT 원본 바이트는 이번에 받지 않았다. 영상 SHA256 `b5217971a2d552fca018cdb01ce206d8a370e7a7c5808508a282201ec753f8e4`. 정상044 복원·메뉴/GBC의 이번 실행 결과는 아직 없다.

고정083의 실제FatFS/native/부팅/저장 코드를 유지하고 FAT32클러스터3–11999를 사용 중으로 만든 모형에서 `ok=0 stage=3 fault=16 commands=44 writes=1 bytes=0 ticks=300`을 재현했다. 디렉터리 생성 쓰기1회 후 데이터 쓰기 전에 실패한다. get_fat와move_window의 cache-hit도 poll을 차감하므로5000개 안팎의 할당 후보 검색으로 writer10000poll이 먼저 소진될 수 있다. ticks300은 화면 대기의 모형값이며 실물10초를 설명하는 측정값이 아니다. 사용자의 실제 FAT/hint/SD 응답을 회수한 것은 아니므로 실기 원인은 확정하지 않는다.

## 변경

- 081 첫mount 뒤 `STEP 1C FIND SPACE`를1초 표시하고 기존60초/100만poll 안에서 실제 get_fat를 통해 읽기 전용 탐색한다. 파일은 아직 만들지 않고 write permission도 열지 않는다. 3072바이트에 필요한 연속클러스터와 여유1개를 찾은 뒤 RAM last_clust만 바꾼다. 예약/FAT쓰기/free-count 조작은 없다.
- 기존 writer10초/10000poll·7개checkpoint·최초fault보존·post-fault추가IO금지·RESET/USB 보호·nativeSD/CRC/타이머를 유지했다. 기본mini/RTL/GBC는 변경하지 않았다.
- 공통33바이트 줄 포맷은32타일 안에서 문구를 중앙 배치한다. 최대26글자·양쪽최소3공백·마지막NUL을 검사하고 긴문구를 조용히 자르지 않는다. 안내는 `POWER OFF / RESTORE 044`로 줄였다. 모든 SRAM 화면 쓰기에 여백 검사가 적용된다. 실기TV overscan 해결은 다음 관측까지 미확인이다.

## 검증 결과와 한계

최종normal05 통합809, 기존 실제1초 timer5, 인과대조5가 통과했다. FAT16/32×SDSC/SDHC, 사용클러스터 앞부분7000/12000,2/8섹터 클러스터,힌트wrap,빈영역분산,조밀한FAT의native116개 전체응답실패,모든593 SRAM IO위치,checkpoint/표식timer실패·고정/랩타이머·재진입을 검증한다. 카드·핀·시간·SRAM·CRC어셈블리원시연산은 모형이다. 인과대조는 공간탐색/재읽기비교/RESET재유지/최초표식/표식재유지를 하나씩 제거하며 기대 assertion으로 실패한다.

루트디렉터리 확장에서는 FatFS가 last_clust 대신 현재directory의 마지막cluster 다음부터 찾는다. 조밀한FAT+가득 찬 root 조건은STEP2에서 제한 종료하고 write0임을 검증했다. 이 경로의 일반적 성공은 이번 수정 목표 밖이다. 확장이 다른 빈영역을 선택해hint를 바꾸면 writer가 다시 탐색할 수도 있다. 분산공간만 있는 카드는 총여유가 충분해도1C에서 거부될 수 있다. 단계별실패를 분리하는 좁은진단이며 모든카드배치에 대한allocator개선이 아니다.

ARM01은 main→run→mini→1A→초기화→1B→mount→1C→실제get_fat→writer 순서와7checkpoint를 확인했다. 기존13개 native/ff/timer/bootdecode 입력SHA를 보존했고, 수정된boot/checkpoint와 새platform/space/layout는 최종host와바이트가 같다. firmware132880바이트 SHA `b2895696ab5c665b2b9a0a4acf3997f0ca13442b40e6f1ebf4abc3513036db1e`. ARM 실기실행·새RTL/Questa/fit/ASM은 수행하지 않았다.

TRIAL176865바이트 SHA `b2cec2a84da893057626a295952683baf20080e993f049c1e95d2112f1972aa3`; SOURCE8595750바이트 SHA `e5abe8a47b6535243919bf42286900b1960d628256f28cf5d420d0548f3fe90b`. 모든ZIP멤버 재읽기와정상044169056바이트의기존원본해시를확인했다. TXT판독기 정상/빈파일/변조3경우통과. SD자동설치없음. [실행·복원](../docs/SDREPORT084-RUN.ko.md).

## 증거와 다음 작업

동결증거2537파일 manifest `1a43873e74e8a5cc888d099874d9ff17caa6959b4b12ffdd53a9d0987100a3d5`. finalnormal05/negative5종05/ARM01/package01. 원래083재현 폴더의 result.json은 복사된083역사메타이므로 신규실행결과로 사용하지 않는다. 별도 provenance084.json과occupied-run.log를 따른다. normal02의mount전last_clust 기대오류,negative03의공통row assertion메시지 기대오류,Make최초의존성실패/재시도,50.37초영상의60초추출범위오류를 보존했다. 완료freeze/update재실행·044–084archive편집금지.

재현은 `nes_report084_prepare.py --evidence081 <고정입력> --out <새source>` → 기존build_nes_report079_arm.ps1 → check_nes_report084_arm.py. 출력obj-report079는이름재사용이며실제VERSION084다. test_nes_report_space084.py의normal과5negative는각각새폴더를사용한다. verify_nes_report084.py는동결증거/모든ZIP/공개소스해시를검사한다. 공개clone만으로개인고정입력까지재현가능하다고주장하지않는다.

PR34는작업시open/미병합으로확인되어같은PR에추가한다. 다음입력은084영상·새TXT·044복원/메뉴/GBC다. 1C/2/3경계를먼저나누고3072바이트·최종화면·복원결과를함께확인한다. 다른SD요구/포맷/LED/분해/PCUSB/부품재질문없이현장firmware→관측회수방식을유지한다. CF68 P2/동일쌍P3 및전체NES4LAB/P5/P6는별도다.
