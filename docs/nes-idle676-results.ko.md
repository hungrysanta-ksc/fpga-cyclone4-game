# 676: map 뒤 입력 진행과 마지막 plan 묶음의 허가

MMC666을 판정 기준으로 두고675의 첫 zero 소비·BG plan 허가·후속 큰 묶음을 그대로 유지했다. 긴 map tail의 검사된 소비 ACK 뒤 실행하던40회 대기를 한 번의 제한된 입력 처리로 대체했다. 후보는 전체 링크 ARM에서 실행하며 FPGA·65816은665와 동일하다.

**판정: 두 후보 모두 기능 통과·시간 게이트 실패다. MMC666을 유지한다.** 입력 단독과 마지막 plan 허가 결합을 각각 두 위상 53화면씩, 총 212화면 재생했다. 결합 후보도 952를 3회로 회복하지 못했으므로 새 설치본은 만들지 않았다.

| 같은 작업량의 비교 | MMC666 | 입력 단독676 | 마지막 plan 허가 결합676 |
|---|---:|---:|---:|
| 952 표시 간격, 위상1/2 | 3/3 VBlank | 4/4 | 4/4 |
| 밀집951–955 합계, 위상1/2 | 15/15 VBlank | 16/16 | 16/16 |
| 밀집 평균 변화, 위상1/2 | 기준 | +3.374/+3.377ms | +3.272/+3.282ms |
| 957 마지막 ACK 변화, 위상1/2 | 기준 | +16.924/+16.905ms | +16.948/+16.711ms |
| 952 선행 map DMA | 1,536/1,536B | 192/192B | 192/192B |
| ARM Flash / 여유 | 212,496/496B | 212,704/288B | 212,688/304B |

두 후보 모두 911 마감·951의 246번 공개선·957 최종 대기 0회를 유지했고, 출력 바이트·map/OBJ 작업량·최종 표시 ACK는 독립 대조와 일치했다. 결합 후보의 952 SEAL 수락은 이전 표시 뒤 43.554/43.365ms로 MMC666의 46.373/46.095ms보다 빠르다. 그러나 남은 DMA가 두 VBlank로 나뉘어 최종 표시는 50.159/50.141→66.186/66.172ms로 늦어졌다. SEAL·tile의 단독 개선을 전체 표시 개선으로 계산하지 않는다.

## 입력 처리 단독 결과

두 위상 106화면의 출력과 독립 검사는 통과했으나, 952가 두 위상 모두 4 VBlank여서 기각했다. MMC666 대비 밀집 평균은 +3.374/+3.377ms, 957 마지막 ACK는 +16.924/+16.905ms다. 911 마감·951 공개선·957 최종 대기 0회는 유지했다. [단독 검증](../analysis/idle676-input-verification.json)

952의 map drain 뒤 첫 ordinary 요청까지는 675의 6.561557/6.561366ms에서 두 위상 모두 0.716464ms로 줄었다. 그중 실제 다음 입력 한 블록의 수신·검사·복원은 0.621511ms다. 그러나 callback과 빈 큐 구간 모두 실제 선행 DMA는 0회였다. 이 구간은 직전 표시 뒤 36.8–37.6ms로, 이미 VBlank를 지난 뒤였다. map 선행 전송은 MMC666의 1,536B에서 두 위상 모두 192B로 감소했다.

마지막 tile ACK는 약 10ms 빨라졌고 SEAL 수락도 약 2ms 빨라졌지만, 업로드에 남은 map·tile·raw가 다음 두 VBlank에 나뉘었다. 따라서 최종 추가 대기 0회를 유지해도 전체 표시 간격은 악화됐다. 입력 수신 시간을 제거하면 그만큼 DMA가 진행된다고 계산할 수 없다.

## 추가로 확인한 마지막 묶음의 대기

단독 후보의 952에서는 13개 record를 담은 마지막 E9가 준비된 뒤에도 약 6ms 대기했다. 첫 E8 응답에는 쓰기 가능한 plan bank와 아직 소유 중인 BG tile descriptor가 동시에 있었다. 기존 ARM은 END 하나만 담긴 패킷에만 쓰기 허가를 보존하고, BG/OBJ와 END를 함께 담은 마지막 큰 묶음에는 이를 버렸다.

결합 후보는 CRC로 framing된 `ending` 묶음에도 같은 bank 허가를 보존한다. 기존 tile identity·토큰·소비 ACK·2슬롯 backpressure와 최종 표시 ACK는 그대로 유지한다. 새 record를 추가하거나 묶음을 잘게 나누지 않는다. 실제 RTL에서 이전 타일을 소유한 채 13개 마지막 record를 수락하고 16개 타일을 순서대로 읽고 완료하는 두 host 위상, 대기 중 STOP과 cold 재시작을 통과했다. 이 제한 RTL fixture의 BG ROM 값은 모델이며 전체 OBJ 캡처·화면 시간 증명은 아니다.

