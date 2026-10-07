# SD 원본 수집 TXT 저장 실패 수정 — 073

## 작업 목표

사용자는072 실행 화면 `SDINFO072-BASE069 / TXT SAVE FAILED / /HW003000.TXT / Save code: 4`와 TXT 미생성을 보고했다. 이 관측은 실제 부팅/화면 도달과 저장 실패의 근거이며, 원본SD 바이트·FatFS 상세 오류·메뉴 승인 근거는 아니다. 문제를 실제 저장 경로에서 재현하고 보호를 유지하는 수정 펌웨어를 준비한다. 기존 PR27은 이번 시작 확인에서 open/미병합이므로 같은 목표의 후속 수정으로 반영한다.

## 작업 내용

072 플랫폼은 nes_diag_begin으로 활성 보호를 켰지만 report writer가 nes_return_log_allow(true)를 호출하지 않았다. 실제069의 nes_return_sd_write는 허용 구간이 없으면 RES_WRPRT를 반환한다. 실제 FatFS의 f_open은 새 디렉터리 entry를 RAM cache에서 준비할 수 있다. 첫 f_write의 FAT 할당이 창을 이동하며 이 entry를 쓰려 할 때 차단돼 FR_DISK_ERR/0바이트·Save code4가 되고 디스크에는 이름도 남지 않는다. FAT16과FAT32에서 이 경로를 재현했다. 표시 이름은 시도 경로이며 성공 증거가 아니다.

073 파생 writer가 보고서 새 파일 생성→쓰기→sync/close→재읽기·모든바이트/close 동안만 기존 bounded 허용 구간을 소유한다. 모든 반환에서 허용을 회수하며 진단 보호는 유지한다. 공유 fault 뒤 물리SD 전송을 추가하지 않고 wrapper의 순수 flag 회수만 한다. 원래 bounded SD/FatFS/runtime11개 입력은 동일 해시이며 우회·legacy 쓰기 fallback을 넣지 않았다. 수집 입력은 계속 읽기 전용이다.

동일072 struct를 쓰는 별도073 collector/writer/platform과 도구로 구분했다. 기존072 공개 소스와1411파일 archive는 그대로다. version SDINFO073-BASE069, 새 TXT HW004000–999다. 원본 사본 경로 firmware.before-sdinfo072.stm은 유지한다. 첫 실패의 Op/FAT result/반환·요청Bytes/offset을 RAM에서 보존해 화면에 표시한다. native fault는 추가SPI 화면출력 없이 보호 상태에서 멈출 수 있다.

실제 전체 FatFS ff.c/ffconf·문자변환·실제069 write guard/response check/runtime/return helpers를 RAM FAT16/FAT32 medium에 연결했다.072 비교는 원문 writer를 symbol만 rename해 링크했다. 기존072 code4·전송0·entry 미반영을 두 FS에서 재현했고073 새 저장/별도 reader의4500바이트 대조가 통과했다. CMD24 위치13개씩26fault·WP·예산·inactive/nested권한·형식 등 **40개** 검사가 통과했다. write-window 제거 mutation은 같은 실제 저장 assertion에서 실패했다. 모델의 read entry는 실제 sdn_read의 sticky fault 조기 거부를 사용한다. FatFS가 실패 뒤 disk_read/write API를 부르더라도 CMD/media 전송은 차단한다. SD medium/CMD24/응답CRC/송신은 모형이며 물리 카드 신호 검증은 아니다.

073 collector52/writer23/platform6/report29도 통과했다. ARM 전체 링크에서 main→sdinv_run, writer의 허용 true/false2호출, 마지막 화면→오류확인→leave 순서를 확인했다.133184바이트 SHA `cd7eea7ae61cca3be60a8c5f876a09dbd29e0c6669ccba53462c035b654de5e7`의 firmware-only 재시험 패키지와 대응 소스를 준비했다. 새로운 RTL/FPGA fit/Questa/ASM/CF68 적재는 없다.

새 동결0731571파일 manifest `eaa22dcf085ac6598484ed6ab5945bc6b56534996f83c18b0eafa24ce9fcd586` audit와 기존072 audit가 통과했다. 최초 경로src누락·함수prototype 추출/타입/문자변환 include·미사용SRAM 링크·FAT 서명 누락·native read 거부 모델 누락과 원시 로그/전사를 보존했다.06 통과 후 최종 writer로07 재실행했다. ARM 최초 Make dependency 실패 뒤 두 번째 빌드 통과도 보존했다. 마지막 동결 스크립트의 숫자로 시작하는 Python keyword syntax 오류는 동결 밖 terminal 전사이며 데이터 생성 전 수정했다. 동결을 사후 편집하지 않는다.

## 작업 결과

**쓰기 허용 구간 누락의 재현·수정·통합/회귀/ARM 검증·새 전달본 준비는 달성했다. 실물073의 TXT 생성 성공은 사용자 재시험까지 미달성이다.** 이전072 writer mock과 platform mock은 하위 SD의 허용 가드를 실행하지 않아 이 누락을 놓쳤다. 앞으로 상태/권한이 다른 계층에 걸친 변경은 실제 호출자·FatFS·native guard/runtime를 연결한 성공·오류 대조를 완료 조건에 넣는다.

[재시험 안내](../docs/SDINFO073-RUN.ko.md)에 기존 원본 독립 백업과072이전 사본 보존,firmware 하나 교체,새HW004nnn.TXT/실패상세 회수,원본 복원을 정리했다. 다음은 사용자의 새 TXT·원본 복원/메뉴/GBC 관측 확인과 실제 menu 분류 대조다. CF68 쌍071·전체 코어059는 변경되지 않았고 준비도5완료/6부분/1미완료 및 설치 보류 상태도 유지한다.
