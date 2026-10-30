# NES495 — 진행 응답·ROM 요청 경계의 공동 비용 검토

[검증·전체 비용](../analysis/status495-verification.json) · [현재 실기493](nes-hardware494-results.ko.md) · [다음 순서](nes-output487-plan.json) · [PR138](progress/pr-138.md).

## 판정과 선택 경계

495는 **실험 후보이며 실기 선택·새 전달본은 보류**한다. 현재 정상 실기는493/9.57fps, 원복·GBC/save도 그대로다.8B 진행 응답과 ROM 검사 요청의 중복 조건 제거를 실제 ARM·FPGA에 구현했고 기능·관련 timing은 통과했다. 그러나 같은 입력의 조건부65816/wire 일정에서 최종 표시 단축을 확인하지 못했다. 전송량 절감을 전체 성능 성공으로 승격하지 않는다.

12프레임의 같은 시작 시각은757.253156→757.250362ms로0.002794ms 단축,시작을4ms 옮기면753.253160→753.266476ms로0.013316ms 증가다. 같은 payload·픽셀·SNES 프로그램이며 VBlank·최종ACK를 유지했다. **이 모델에는 실제 ARM busy-poll/IRQ/source ROM 시간이 없고, 실제plan마다 bulk packet을 하나씩 만든다.** 실제tile_bulk206은 같은kind·연속slot·2048B 이하를 묶을 수 있으므로 실제chunk 일정과 동일하지 않다. 이 결과로 실기 단축이 없다고 단정하거나 후보를 전체 기각하지도 않는다. 공통 일정 증명이 남았으므로 전달을 보류한다.

## 구현·유지한 검사

기존 E0는20B로flags/accepted/retired/ACK12/CRC8을 한 번에 반환한다. 새 **EB는8B:dummy/F8/flags/acceptedBE16/retiredBE16/CRC8**이며 첫6응답 byte의CRC를 검사한다. 기존152bit snapshot과 직렬CRC 상태·주소 선택을 재사용한다. 별도snapshot RAM/CRC FSM·새FIFO·별도clock은 없다. E0/E1 및 기존SNES ABI4891은 유지하며 새 ARM은 EB 지원FPGA와 짝으로만 사용한다.

ARM은credit polling에서EB를 사용한다. SEAL 대기에서도EB로진행을보고retired==sent가 된 뒤 **기존E0 전체ACK를 반드시 다시 읽어op/sequence/serial/generation/서명을 검사**한다. 해당구간에ARM이새E1을발행하지않으므로empty 뒤ACK identity는안정적이다. 다른drain·초기화의E0와range/CRC/서명·STOP/guard·최종ACK 이후commit/EA·VBlank·메뉴복귀는유지한다. FPGA는기존처럼각SNES ACK를head와대조한뒤에만credit을반환한다. EB는소비완료가아닌저장승인을표시로오인하도록바꾸지않는다.

첫전체배치는관련setup -0.249ns로기각했다. 병목은새CRC가아니라 **check_next[18]→ROM reader remaining**이었다. `nes_rom_boot`가physical reader로넘기는중복raw_ready/address_valid/check_failed gate를삭제했다. physical controller의owner_valid/IDLE 검사는그대로이며,원래check_failed의owner/range/START 충돌검사는동일한mem_clk edge에유지한다. 잘못된요청은등록된CE/OE가활성화되기전에reader reset으로취소된다. 유효읽기의SETUP/16ACTIVE/HOLD/RELEASE·표본edge·태그·응답은바꾸지않는다. 같은제약·seed로다시전체배치를측정했으며seed/false-path 조정은없다.

## 전체 비용과 시간 근거

| 항목 | 정상493 | 실험495 |
|---|---:|---:|
| Whole Lite LE /여유 | 15272 /136 | **15121 /287** |
| 조합논리/FF | 14078 /8392 | **14097 /8394** |
| logical RAM/M9K | 264800bit /51 | 동일 |
| 관련구현 setup/hold | +0.183/+0.168ns | **+0.046/+0.164ns** |
| 관련nominal setup/hold | +0.224/+0.168ns | **+0.249/+0.164ns** |
| ARM firmware/Flash여유 | 212844B /148B | **212896B /96B** |
| ARM BSS/RUN | 18572B /31848B | 동일 |
| SNES body/program | 4311B /5120B | **byte 그대로** |

