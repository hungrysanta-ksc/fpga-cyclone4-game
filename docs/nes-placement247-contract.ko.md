# NES247: 해석·검증 처리 위치와 전체 비용 비교

같은71개 스크롤 frame을 비교하면 **ARM의 planner를 유지하고, FPGA가 map 범위·수신 일치 검사를 담당하며, SNES가 명시적 범위 DMA와 최종 표시를 담당하는 제한된 분담**이 다음 조사 대상으로 가장 유망하다. 전체 planner를 FPGA로 옮기는 안을 선택한 것이 아니다. **배치 변경만으로60fps가 되는 후보는 아직 없다.** 출력 단계의 실제 겹침, 새 CPU/회로 비용과 mapper 여유가 함께 필요하다.

SELECT `placement05`. `placement01`은 분석기 set alias 오류로 실패해 원본을 보존했다.02는 기본 비교,03은 최종 표시 비용 민감도,04는 입력 완료 장벽을 반영했으나 SEAL coverage를 출력과 겹칠 수 있게 둔 오류가 있어05로 대체했다.05는 coverage를 전송 뒤의 필수 구간으로 분리한다.04의 자료 재구성 검증은 유지하지만 그 겹침 수치를 선택 근거로 쓰지 않는다. 새 product RTL/C/65816, 합성, ARM build, emulator 실행, 실기 결과는 없다. 기존 실제 실행 수치를 조합한 모델과 새 Python 자료구조 검증이다.

## 무엇을 같은 조건으로 비교했는가

- cold905/906은 정확성에 포함하고 성능 비교는warm907..975의69frame이다.
- 입력은 기존247의 의미 raster449B+row shift 표현이다. FPGA→ARM 입력 SPI, ARM→FPGA map/manifest 재전송, 기존 tile plan/bulk, non-map metadata, BEGIN/SEAL/status/final 제어를 모두 유지했다. 입력 표현의 FPGA 구현·prepare 시간은 미측정이다.
- SPI는2.625MHz, packet payload≤240B,19B envelope,ready4 시나리오다. 준비 지연에 따라 poll이 늘어나는 실제 상한은 아니다.
- SNES5886/2472의 map·manifest·non-map mark·coverage는 기존 실제65816 측정이다. 새 경로에서 재사용하는 non-map 시간도 조건부 가정이며 새 측정으로 표현하지 않는다.
- 최종 VRAM 쓰기 집합·명령 목록을 그대로 유지한다. 기존 실제 목록의952/955 multi-VBlank와 전역 재정렬의955 최소4198>4192 조건도 남는다.4192는 기존 분할 정책이지 master-clock 상한이 아니다.

## 비교 결과

아래는warm69의 최대값이다. `직렬+표시 표본`은 SPI와 알려진 CPU 구간을 직렬로 더하고, 최종 명령·표시의 기존 no-wait 표본 최대치를 대입한 **민감도 계산**이다. `입력 장벽+출력 이상적 겹침`은 입력 SPI가 끝난 뒤에만 출력 전송과 SNES 준비를 겹치게 한다. 어느 열도 전체 실행시간 실측이나 WCET가 아니다.

|배치|최대 SPI clock-byte|직렬+표시 표본 ms|입력 장벽+출력 이상적 겹침 ms|후자16.67ms 초과|
|---|---:|---:|---:|---:|
|SNES 기존5886 해석·검증 유지|4095|26.135|20.420|9/69|
|SNES 기각2472 압축 해석·검증|3976|32.440|27.153|39/69|
|ARM이 exact64 literal로 풀어 전송|5129|21.034|18.545|5/69|
|FPGA 좁은 검증+SNES typed DMA,제어확장16B|4107|17.334|15.525|0/69|
|ARM이 descriptor/값 배치를 만든 뒤 FPGA가 검사|4272|17.837|16.028|0/69|

ARM literal안은 **새 수신·range 처리 시간을0으로 놓아도** 위 잔여 부족이 남는다. ARM에서 먼저 검사하는 것만으로 전송 후의 범위·수신 일치 검사를 없앨 수 없다. 자료를 풀어 보내는 안은 SPI 비용이 커진다. ARM이6B descriptor와 값을 미리 배치하면 FPGA 파서는 단순해질 수 있지만, 이득은 회로 측정 전에는 알 수 없고 SPI 최대는FPGA 파서안보다165B 늘어난다.

FPGA안의15.525ms는 처리 위치 비교에서 가장 유망한 수치이나 **약1.142ms가 모두 순수 여유인 것은 아니다.** source prepare·ARM planner/새 입력 decoder·IRQ·FPGA parser·새 SNES descriptor/setup/service·추가poll·CDC·VBlank 정렬/대기·최종 retire 등 미측정 비용을 넣어야 한다. 따라서0/69 초과를60fps 통과로 읽지 않는다.

### 입력 완료 장벽을 무시하면 판단이 달라진다

