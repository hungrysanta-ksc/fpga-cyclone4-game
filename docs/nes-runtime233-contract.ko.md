# NES233: 출력 증분 전체 RUN 연결과 송신기 사전 조건

PR127의231/232 후보를 이어 **출력 planner/sink를 실제 전체 ARM RUN에 연결했다.** 이전의 상주160B 산술 차감에서 한 단계 나아가 링크된 콜백·오류 처리·활성 IRQ까지 검증했다. 남은 여유1616B로 기존1024B 기준을 통과했다. 입력은 기존227 프로토콜이며 아직 FPGA 입력 delta 송신기가 연결된 것은 아니다.

## 작업 의미

60fps 화면 경로를 실제 실행 루프에 통합하기 위한 작업이다. 화면 생성→계획 queue→실제 drain→최종 표시 ACK→resident/dirty commit→FPGA retire 순서를 기존 RUN에서 유지했다. 저장 공간만 맞춰 본 사전 컴파일이나 디버그 로그 추가가 아니다. 다만 아래 시험의 FPGA/SNES 응답은 모델이며 실제65816 검증은 앞선232의 범위를 재사용한다.

## 구현·실행 검증

`nes_runtime233.py`는 봉인된227 소스에서 별도 후보를 만든다.231 receiver/planner/sink를 가져오고 RUN의 planner와 SEAL 호출을 교체한다. RUN 지역 work에 dirty124B와 향후 입력 source36B를 두고, runtime에는 포인터2개를 추가한다. 시작 때 두 상태를 초기화하고 오류에서 dirty를 abort/source를 invalid로 만든다. RUN 종료 시 포인터도 회수한다. 대형 work 할당 전의 기존 low-stack startup은 유지한다.

**source36B는 예약 및 reset/fail 수명만 연결했다.** 기존 수신기를 새 delta decoder로 바꾼 것으로 표현하지 않는다. 링크 결과에서도 source begin/write/raster/shift 등 미사용 함수가 제거되었음을 확인했다. 따라서 향후 입력 parser/상위 transport callback이 연결되면 스택 그래프와 ROM 크기를 다시 검증해야 한다.

실제 전체 C RUN은9개 프레임, generation65535→0, queue/plan finish/표시ACK/retire 순서를 통과했다. reference624,064 checks, map/CGRAM/OAM/raw metadata 복원, dirty 최종commit을 확인했다.6종 오류(표시ACK 변조, deadline, service 실패, retire 정지, 잘못된 bulk generation, 입력CRC), 기존 입력9경계, mutable 거절 및 동일 ROM cold restart도 통과했다. 오류 후 추가 SPI 호출 금지와 양쪽 기준 무효화도 확인했다. 시계와 source/SNES 응답은 fixture이며 출력 cadence 측정은 아니다.

## 실제 ARM 링크 메모리

| 항목 | 기존227 | 후보233 |
|---|---:|---:|
| 상주 RAM |28,116B|28,124B|
| RUN 외 가용 |37,308B|37,300B|
| foreground 전체 상한 |35,000B|35,176B|
| IRQ reserve |508B|508B|
| 최종 여유 |1,800B|**1,616B**|

native_frames의 실제 prologue는 push8 + SP32000 + SP8 =32016B로 `.su`와 일치한다. 기존31848 대비168B 증가이며 work160B 외 호출 인자/정렬8B가 포함된다. planner 등 나머지 경로도 실제 링크 그래프로 다시 계산했다. IRQ는 SysTick/TIM2/NMI 각각의 FP 확장 hardware frame과 정렬까지 유지한다. 기존 platform/library 명령 본문도 주소 정규화 후 동일함을 검사했다. 최소1024 기준 대비 남은 추가 여유는592B다. 스택 high-water 실측이나 모든 메뉴/GBC 경로의 새 증명이 아니다.

compile-only 이미지211,428B, SHA256 `500da3d6ac16be681c88b465861b8b8edf7f92cc1ab5b91adde184a2dc4e2058`. 새 FPGA/ROM pair 및 설치ZIP은 없다. 이 이미지를 기존 FPGA로 실기 실행하도록 배포하지 않는다.

## FPGA 자원: 기존 송신기를 교체해야 한다

봉인된224 FIT에서 총15,249/15,408LE,47/56M9K를 확인했다. `nes_native_export203:native_export`는644LE/225register/0M9K다. 새 송신기를 옆에 추가하면159LE뿐이지만, **기존644LE를 교체할 경우 산술상803LE의 영역**을 검토할 수 있다. 이 수치가 그대로 회수되거나 타이밍이 통과한다는 뜻은 아니다. 합성 최적화·배치·라우팅은 다시 확인해야 한다.

8비트 packed base5741B를1024×8 RAM으로 저장하는 용량 모델은6M9K다. old/new map row2×66 + literal240 + record13 =385B scratch를 별도1M9K에 둔다면 합계7M9K, 남는2M9K다. 이 계산은 실제 추론·포트·제어 로직을 증명하지 않는다. 폭이 다른 물리 query의 zero-padding 및 비활성 항목 canonical 값, 읽기 지연, in-place base 교체와 취소 처리도 필요하다. 두 개의5741B 전체 base를 추가하면 최소12M9K로 현재 여유9개를 초과하므로 기본안에서 제외한다. cartridge save SRAM은 사용하지 않는다.

