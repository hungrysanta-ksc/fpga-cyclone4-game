# NES226: 일반 배경 셀의 반복 계산 제거

225 실기는60초 실행·메뉴 복귀에 성공했지만 스크롤 성능은 미달이었다. 이번 변경은 **실제 화면을 만드는 ARM 계산량을 줄이는 성능 구현**이다. 새 디버그 체계나 FPGA 배선 변경이 아니다. 예외가 없는 열에서 기존과 같은 타일 계획을 더 적은 계산으로 만들며, 계획 순서·타일 내용·두bank 갱신·최종표시ACK는 보존한다.

## 변경과 동등성 근거

기존 플래너는 모든 BG 셀에 대해 최대8줄의 destination/source fineY를 반복 조회했다. 조회마다 예외 목록을 순회하고, 셀마다16개 row값을64bit키에 다시 넣었다. 스크롤 좌표를 바꾸는225와 달리226은 이 계산만 줄인다.

compact group마다 해당 줄 범위에 속한 예외 열을33bit mask로 한 번 분류한다. 현재열과0번열에 예외가 없으면 `fine(y,0,false)`, `fine(y,x,true)`, `fine(y,x,false)`는 모두 `rows[y]&7`이다. 초기identity row에같은값을다시쓰는작업이므로 생략해도 같다. 그때 exact key의row부분은컴파일상수다.

**0번열의 예외는 모든 열의 destination fineY를 바꿀 수 있다.** 따라서0번열에예외가있으면group전체가기존경로를사용한다. 다른열의예외는그열만기존경로를사용한다. 예외태그·row-alt·mask·물리CHR검증을삭제하지않으며, split group·raw row·palette epoch·fineX·coarseX의의미도바꾸지않는다. 이것은프레임간CHR캐시추측이아니므로새로보이는타일의계획·갱신을생략하지않는다.

실제소스는`nes_fast226.py`가봉인된225/arm01에서재현한다. 바뀐파일은planner, 두phase계측을추가한runtime/budget C·H, 시험판이름3파일이다. wire2231, SNES2121, 기존FPGA, resident allocator, plan service, receiver, sink, input/audio/60초제한과시작절차는유지한다.

## 검증

- **225와226의실제C1,939프레임**: emitted plan struct, 전체video, 함수포인터를제거한resident상태, 두bank전체를138355352B trace로저장하여완전히비교했다. 화면결과뿐아니라타일키·slot·순서도같다.
- 독립적인186 reference표시픽셀·OBJ바이트비교를함께유지했다. `referenced_bytes=111072192`는BG픽셀과OBJ바이트가섞인검사수이며순수픽셀수로부르지않는다.
- 33개열×8개줄×2개fine변형을각각3bank전환으로확인하고,128개예외목록·raw row·palette변화·양방향wrap·epoch·최대slot·동작중실패등을포함했다.
- 기존11개오류경계통과. 0번열broadcast를제거하거나모든예외를무시하는2개잘못된구현은독립픽셀검사에서실패했다.
- 생산RUN소스9프레임·6실패경계·receiver9경계통과. 기존scalar geometry의BEGIN만2231인fixture를재사용했다. 전체게임/실제FPGA cosimulation은아니다.
- BEGIN/finish카운터기록·잘못된phase거부·기존wire집계·4096B로그상한검사통과. 최대3521B. postSTOP저장경로는225와이름외동일하다.
- 기존225의C+실제65816소비기30프레임1835520픽셀검증은이번에재실행하지않았다. 같은소비기소스와같은계획/출력상태를근거로재사용하고기존출력파일도대조했다. RTL/FIT/ASM을반복하지않았다.

합성시험의`fine()`호출은43850959→880612회, 그함수내예외항목검색은50657951→1174142회다. **새group mask검색은이두수치에포함되지않고실제CPU시간·FPS증가율도아니다.** 실제SMB3에서예외가많으면기존경로비중이높을수있다. 동일입력에대한전송량·타일생성량을줄이는변경은아니다.

## 전체 ARM과 계측 의미

|항목|225|226|
|---|---:|---:|
|펌웨어|209196B|209476B|
|static RAM|28020B|28116B|
|RUN 보수적 bound|34984B|35008B|
|IRQ 예약|508B|508B|
|남는 여유|1912B|1792B|

증가분은12bin×2필드×4B=96B static계측과24B의RUN bound다. 기존1024B여유gate를완화하지않았다. 정적call graph검증이며실측stack high-water나모든향후mapper메모리보장은아니다. 저장SRAM/GBC164를사용하거나변경하지않는다.

budget schema226은기존21필드뒤에`begin_ticks`, `finish_ticks`를덧붙인다. BEGIN은guard/resident_begin/sink_begin, finish는마지막flush·chunk전달·END확인과동반서비스/대기를포함한다. 둘다10ms단위이고해당subphase가성공했을때누적한다. 뒤에서프레임이실패하면앞subphase만남을수있어전체plan과항상정확히합산되는것은아니다. CPU-only/FPGA-only시간으로해석하지않는다. 오디오·컨트롤별지연은이계측만으로분리되지않는다.

첫test01은Windows GCC의`%llu`출력형식거부로컴파일실패했고생산소스문제는아니다. 출력cast를수정한test02를선택했다. check01은보수적메모리검증뒤검증기출처메타데이터키불일치로마지막단계가실패했다. 완화없이출처필드를맞춘check02만배포gate다. 실패자료도보존한다.

## 다음 실기와 남은 일

[시험 안내](nes-game226-ready.ko.md)에따라첫레벨숫자1+A→오른쪽+B/A스크롤을확인한다. 선택증거는arm01/test02/runtime01/check02/evidence01/release01이며[분석JSON](../analysis/fast226-verification.json)과[배포JSON](../analysis/release226-verification.json)에해시를기록한다.

판정은전체표시완료·실제스크롤체감과receive/planner/BEGIN/finish/SEAL을함께본다. CPU가빨라지면뒤단계에일찍도착해E8조회가늘수도있으므로조회수하나로퇴보/성공을판정하지않는다. 여전히전체수신, 예외처리, 새타일생성·전송완료,64B맵갱신비용이남는다. 정지장면개선만으로합격하지않으며60fps는미완료다. 같은225/044재시험·추가FIT보다이번첫레벨실기가다음gate다.