조합논리는19개,FF는2개늘었다. LE151개감소는이번whole FIT의묶임/배치결과이며제어151개삭제성과가아니다. 기존snapshot의재사용과요청gate삭제를확인했어도단독LUT절감으로해석하지않는다. per-function static stack은status72/send296/init40B 등동일하며full RUN/IRQ stack 증명은아니다. 전체reset/CDC/IO/electrical signoff도여전히미완료다.

실제linked495의12개기존ownership/STOP/token/ACK guard와6개진행CRC/header/flags/counter/최종fullACK 반례를통과했다. 같은고정poll fixture에서busy0/1/3/10/75회는전체wire16/28/52/136/916B를줄였다. 반면credit 압력이없고즉시최종완료한경우에는추가E0 때문에 **8B 증가**한다. 이저지연회귀도선택근거에포함한다. 같은E1 payload를유지했고오류뒤추가SPI·commit이없다. 이instruction-clock fixture를물리시간으로환산하지않는다.

RTL queue의기존33packet·ACK12byte 각각의오류·partialACK·겹침·COMMON reset/STOP·위상·wrap 검사와EB snapshot/길이7·9거부가3조건각3949check로통과했다. ROM요청은2위상각48개valid read와12개fault/cancel,기존sticky 검사4096조건이같았다. 주소fault를삭제한잘못된구현은차등검사가거부했다. loaded 상태와PSRAM 값은seed했으므로384KiB 전체적재/CRC를재실행한증명은아니다.

선택ARM C/source·공유SPI·PSRAM/ROM경쟁·기존48965816을연결한한실행에서 **1표시/34ACK/2chunk·8512VRAM byte·STOP·observer**,기존과같은첫화면hash를확인했다. C/RTL/Mesen RPC는기능연결이며M4/IRQ의공통물리시계가아니다. client/SNES프로그램은정상489와같다. programmer/BI3/설치ZIP은생성하지않았다.

## 다음 작업과 재현

다음은 **실제ARM busy-poll + tile_bulk206의실제chunk +65816 소비를같은event ledger로연결**하는관문이다. 현재CPU fixture의plan당bulk를실제묶음으로바꾸고accepted/retired/실제DMA·SEAL/최종ACK를구분한다. E8/source 공급과ROM허용구간·IRQ/128us quiet를빠뜨린단축을만들지않는다. 이관문을닫기전추가compact opcode나작은word루프를계속조정하지않는다.

읽기전용12프레임profile에서upload는274.22ms,service는138.74ms,coverage는16.22ms,append는13.42ms였다. **inclusive이므로서로중첩되며더하지않는다.** ARM905..907의입력해석/계획instruction profile도기록했다. native 입력CRC16은이미table없는빠른식이므로기존bit-loop인것처럼다시최적화하지않는다. 현재493로그의FINAL_ACK call수를고정하면wire약2.71ms/표시절감투영이지만실제poll cadence와소비시각이바뀌므로예측/전체이득/60fps증명이아니다.

선택로컬은 `probes/nes-status495/candidate03`,temp의 `nes-status495-arm02`·`board02`·`rtl02`·`boot01`·`live03`·`profile02`·`schedule01`,로컬 `arm-test02/profile02.json/analysis02.json`이다. 이들hash와비용은공개검증JSON에고정한다. ARM01 SUBST실패,RTL01 구문실패,live01 입력schema/live02 구어댑터의EB 거부,첫negative timing과profile준비실패는보존했다. 라이선스부족이아니며추가라이선스는요구하지않는다. 정상Questa Starter FLOAT1좌석을순차사용하고Quartus는Lite만사용했다.

[prepare](../tools/nes_status495.py)는선택493 ARM·정상489보드를고정검증하고,`--direct-check`로경계교체를포함한다. [ARM](../tools/test_nes_status495_arm.py)·[SPI](../tools/test_nes_status495_rtl.py)·[ROM핀/취소](../tools/test_nes_status495_boot.py)·[공동기능](../tools/test_nes_status495_live.py)·[동일일정](../tools/test_nes_status495_schedule.py)·[SNES profile](../tools/profile_nes_status495_snes.py)·[ARM profile](../tools/profile_nes_status495_arm.py)·[분석기](../tools/analyze_nes_status495.py)를제공한다. 원본private source/고정입력·도구의미이식범위는[재현안내](../cores/nes/REPRODUCING.ko.md)를따른다. 바이너리/ROM/원시로그/라이선스를Git에넣지않고정상493·489및기존원복·save를보존한다.