현재 exporter의 query/lease/release/ACK 및 core/fill/CDC 연결을 교체 범위로 명시한다. 기존 sender와 새 sender를 동시에 남기거나159LE 여유에 새 기능을 단순 추가하는 방향으로 진행하지 않는다. 물리 tag·행별 bank·mask 및 MMC4/MMC5 확장 시 fetch-time 의미를 보존한다. 제어 로직803LE 이내와 작은 RAM의 실제 포트 구현은 **아직 미검증**이다.

## 순차 두 번 스캔은 이 모델에서 탈락

231의 입력 API는 BEGIN에서 span 수/펼친 byte 수를 받는다. 이를 FPGA가 처음부터 알려면 사전 계산, descriptor 저장, 또는 전송 형식 변경이 필요하다. 단순히 geometry를 두 번 훑고 나서 전송하는 방안을 수치로 확인했다.

가장 무거운 ready4 시나리오(954프레임)는 SPI5333B,2.625MHz에서16.25295ms다. 선택한8비트 base를 두 번 전체 순회하는11482cycle만 추가해도 SDC45.454ns 기준0.52190ms이며, 순차 합은**16.77486ms**다. 이는 query 대기·write·FSM·ARM 계산·SPI 간격 등을 모두 제외한 해당 설계의 낙관적 값이다. 물리 clock 계측이나 모든 구조의 불가능성 증명이 아니며 ready4 자체도 실제 runtime 상한이 아니다.

따라서 이 두 번 스캔 순차안을 구현/FIT 대상으로 채택하지 않는다. 다음은 **한 번 순회하며 개수를 END에서 확정하는 framing** 또는 근거 있는 capture/전송 겹침을 먼저 정한다. END에서 개수를 검증하더라도 serial/epoch/CRC/token/범위·순서·부분 실패 무효화 조건은 보존해야 한다. source 내용을 소비한 시점과 화면 표시 완료도 구별한다. 현재 exporter는 이전 표시 retire를 기다리므로 새 겹침이 이미 구현되어 있다고 가정하지 않는다.

## 남은 SNES 5프레임 분해

232와 동일 자료/결합 규칙으로 계산했고 실제 다회 VBlank 사용과 대응한다. 아래는 bytes와 DMA 설정 비용을 합친 charge이며 실제 CPU cycle이 아니다.

| 프레임 | map 업로드 B/명령 | OBJ 업로드 B/명령 | raw B/명령 | 총 charge |4192 초과|
|---|---:|---:|---:|---:|---:|
|952|1824/2|512/9|48/1|4752|560|
|954|1680/5|384/1|112/1|4272|80|
|955|1664/4|448/4|112/1|4400|208|
|963|2000/5|96/1|112/1|4240|48|
|968|1968/3|352/8|176/1|4720|528|

총 charge에는 BG패턴 및 final960도 포함한다. 따라서 raw 압축만 더 하는 것은 이 구간의 주된 해결책이 아니다. 작은 OBJ 명령과 스크롤 map, 마지막 시점에 모든 DMA를 몰아놓는 구조를 함께 봐야 한다. 비활성 VRAM에 일부를 미리 올리는 방안은 가능성일 뿐 아직 구현하지 않았다. 구간별 유효성·목적 은행·token과 표시 전에 완전성 확인이 필요하며,232의 최종 coverage에만 의존하던 간격 결합을 그대로 앞당기면 안 된다.

## 다음 실행 순서

1. 송신기 교체 범위 안에서 한 번 순회/END-count 계약과 RAM port schedule을 정하고, 같은 실제 스크롤 입력에서 byte·source cycle·ARM parser 상한을 연결한다. SPI input/output을 동시에 보는 현재 모델과232 소비기를 재사용한다.
2. 작은 범위의 실제 controller/포트 근거가 확보되면 한정된 합성 자원 검증을 한다.803LE는 합격 결과가 아니며 이를 넘는 seed/FIT 반복으로 이어가지 않는다. A가 성립하지 않으면 병렬 metadata B로 전환한다.
3. 잔여48..560charge의 작업 분산과 전체16.67ms/최대 화면 나이를 검증한다. 기존4192를 낮추거나 frame skip/강제 blank로 합격 처리하지 않는다.
4. 생산 입력 binding 후 full RUN/IRQ 재검증, whole-board/paired build를 통과하면 첫 레벨 스크롤 실기로 간다. 같은227/044 시험은 반복하지 않는다.

선택 `probes/nes-runtime233/arm01`, `check01`, `test01`, `analysis02`. builder의 전체 로그/ELF/SU/콜백 그래프와 소스 pin을 로컬 보존한다. analysis01은 FIT 보고서를UTF-8로 읽으려다 실패했으며 ASCII 수치 구간을 byte-preserving latin-1로 읽도록 수정했다. sandbox objdump DLL 재할당 오류는 기존처럼 승인된 외부 실행으로 해결했다. FPGA source·라이선스·ROM 원자료를 새로 배포하지 않는다. 이전232/231과 생산13pin은 검증에 사용한 파일의 hash로 연결하고 이전 전체25720파일을 이번에 다시 읽었다고 주장하지 않는다.

재현은 `nes_runtime233.py --out <new-arm>`으로 후보를 만들고 기존 `build_nes_game149_arm.ps1` 임시 드라이브/검증된 mini image 절차로 빌드한다. 이어 `test_nes_runtime233.py --arm <arm> --out <new-test>`, `check_nes_runtime233_arm.py --arm <arm> --arm-bin <bin> --out <new-check>`, `analyze_nes_runtime233.py --arm-check <check> --runtime-test <test> --out <new-json>`을 사용한다. GBC164/게임 세이브 SRAM/227 배포물과 기존 오류 자료는 유지한다.