기존233 `nes_native_runtime165.c`는 receiver COMMITTED 뒤 BEGIN→planner→plan finish→SEAL/display→retire→consumed 순서다. 현재 frame의 입력 SPI와 그 frame의 SNES map 처리를 처음부터 겹칠 수 없다.4packet output window는 이미 있으며, 일부 출력 겹침을 새 기능으로 세지 않는다. op7은 앞선 metadata를 drain하는 barrier다.

계산식은 다음과 같다.

```text
직렬 민감도 = 입력SPI + 출력SPI + 알려진SNES준비 + 최종표시표본
입력장벽 모델 = 입력SPI + max(출력SPI, SEAL전의 알려진SNES준비)
                + SEAL coverage + 최종표시표본
```

coverage212는 SEAL 뒤에만 실행되므로 출력과 겹치지 않는 필수 꼬리 구간이다. 두 번째 식도 chunk가 준비되는 순서·ARM 작업·barrier를 구체적으로 스케줄한 것은 아니다. `max(전체SPI,전체SNES)`보다 엄격하지만 여전히 낙관적이다. 기존5886이 입력 장벽 모델에서도9frame을 넘는 점은 단순한 출력 queue 개선만으로 충분하다고 승인할 수 없다는 근거다. 입력을 stream으로 planner에 넘기거나 frame간 pipeline까지 바꾸는 별도 구조의 불가능 증명은 아니다.

## 가장 빠듯한954의 비용

FPGA typed안의중간 제어확장16B 조건:

|항목|비용|근거|
|---|---:|---|
|입력 SPI|2220B /6.765714ms|의미 raster+shift 모델|
|출력·plan·기존bulk·추가제어 SPI|1887B /5.750857ms|총4107B;ARM 재전송 포함|
|유지하는 non-map mark|1.752178ms|5886 실제 구간|
|유지하는 coverage|1.048644ms|5886 실제 구간|
|map 값154B의 WRAM DMA 정규화|0.057363ms|8master-clocks/B 민감도;setup 제외|
|최종9 VRAM 명령2296B+표시|1.797901..1.959467ms|기존 no-wait 표본을 대입;새측정 아님|

최종 표시를 빼면15.374756ms,잔여1.291911ms처럼 보인다. 최종 표시 표본 최대를 넣으면**17.334223ms**로 이미0.667556ms 초과한다. 따라서 FPGA로 옮겼다는 이유로 직렬 일정이 성공한다고 판단하면 안 된다.

이 frame에는45개의 작은 범위 DMA가 필요하다. 새 descriptor 검사·DMA setup·service를 합해 범위당500/1000/1500 master clocks라고 **가정**하면 추가1.048/2.095/3.143ms다. 그때 필요한 겹침은 각각최소1.715/2.763/3.810ms이며,source/ARM/parser 등은 아직 포함하지 않았다. 이500/1000/1500은 새 코드 실행값이 아니다. VRAM 명령의1218..1586 표본을 WRAM staging setup 실측으로 전용하지 않는다.

최종 표시 민감도는 기존232의 payload×8을 뺀 명령잔여1218..1586clock, warm final9284..9442clock을 사용한다. refresh·정렬·실행 경로 영향이 섞인 관측 범위이고 실제 대기 명령은 제외됐다. 새 스케줄의VBlank 여유나 deadline을 증명하지 않는다.

## 제한된 FPGA 역할과 버퍼 수명

새 형식을 정식 protocol로 확정하지 않고 다음 경계를 비용으로 정의했다.

1. ARM은 현재 planner·resident/dirty·양 target stale word를 유지하고 packed exact64 map과 정확한 manifest를 SPI로 전송한다. 기존 byte 비용을 없애지 않는다.
2. FPGA는 CRC/sequence/frame admission 이후 map 범위·payload 길이·단조 비중복을 검사하고256B receipt를 만든다. manifest의 생략zero까지 receipt 전체와 일치해야 한다. 검사 결과를 짧은 hash로 대체하는 안이 아니다.
3. FPGA는 기존2KiB aperture buffer에 `32B header 예약+6B×범위수+값`을 만든다.6B는목적offset/sourceoffset/length 각16bit다. sourceoffset/length는chunk 내부, 목적은inactive map 범위다. descriptor도 버퍼 용량에 포함했다. 새4096B map base를 추가하지 않는다.
4. SNES는 typed version/kind·frame/token·순서·buffer/source/destination 범위를 확인한 뒤 각 범위를WRAM으로DMA한다. descriptor를 무조건 신뢰해 arbitrary destination에 쓰지 않는다. 기존gap 병합 목록을 최종VRAM에 사용한다. 빠진map gap의 값은SNES의기존target shadow에 남으며FPGA가 임의의gap 값을 만들어 보내지 않는다.
5. 정확한 receipt 검사는FPGA로 옮기되,SNES는모든chunk 소비와최종frame certificate를 확인한 뒤에만SEAL/표시한다. certificate용32B를 기존190B SEAL에 더한222B로 예약했다. final binding/카운터 폭/상태 검사는 미구현이며 단순generation16만으로 승인하지 않는다.
6. manifest 검증 전이라도 staging은가능하지만 오류시후보를폐기하고map 초기화상태를무효화해야한다. chunk consume은버퍼해제일뿐display ACK/lease retire가아니다. STOP/epoch/늦은token ACK가다음frame 상태를복구해서는안된다.