실제 결합 재생에서 952의 END 함수 대기는 5.939/6.153→1.142/1.142ms로 줄었다. 마지막 tile ACK도 32.536/32.594ms로 MMC666보다 10.777/10.669ms 빨랐다. 957의 마지막 tile ACK 역시 두 위상 모두 약 9.6ms 앞당겨졌다. 하지만 952 map 뒤 입력 callback 중 실제 DMA는 여전히 0회였다. 타일 공급의 이득과 후속 큰 묶음 보존은 확인했으나, 요청한 952·밀집 간격·마지막 ACK의 동시 개선에는 실패했다.

## 구현한 경계

`nes_sink212_seal`의 map drain은 기존처럼 packet identity·retired credit를 확인한다. 이전 표시 이력이 있고 OBJ가 해당 조건까지 발행됐으면 새 reason4 callback을 한 번 호출한다. callback은 STOP/서비스 검사를 먼저 실행하고, 이미 COMMIT된 이전 입력의 수명을 해제한 뒤 기존7블록 선행 수신 예산 안에서 다음 입력을 한 번 poll한다.

입력이 있으면 실제D1 전송·CRC·ARM 복원·D2 반환·D0 반환 확인을 끝낸다. 입력이 없거나 이미 COMPLETE이면 기다리지 않고 복귀한다. 새D3/COMMIT·E1 출력·EA를 이 callback에서 발행하지 않는다. 복귀 직전에도 STOP을 검사한다. 이전 출력은 독립된 video/resident 문맥과 최종 표시 ACK를 계속 소유한다.

38회의 고정 휴지와 뒤2회의 수신 시도를 반복하던40회 루프를 제거했다. 기존 출력 큐를 비운 상태에서 유효한 입력 작업이 걸린 시간만 사용하며, callback 뒤에는 다음 ordinary를 발행한다. 추가 큐·타이머·버퍼나 DMA 완료를 가정한 credit는 없다.

**현재 E0 ACK는 map 수신·검사 완료이고 VRAM DMA 완료 신호가 아니다.** 새 경로는 큐가 빈 동안65816이 선행 DMA를 실행할 기회를 제공하지만, ARM이 DMA 완료 이벤트를 받아 기다림을 끝내는 새 프로토콜은 구현하지 않았다. 실제 DMA 발생 여부는 같은 일정의65816 `ppu_dma`·VBlank·최종 출력 기록으로 별도 판정한다. 데이터 수신 완료를 DMA 완료로 부르지 않는다.

## 안전 검사와 자원

- 실제 링크 ARM 입력 callback 8조건: 정상 한 블록, 입력 없음, 이미COMPLETE, 잘못된CRC, 잘못된D2 반환 확인, 처리 전STOP, D1 뒤STOP, D1 IO 실패를 확인했다. 정상은D0/D1/D2/D0만 실행하고, 실패 시새COMMIT/EA/출력은 없다. 데이터CRC나STOP 실패 뒤D2를 보내지 않는다.
- map-tail caller 5조건: 정상, OBJ 조건 미달, 잘못된credit, callback 중STOP, 잘못된최종ACK를 검사했다. 정상 callback은한 번,조건미달/credit실패는0번이다. 최종ACK가 맞을 때만뱅크 이력이 확정된다.
- 675의초기BG grant·소비 소유권12조건, routing/STOP12조건, 메뉴 준비·해제5조건과marker4조건도 새바이너리로 통과했다. 초기unit01은 시험기 DWARF에runtime 구조가누락돼실행전실패했고, 구조를실제ELF에서읽은guards02가선택본이다. 제품실패와구분해원시로그를보존한다.
- Flash212704B/free288B:675보다80B,MMC666보다208B 증가했다. data10040/BSS19544B와wait634의함수stack24B는동일하다. 전체 호출stack 상한을새로측정했다는뜻은아니다.
- 위 Flash 수치는 입력 단독이다. 결합 후보는 허가 조건을 단순화해 16B 작은 212688B/free304B이며, MMC666 대비 +192B다. 추가 static RAM은 두 후보 모두 0B다.
- 결합 후보는 실제 링크 ARM에서 마지막 13개 record의 정상/한 번 busy/잘못된 count·generation·token·CRC/발행 전 STOP 7조건을 추가로 통과했다. 초기 grant 12조건, 기존 END 9조건, 입력·caller 13조건, routing 12조건과 메뉴 경계도 같은 바이너리로 확인했다. `--trial666` 오기인 메뉴 시험 첫 실행은 실행 전 인자 오류였고, `--trial 666`으로 실행한 `joint-menu02`가 선택본이다.
- FPGA/65816 변경이 없어 기존665 전체보드15324LE·962LAB·56M9K와STA setup+0.511/hold+0.149/recovery+1.828/removal+0.393ns를 재사용한다. 새 FIT는 반복하지 않았다. 실제 같은 RTL에 큰 마지막 묶음을 보내는 소유권 시험만 추가했다. 외부IO 전체 sign-off·지속60fps·새 실기 메뉴 복귀는 별도 미완료다.

