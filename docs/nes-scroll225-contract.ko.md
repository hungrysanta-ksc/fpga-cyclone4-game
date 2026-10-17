# NES225: 가로 스크롤 시 SNES 맵 위치 유지

PR122는6c4bd8412a9e6bba0c5c54939029a95e20db22ea로 머지됐다. 새 branch `codex/nes-scroll-map-225`. 223 실기60.06초/416표시를 기준으로 다음 성능 변경을 구현했다. 시험판 준비 완료이며 실기225 결과는 아직 없다.

## 작업 의미

60fps를 위해 스크롤 때 다시 쓰는 맵의 양을 줄이는 구현이다. 기존 타일 재사용은 유지하되, 매번 화면 왼쪽부터 타일을 재배치하던 일을 줄였다. 디버그 기능 추가나 FPGA 배선 재시도가 아니다. 첫 레벨의 실제 스크롤로 다음 효과를 확인한다.

## 원인과 변경

기존 플래너는33개 보이는 열을64열 맵의0..32에 놓고 나머지를0으로 지웠다. 가로로 한 타일 이동하면 같은 타일도 다른 목적지에 놓여 두64B 행 블록을 다시 전송할 수 있다. 두 VRAM bank가 번갈아 표시되므로 직전 표시 대비 변경과 대상bank의 미반영 변경도 합쳐야 한다.

225는 캡처한 line_v의 coarseX와NT-X를0..63 배치 좌표로 사용한다. compact group마다 첫 행의 좌표를 고르고33개 열을 `(base+x)&63`으로 놓는다. HOFS에도 `base*8`을 더해 같은 화면을 보인다. 같은group의 중간 raster값이 달라져도 배치는 고정한다. fine X·VOFS·행 재조합은 기존 값을 유지한다.

이 좌표는 **배치 선택일 뿐 패턴 내용 추측이 아니다**. 실제 fetch된 physical CHR tag, 속성, row/alt/mask와기존slot 할당으로 모든 보이는 셀을 계속 작성한다. coarseX가 geometry와 무관한 값이어도 map/HOFS를 같이 회전하면 픽셀은 같아야 하며 이를 시험했다. MMC3 은행 번호나 특정SMB3 장면으로 재사용 여부를 추정하지 않는다.

cold map은 기존4096B를 모두0으로 시작하고 첫 두bank를 완전히 초기화한다. 이후 보이지 않는 열·행은 지우지 않는다. 다시 보이는 셀은 SEAL 전 반드시 덮어쓰므로 오래된slot을 가리키던 셀이 그대로 드러나지 않는다. 화면 밖 셀까지 VRAMslot의 유효성을 요구하지 않고 현재 보이는used bitmap만 기존대로 검증한다. dirty union, inactivebank 보호, epoch와최종displayACK/commit 규칙은 변경하지 않았다.

## 자원·호환 범위

- 실제 변경: `nes_planner211.c`의 배치·HOFS와화면 밖 지우기 제거, 시험번호/경로3파일. 생성기는 `tools/nes_scroll225.py`다. 전체 실제diff는 로컬 증거에 보존한다.
- 새 지속/임시 버퍼0B, wire2231/SNES2121 유지. 입력·오디오·60초 제한·시작222·로더·FPGA·SPI queue는 동일하다.
- ARM209196B(+28B),static28020/RUN34984/IRQ508/여유1912B. 실제 linked callback graph 및 시작 전 작은stack 조건 통과. 실측 high-water는 아니다.
- FPGA는223의7cb1d61a…와바이트 동일, 새FIT/ASM 없음.159LE/2LAB/9M9K 여유 및 기존 조건부IO/CDC 증거를 재사용한다. 전기적·MTBF 전체signoff를 새로 주장하지 않는다.
- 저장SRAM/GBC164를 사용·수정하지 않는다. futureMMC4/5에도 fetch-time physical identity가 기준이다. 새mapper지원이나 강제저장/로드의 실제 구현 완료를 의미하지 않는다.

## 검증

| 검증 | 결과와 범위 |
|---|---|
|기존223 vs225 C|353프레임, normal BG 표시픽셀 및 OBJ 바이트/팔레트/HDMA/raw patch 비교. 양bank 동기화·epoch·wrap·임의coarse변화·축소/확장·11거부 경계 통과. 합산checked값은 픽셀과OBJ바이트를 섞으므로 순수pixel수로 쓰지 않음|
|실제65816|실제Cplanner/sink→기존212프로그램,30프레임1835520픽셀을186기준출력과완전비교. 좌우wrap·fine scroll·재진입 포함|
|실제65816 거부|bad_base/missing_map은 이전화면보호. 잘못된최종ACK는SNES2/C1commit으로갈라져공통reset필요,기존정책유지|
|실제RUN|9프레임·6오류/종료 경계,queue/bulk/finalACK/retire 통과. peer는SPI모델,2231 BEGIN으로변경한기존scalargeometry 입력. packed exporter 검증은미변경223 증거재사용|
|배포검증|선택소스와C/SNES/RUN시험·ELF·firmware·기존FPGA·ZIP내부해시대조. 메모리여유1912B 유지|

