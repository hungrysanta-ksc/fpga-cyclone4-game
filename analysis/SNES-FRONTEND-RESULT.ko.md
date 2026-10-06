# H0 실기 확인과 SNES 전송부031
2026-10-06. NES-H1-SNES-FRONTEND-031. Core014/CPU017/NES trace replay025 유지.

## H0 결과
사용자가030 진단이 정상으로 보인다고 보고하고 계속 개발하도록 지시했다.
첨부5.27초 영상의0.5초 간격11표본에서 제목NES H0 030,GRID/BARS/CROSS 및1→2→3→1 순환을 확인했다.
표본 페이지는1,2,2,3,3,1,1,2,2,3,3이다. H0 기본 육안 확인을 통과로 기록한다.
전원 시작·RESET/메뉴·warm restart·장시간·NES FPGA/SMB3·물리타이밍은 이번 영상에서 검증되지 않았다.
사용자 MOV와 추출 PNG는 로컬 ignored 증거로만 보존한다. 촬영 영상으로 exact 화소나 정확한60Hz를 주장하지 않는다.
이전029 점무늬 진단의 판정 불가는 그대로 보존한다.

## 새 구현과 실제 시험
논리 SNES 핀→주소 decode/단발 read/write→029 준비 버퍼→CDC→큐를 같은 nes_transport wrapper에 연결했다.
00:6000..6009 제어/상태,00:600A 오류,40:8000..8BFF 연속 payload 읽기다. 아직 설치 ABI가 아니다.
긴 /RD에서 한 바이트만 소비하고,raw /RD 종료·write충돌·reset·주소/ROMSEL 변경에 버스 구동을 차단한다.
중단된 주소가 되돌아와도 오류가 래치된 payload를 다시 구동하지 않는다. 복구는 fresh epoch 공통 reset이다.

실제 Questa 최종3개 클록 조합×13조건 PASS. 원시 핀 출력19,218B가 입력 패킷과 exact 일치했다.
약84MHz host 모델의 payload read 응답 min/median/max48/54/60ns,100MHz45/47/48ns,50MHz87/96/98ns.
모든 register 포함 최대는60/48/100ns다. 이는180ns low/100ns gap/20ns bundle 여유를 준 논리 시험이며 실제 SNES IO 규격이나 물리타이밍 실측이 아니다.
잘못된 순서·조기commit·overread·held address변경·read/write충돌·ROMSEL중단·read중reset·짧은pulse·fresh generation을 검사했다.

## 실기 준비를 막던 RAM 합성 문제 수정
최초 Quartus map은027 큐를 RAM으로 추론하지 못하고 레지스터 수 초과로 실패했다(276003/276007).
031 별도 동기식 RAM 구현을 만들고028 CDC의 복제본에서 해당 queue만 교체했다.027/028 원본 보존.
원래027의14조건을 동일 입력으로 실행하며 매 클록 모든 외부 출력을 원본과 비교했다.
10,492write/10,460read/38,510cycle에서 일치했고,새 통합13조건도 다시 통과했다.

동일 최종 wrapper의 실제 목표기기 EP4CE15F17C8 map/fit 성공:
|항목|전송부만 실측|
|---|---:|
|LE|1,139|
|LAB|111|
|M9K|12|
|payload RAM|73,728bits (9KiB)|
|register|735|
|virtual pins|133|

큐6144B가8M9K,stage3072B가4M9K로 배치됐다. 바이트 총량/9Kbit 단순 계산보다 비용이 크다.
핀2개 위치 미할당,클록주기ps절삭,전압 인터페이스 등의경고는 남는다. 물리핀/PLL/IO/CDC 제약 및STA를 완료하지 않았다.
이 출력은 FPGA 설치용 이미지가 아니며 새 H1 실기 묶음은 아직 준비되지 않았다.

## 전체 NES 자원 위험과 다음 작업
018 코어+기본RAM12,281LE/881LAB/12M9K에 단순 합산하면13,420LE/992LAB/24M9K다.
992LAB는기기963개보다29개 많고,13,420LE는내부목표13,000보다420개 많다.
별도 fit 값은 공통화/packing에 따라 달라지므로 통합 불가능의 증명도,통합 가능의 보장도 아니다.
**전체NES+전송부 합성으로 실제 packing을 먼저 확인하고 자원 절감 대상을 정한다.**
H1 자체 패턴 생산기·실제 PPU DMA 클라이언트·보드PLL/핀/IO/CDC/복귀는 별도 진단 경로로 계속 연결한다.
H1은 전체SMB3/DMC 완료를 기다리지 않되,자기 후보의 실제board fit/STA/로더/복귀가 갖춰져야 한다.

## 실패·검증 이력
compile01: TB변수before가SV예약어였음. 이름을고치고원본/로그보존.
initial-pass02:11조건통과 후중단주소재구동금지/ROMSEL/overread와통합wrapper를추가.
test03:overread가stage에요청1회를보내고데이터없이거절됐는데quiet_read검증기가요청0회를요구한오류.정확히1요청/no drive로수정.
resource01:기존큐RAM추론실패를별도구현으로수정.
최종04:동등성14조건+frontend3×13조건성공.최종resource02:map/fit성공.
최종검증기는Quartus보고서0xB0문자를UTF-8로읽다실패;원본유지하고byte보존latin-1로ASCII수치만읽도록수정해같은증거재검증.
무료StarterFLOAT기존경로사용,새유료라이선스나반복smoke없음.
[검증](snes-frontend-verification.json), [계약](../docs/nes-snes-frontend-contract.md), [실기 상태](hardware-readiness.json).