71frame의배치를기존target map에서독립재구성해290,816B가일치했다. 따로잘못된목적/길이/source offset·중복·누락·manifest·cold coverage의Python 반례14건을거부했다. 실제RTL/CPU 오류주입14건이라는뜻은아니다. warm69는각1chunk,총1941범위다. cold포함최대chunk1992B로2KiB안에든다.

기존BG/OBJ descriptor kind는1bit이고현재consumer는kind>1을거부하므로단순재사용으로완성되지않는다. typed consumer/control/mux/CDC를함께설계해야한다. 기존tile이읽고있는immutable buffer와metadata buffer를동시에공짜로겹치지않는다. 우선tile phase가drain된뒤같은aperture를쓰는스케줄을가정했으며그대기비용은미측정이다.

추가제어는기존bulk모델83B/chunk(43B descriptor/op7+40B status)를출발점으로,새필드확장0/16/32B를각각더했다. certificate32B도별도로계상했다. 최대SPI는4091/4107/4123B,입력장벽+표시표본은15.476/15.525/15.573ms다. 최종protocol이이상한도내라는승인이아니라제어길이민감도다. 기존packed input의19B envelope와ready grouping을남겼기때문에수신과typed소비의확인을공짜로합치지않았다.

## 회로·메모리·ARM 비용

|자원|현재 비교 근거와 추가 비용|
|---|---|
|FPGA logic|240은490LE/40LAB부족;새parser/control/mux의LE/LAB는미측정. 단독logic 수치를전체FIT에서빼지않음|
|M9K|240의54 + program4→6의2 − semantic base6→5의1 + receipt전용1 = **56/56**,여유0. 모두동시실현미검증|
|aperture|기존2×2KiB재사용;descriptor와값모두내부계상. tile과동시소유불가|
|map base|새FPGA full-map retained array0B. sparse수신과SNES target shadow사용|
|raw 변환 추가|별도2048B raw base의2M9K를더하면58/56. 다른회수근거없이현재안과동시채택불가|
|ARM retained|word dirty 추가448B;233의1616B여유에서1168B,1024B기준위144B라는산술뿐. 새입력RUN/IRQ·stack미검증|
|SNES|기존WRAM/target·command list사용. 새typed decoder코드·임시상태·실제DMA setup/service시간미측정. ROM4/5/6KiB고정금지|

receipt256B를기존scratch의빈주소에그냥넣지않는다. 새memory/port/lifetime을확보해야하며여기서는1M9K전용시나리오를계상했다. 코드를더줄여program RAM을회수하거나source전용회로를줄이는가능성은별도증명이필요하다. 새FPGA 여유나mapper확장승인은없다.

전체planner를그대로FPGA로옮기는B는기존배열18,752B/최소17M9K가필요하고,이전의낙관적회수12M9K보다크다. 재설계된allocator의보편적하한은아니다. 입력227그대로출력만옮긴236의19ms이상실패도fullB전체의불가능증명으로사용하지않는다. 반대로SNES로planner까지옮기는안은geometry allocator/변환의실제CPU비용이없어60fps유리함을주장할수없다.

## 결정과 다음 검증

현재구조에서ARM으로압축해제를집중하는안은wire와ARM부담을늘린다. SNES에현해석·검증을유지하는안은입력장벽을보존한낙관적겹침에서도부족하다. **ARM은계획과게임의미검증,FPGA는좁은map 범위·receipt검증,SNES는bounded DMA·최종표시**라는분담을다음한정조사대상으로정한다. P2제품구현선정은아니다.

다음deliverable은같은954/970및952/955경계에서①각검사의담당과certificate/STOP수명,②tile drain→typed map→manifest certificate→SEAL순서의실제시각,③새SNES setup/service와ARM/parser의공동잔여예산,④semantic source+receipt+ROM의전체LE/LAB/M9K회수근거를결합한경계설계다. 이조건없이새RTL/FIT로뛰거나token/opcode미세수정을반복하지않는다. 최종VRAM burst가해결됐다고하지않는다.

생산227,진단5886B,기능240미배치,기각241/246/2472CPU,GBC164/save SRAM을보존했다. [분석기](../tools/analyze_nes_placement247.py),[집계](../analysis/placement247-verification.json),[497행비교](../analysis/placement247-frames.csv),[71행chunk](../analysis/placement247-chunks.csv). 직접소비입력215개hash를기록했다. 재현은 `python tools/analyze_nes_placement247.py --out <새 private 경로>`이며기존private probe가필요하다.