C와65816 연결은 실물 FPGA/전체NES게임을 함께 구동한cosimulation이 아니다. 원본 영상으로60fps를 측정한 결과도 아니다. 새호스트검증의Pixel oracle은SNES64×32 맵주소와HOFS/VOFS로매픽셀을독립계산하며동일map배치를전제로하지않는다.

## 비용과 남은 병목

동일192프레임의합성가로스크롤(양쪽64열wrap)을실제223/225 C와실제sink212로각각처리했다.

|지표|223|225|
|---|---:|---:|
|맵업로드|689152B|348672B|
|맵패킷수|3844|1944|
|맵E1 clock bytes(3Bframing포함)|761684B|385104B|

맵E1은49.44%감소했다. 같은합성프레임당순수맵E1전송은약12.09→6.11ms(2.625MHz)다. **실제SMB3의전체전송/FPS가절반이된다는뜻이아니다.** 353프레임전체에는매프레임임의coarse값을넣는거부·급변스트레스가포함되어총E1은1601186→1613679B로약0.78%늘었다. 장면급변/비정상적placement변화에서보편적성능이득을보장하지않는다.

실제65816에보낸30합성프레임의E1구성을분해했다:map54442B, OAM18030B, HDMA/raw13912B, CGRAM7656B, SEAL5610B, bulk descriptor7038B, BEGIN930B(총107618B). 이는225합성표본이며223실기E0/E1중map비율의대용물이아니다. E0는상태/회수poll이고E1은map외여러section·제어를포함한다. 별도오디오·parallelaperture는이합계에서제외된다.

223실기의D1만평균17.91ms,전체계측SPI52.69ms/완료였으므로이번map절감만으로전체16.67ms를충족한다고주장하지않는다. 64Bdirty단위, 세로스크롤의group재배치, 전체geometry수신·plan재생성,메타데이터전송이남는다. 실기225에서receive/plan/seal와완료수·스크롤영상을확인한뒤다음병목을고른다.

## 재현·실패 보존

선택은 `arm01/test02/snes02/runtime01/check02/release01`이다. `nes_scroll225.py`, `test_nes_scroll225.py`, `test_nes_scroll225_snes.py`, `test_nes_scroll225_runtime.py`, `check_nes_scroll225_arm.py`, `nes_scroll225_evidence.py`, `release_nes_scroll225.py`를사용한다. 상세hash와경로는 [분석JSON](../analysis/scroll225-verification.json) 및 [배포gate](../analysis/release225-verification.json).

첫C/objdump 실행은sandbox WinError623으로시작하지못했고승격된동일도구실행으로해결했다. SNES 첫확장시험은기존14프레임용55초host walllimit에서23프레임뒤종료되었다. 동일기능소스로30프레임시험의runner를180초로늘려완료했다. **실기60초나통신timeout은변경하지않았다.** 초기adapter quoting syntax오류도시험진입전수정했으며실패log/metadata를보존했다.

## 다음 gate

[225시험안내](nes-game225-ready.ko.md)에따라실제첫레벨에서오른쪽+B/A스크롤과가능하면짧은왼쪽이동,3TXT·소리/입력·메뉴복귀를확인한다. 영상은장면대응에도움이된다. 현재추가동일223/044시험이나새FIT·계측전용시험은필요없다. 기준223416완료/60.06초는장면이다르면통제성능비교가아니다.


## 225 실기 결과 반영

[225 실기 분석](nes-game225-hardware01.ko.md): 60.07초 실행·사운드·메뉴 복귀 정상. 정지 화면 개선과 스크롤 악화 의심이 보고됐고, 표시 완료401회로223의416회보다 적었다. 장면이 달라 통제된 회귀율은 아니지만 스크롤 성능 개선은 미합격이다. 합성49.44% 맵 절감을 실기 FPS 성과로 해석하지 않는다. 새 타일 처리·BEGIN/finish/drain과 수신/재계산 비용을 함께 다루는 다음 구현이 우선이며 같은225/044 반복시험은 요청하지 않는다.