## 재현과 범위

`prepare_nes_idle676.py ../probes/nes-bg675/grant01 <새 빌드>`는675 firmware hash를확인하고 `nes_native_sink165.c`·`nes_native_runtime165.c`만수정한다. `build_nes_trial577.ps1 -SourceRoot <새 빌드>`로전체링크하고 `check_nes_idle676.py --arm <새 빌드>/src --out <새 JSON>`으로새경계를검사한다.

`--ending-grant`를 추가하면 `nes_plan_service200.c`의 마지막 묶음 허가 조건도 교체한다. 이 결합 후보는 `joint01`, 두 위상 재생은 `nes-idle676-joint1/joint2`다. `check_nes_tail676_arm.py`와 `check_nes_tail676_rtl.py`가 추가 경계 시험이다. RTL 시험은 허가된 Starter FLOAT wrapper 한 좌석에서 순차 실행한다.

`test_nes_idle676.py`는기존673 계측과동일한전체재생에readonly callback 진입/복귀관찰만추가한다. 큐가실제로비어있는지,수신token이0/1개만전진하는지,callback에서D0/D1/D2만발행하는지확인한다. 실제인자는로컬 `../probes/nes-idle676/replay.ps1`,결과는ASCII Temp의 `nes-idle676-input1/input2`다. 원본 `nes-ready673-b1/b2`와675의 `nes-bg675-grant1/grant2`를동시에대조한다.

두시작시각은7288416/7467100 master clock이며각905–957의53화면이다. 실제링크M4·65816에CPI2·SPI/IRQ모형·측정된반복ROM달력을연결한다. 독립map/OBJ/ordinary 바이트·VRAM·수신과최종표시ACK를비교한다. 실기26.84ms의임의분할이나물리FPS 환산은하지않는다. `analyze_nes_idle676.py`와[검증 JSON](../analysis/idle676-verification.json)이판정근거다.

원시재생·소스·전체ELF/firmware·경계시험과실패로그는별도private archive에보존한다. [보관요약](../analysis/idle676-archive.json). 기존설치본·RESTORE·상용ROM·세이브는변경하지않는다.

## 다음 한 단계와 중단 조건

다음은 952의 **map 수락과 실제 빈 큐 DMA 선택**을 이전 VBlank 안에 맞추는 경계다. 결합 후보의 첫 map은 17.490/17.555ms에 발행돼 원본보다 빠르지만, offset2048부터 후속 타일·credit와 교차하면서 마지막 map 수락은 35.986/36.030ms로 원본보다 2.861/2.625ms 늦다. 첫 map만 빨리 보내거나 map 전체 drain 뒤 시간을 확보해서는 놓친 VBlank를 되돌릴 수 없다.

현재 239/241번 선에서 192B만 선행 DMA된다. 원본의 1,536B와 차이인 1,344B는 DMA 데이터 이동만 최소 약 0.501ms이며, 설정·독립 검사·새 패킷/STOP 확인은 추가 비용이다. 다음 검토에서는 offset2048–3392의 준비·bulk 우선권·수락·큐가 비는 순간과 실제 DMA 선택을 함께 묶어, 원본의 수락 마감 33.125/33.405ms에 들어갈 예산을 먼저 확정한다. 확정된 map을 위한 슬롯 예약과 bulk 우선권의 충돌을 대조하되 기존 tile identity와 큰 plan 묶음을 깨지 않는다.

고정 대기 횟수·pair 크기·위상 상수를 다시 조절하는 반복은 보류한다. DMA 진행을 ARM에 공개하는 안이 필요하면 실제 읽기 완료 신호·CDC·STOP 무효화와 Flash/LE 비용을 먼저 정하고, E0 소비 ACK를 DMA 완료로 재해석하지 않는다. 검증된 순이득이 없으면 676을 제품에 섞지 않는다. 60fps·새 실기 성능은 아직 검증되지 않았다.
