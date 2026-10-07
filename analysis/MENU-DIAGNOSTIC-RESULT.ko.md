# NES062 — 메뉴에서 호출되는 후보 확인·검증·복구 경로

2026-10-07 KST.061/PR15 병합 커밋 `39e831aaf045fd0f668f8b30b0482dbded2558fb`에서 진행했다. **새062 C 함수를 실제 수동 메뉴에 연결하고 CF61·형상 확인 및 복구 결과 기록을 검증했다.** 아직 설치할 SD 이미지나 실제 STM32 실행은 없다. [계약·재현](../docs/nes-menu-diagnostic-contract.md), [기계 판독 결과](menu-diagnostic-verification.json).

## 변경한 동작

-80/96KiB 전용 `.nh1` 표식을 구분하여 승인된 고정 SD 진단만 선택한다. 표식과 실제 헤더의 형상이 다르면 FPGA 설정 전에 거부한다. 기존044 표식/이미지와GBC를 보존한다.
- 적재 전 CF61/F0A5/F144/protocol59와idle/count0을 확인한다. 잘못된 FPGA 조합은BEGIN 전에 거부한다. CF는파일해시 확인을 대신하지 않는다.
- 파일 선택/최근/즐겨찾기의3개 실제 메뉴 호출을 연결하고NH1자동실행NACK을 유지한다. 성공/복구가능/메뉴준비/RESET해제 경계를 구분한다.
- 메뉴재적재 크기0 또는SRAM확인실패에서RESET을 해제하지 않는다. base복구실패 시RESET/USB보호를 유지하며새SD로그쓰기나메뉴진행을 막는다.
- UART안내와결과,안전복구 후별도FIL로그를 추가한다. 로그open/write/짧은write/close실패는복귀를 막지 않으며USBIRQ원래 상태를 보존한다. 화면 표시·진행률·취소입력은아직없다.

## 이번 실행 근거

| 시험 | 결과와 정확한 범위 |
| --- | --- |
| 실제 생성C + SD/PSRAM 호스트 모형 | 기존41SD/복구 경로·18입력 거부,80/96KiB 전체 적재/비교; 추가16메뉴 세션 |
| 잘못된 조합 | CF60/44/0,F0/F1오류,protocol0/54,표식/파일형상불일치가BEGIN0/DATA0으로거부됨 |
| 메뉴/로그 | 재진입 차단,잘못된메뉴준비,IRQon/off,SD입력open실패,STOP실패 후base복구,base실패,로그4오류종류 |
| 검사 제거 대조2개 | CFguard 제거는후보/BEGIN0 assertion,메뉴크기guard 제거는준비거부 assertion에서실패 |
| 실제C GPIO→061물리top 재생 | 적재33200samples/29032응답비트/256핀바이트,비교49472samples/43288응답비트/256ACK; SD오류→STOP |
| 최종ARM전체링크 | main의3개수동run호출과준비/해제호출,run→실제SDprobe호출을disassembly로확인. probe1104B/run160B |
| 자원/STA | 새실행없음. 합성대상SV가061fit03과동일하므로2386LE/186LAB/1458regs/44M9K/135핀/PLL1·내부최소0.131ns재사용 |

파형 총응답72320비트다. 비교96KiB 준비는testbench loader→핀 쓰기이며,새C→보드전체성공시험이아니다. 디지털PLL stub과70ns/35ns/350ns 모델을실제부품사양으로부르지않는다.061START두방어/lock상실 검사도같은파형시험에서유지했다. FLOAT wrapper가종료했고라이선스서버listener18000은0이었다. 전체NES코어8프레임은이번에재실행하지않았다.

동결 원시 근거는로컬 `probes/nes-menu-diagnostic-062/`의 **309파일manifest**다. verifier가소스/로그/대조/ARM호출/061SV동일성을검사했다. 공개저장소에는ROM·실행파일·라이선스·원시로그를포함하지않는다.

## 보존한 초기 실패

첫host생성은056prefix에도존재하는ID루프를단일매치로변환하려다assertion에서멈췄다.060추가부분만변환하여044/056전체prefix를보존했다. 첫CF대조는정확한사전BEGIN assertion에서실패했으나수집기가더뒤의result assertion을기대하여실패했다. 첫메뉴대조는guard제거로인자를미사용하게만들어Werror에서멈췄고,인자참조를유지한두번째대조가의도한assertion에서실패했다. archivefinalizer의초기괄호syntax오류도archive생성전에수정하고실패source를보존했다. 동결finalizer를다시실행하지않는다.

정상host03의driver snapshot은대조수집기수정전이며생성C는최종공개generator와같다. ARM빌드 당시builder와이후동일호출검사의disassembly를각각보관했다. 최종publicbuilder는그호출검사를내장한다.

## 다음 완료 경계

H07/H09가진전했고H11은실제메뉴포함ARM부분이완료되어부분완료다. 최초실기준비12항목은완료4/부분6/미완료2이며공수/제품완성률이아니다. 화면/관측·취소/블로킹정책은H08,실제보드부품/외부IO는H05/H06,두형상전체C→보드성공은H10,FPGAASM·쌍패키지/SD백업복원은H11/H12로남는다. 메뉴RESET해제코드에도달한것을사용자화면복귀성공으로기록하지않는다.
