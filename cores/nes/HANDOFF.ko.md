# 현재 NES 인계

PR139 merge `46c0cc962397b3e757c838164b70b75fe73090a6`와head의master도달·tree일치를확인했다. 현재 `codex/nes-bandwidth-dma-budget-504` / [PR140](../../docs/progress/pr-140.md)다. [504 비용·교체 경계](../../docs/nes-budget504-contract.ko.md) · [실행 계획](../../docs/nes-budget504-plan.json) · [503 실기](../../docs/nes-hardware503-results.ko.md)를 먼저 읽는다.

## 현재505 — 선행 DMA 기능 검증, 실기 승격 보류

[505 계약](../../docs/nes-early505-contract.ko.md)과[검증](../../analysis/early505-verification.json)을 먼저 읽는다. 실제65816의 불변prefix DMA를 추가body205B/WRAM4B로 구현했다. 최종재전송을 삭제하고 STOP/실패의 tentative bank 무효화를 연결했다. 연속12×2위상 RGB·VRAM양동일/6거부/오염boot/4KiB입력정체를 통과했다.

전체12개는약16.6ms 빨라졌지만 첫frame뒤11개는−0.012758/+0.032686ms로 사실상 같다. 고립된 prefix·opcode·위상 미세조정을 반복하지 않는다. 다음은 wire본문/packet준비의존성을 바꾸는 후보를 실제ARM·SPI·IRQ·ROM과 연결해 지속warm 예산으로 판정한다. 실기502/10.59fps·기존메뉴복귀기준은유지한다. 변경ROM Quartus/새전달본은없다. private근거는probes/nes-early505, source/실패/선택raw와archive01을보존했다.

## 현재504 — A2 비용 분해와 다음 실행 경계

새PC계측은기존65816의픽셀·최종ACK시각을바꾸지않았다. 과거연속12개에서SEAL→upload2.24ms/upload→ACK23.65ms,wait1~3회다. 실제502warm/ARM·IRQ·ROM공통시간이아니다. 조회제외5911.51B/표시이며12mswire예산까지1974.01B부족하다. 전체7533B이력cache는M9K최소7개로남은5개에안맞는다. 공통generation은actual cold332record의Pythonbyte시제품만통과했다.

504에서정한실험은packet완료뒤불변dirty-list prefix만현재VBlank에들어갈때선행DMA하고,열린tail/SEAL최종검사/ACK를유지하는실행실험이다. 기존cursor초기화·최종재전송을대체하며추가SNESbody512B/WRAM8B/newM9K·ARM실행코드·FPGA제어0을할당했다. 미달성예산이며전체60Hz gate는미통과다. 새FW/합성/전달본없이실기502를유지한다. [504 검증](../../analysis/budget504-verification.json).

## 현재502 — 첫 실기 성공, A2 비용 검토로 진행

60.07초636회 최종 표시/**10.59fps**,실행·메뉴 복귀 정상이며 사용자는 확실한 개선을 보고했다. 이전493575회/9.57fps와 동선이 같지 않아 관측+10.61%를 인과율로 쓰지 않는다. 수신22.14/계획·타일31.32/SEAL·최종ACK40.27ms다. 보존history8전이의fetch/compact/raster/ROM 오류는0이며mask0거부4/회복4가 남는다. 전체capture건강·거부율·레벨별FPS는 미증명이다.

마지막637번째 입력의SEAL은60초guard 제한(runtime1/window2/sink2)으로 미완료다. 실제502 ARM의정상/guard/postguard/IO4조건과로그16반례를 확인했고표시636회에더하지않았다. 새FW/ZIP/합성/Questa는없다. 원시로그/receipt/termination01은로컬 `probes/nes-hardware503`에보존했다.

## 현재 실기 선택

| 항목 | 고정 기준 |
|---|---|
| 구현 | MMC502 RTL commit485a946fba53eb0c70b72c5147dcaf4a1f70629c |
| ARM·SNES | ARM502-01,493에서파일명만변경/781함수동일;493/4891 client 유지 |
| 보드 | board01 Lite15287LE/14135comb/8399FF/264816bit/51M9K,121LE여유 |
| 관련 timing | setup+.353ns/hold+.142ns;full reset/CDC/IO 미승인 |
| MCU | firmware212844B/Flash148B/RUN31848B;fullstack·IRQ 미증명 |
| 전달/실기 근거 | [package](../../analysis/capture502-package.json) / [503](../../analysis/hardware503-mmc502.json) |
| 후속 배포 | 사용자 별도백업 보유: 다음 시험판은RESTORE폴더생략,기존ZIP삭제금지 |

[502 bounded검증](../../analysis/capture502-verification.json)은정상33/반례12,raw15360pixel/native241956이벤트,필요한4행 보존을확인했다. 한cold source→493M4→65816에서RGB동일·수신−330B/E1−1797B,같은시작두위상ACK−.20347/−16.82504ms는모델경계이며실기개선율이아니다. [제작검증](../../analysis/capture502-release-verification.json)의hardware_verified=false는제작시점기록으로유지한다.

**다음 순서:** A2본문/framing·늦은VRAM DMA·계획공급을같은ARM/SPI/IRQ/ROM/VBlank일정으로예산화한다. 조회제외wire18.02ms/전체94.45ms(60Hz까지77.78ms)가남는다. 실제삭제할제어와121LE/Flash148B예산을명시하고중첩op/quiet를합하지않는다. 기존498/status/FSM 미세조정은자동승격하지않는다. mask0거부의전체원인·동일동선재검증은열린항목이지만변경없는FIT/Questa반복으로대체하지않는다.

## 최신498: 입력 시작과 이전 표시 소유권 분리

END 수락과 drain은 exporter의 IDLE 시작에서만 확인한다. 진행 중 ROM 접근으로 drain이 내려가도 기존 lease/END로 입력을 유지한다. ARM은 최종 ACK 대기 중 기존 receiver를 COMPLETE까지 채우고, 이전 video/sink identity를 보존하며 old ACK/EA 뒤 다음 step에서만 COMMIT한다. 첫 후보의 연속 drain gate는 실제 공동 실행에서 exporter ABORT→old lease fault를 일으켜 기각했다.

linked M4 정상 수신과5반례, END/lease/exporter4mutant, 고정 MMC3 fixture의 C/RTL/기존65816 두 표시·68ACK·4bulk·STOP을 확인했다. COMMIT12→ACK/EA12→COMMIT13→ACK/EA13 순서다. 첫 RGB는495와 동일하며 두 번째 전체pixel oracle·실제 M4/IRQ 공통시간·물리 메뉴 복귀는 새로 증명하지 않았다. live04의 후처리1frame 기대값은2로 고쳐 저장된 완료 산출물을 재검사했고 원래 실패 기록을 보존했다.

전체 Lite15132LE/14105comb/8394FF/51M9K·잔여276LE,관련setup+.084/hold+.147ns,Flash8B다. 실기493 대비−140LE/+27comb/+2FF로 제어140개 삭제가 아니다. callback은728B stack을 관찰했고 전체 IRQ 중첩은미확인이다. source 보드와 비용 보드의 차이는 loader WRITE next-state의 late blocked 조건식이며512조합+mutant로 동등성을 고정했다.

498 당시 다음 순서는 공통 M4·IRQ·ROM/65816 시간 연결이었다. 현재는499의 수집 정확성 우선 계획으로 대체했다. 수신 비용이 SEAL 안으로 이동했으므로 phase를 단순 합산하지 않는다. 새 실기 전달본/60fps 향상은 선택하지 않았고 정상493·9.57fps와 원복을 유지한다.

## 실험495: 기능·관련 timing 통과, 전달 보류

EB8B 진행 응답은 기존 snapshot/CRC를 재사용하고 마지막 E0 전체ACK를 유지한다. ROM 요청의 중복 gate를 제거하되 기존 owner/range/START 오류·STOP 취소·유효 CE/OE edge는 유지했다. M4 기존12/추가6반례, RTL queue3조건 각3949검사, ROM2위상·4096fault, 실제 C/RTL/기존65816 첫표시34ACK·STOP를 통과했다. loaded ROM 상태를 seed한 기능 연결이며 전체384KiB 재적재·공통 물리 시계 증명은 아니다.

Whole Lite15121LE/14097comb/8394FF/51M9K, 관련 setup+0.046/hold+0.164ns다. LE151개 감소는 packing 결과이며 comb는19개 늘어 제어151개 순삭제로 해석하지 않는다. Flash96B 잔여, BSS/RUN/SNES body는 그대로다. **실기493 비용표를 이 후보 값으로 교체하지 않는다.**

동일12프레임 최종표시는0.002794ms 단축,시작4ms 이동은0.013316ms 증가로 유의미한 전체 개선이 없다. 현재 CPU/wire 모델은 실제 M4 busy-poll·IRQ/sourceROM과 실제 연속tile 묶음을 포함하지 않는다. 따라서 후보를 실기 선택하거나 물리 성능이 나빠졌다고 단정하지 않는다. 새BI3/programmer/ZIP 없이493을 유지한다. [상세 판정](../../docs/nes-status495-contract.ko.md).

## 496 모델·소유권 교정

[496 근거](../../docs/nes-schedule496-contract.ko.md):219계획을실제규칙의32묶음으로교정,동일12픽셀·4조건통과.657.420ms는새가속이아닌fixture교정이다. 실제lease RTL에서다음캡처는허용하되export는이전retire까지차단됨을확인했다. stale/STOP·잘못된early-export mutant를검사했다. ARM만앞당겨서는수신겹침이불가능하다. S9는499 재계획으로 보류하며 당시에는실제M4 complete485 단일bulkPending/E8/E0·IRQ/ROM 시각을연결해야한다. source export시작과COMMIT 분리·기존identity 보호를함께검토한다.

## 497 실제 M4 대기 연결

[497 검증](../../docs/nes-bulk497-contract.ko.md):linked493의emit/complete485/finish를2bank 묶음 endpoint에연결해36조건·9반례를통과했다.32묶음의모든소비후FINISH,표시ACK 없는retire 거부를확인했다. 소비는지정instruction 지연으로실제65816/IRQ/ROM 공통시간은아직미완료다. reader_drained는arb_idle이므로새export 허용에충분하지않다. generation에묶인END 수락+drain과oldACK/EA 뒤새COMMIT을구분해야한다. 기존493·예산·전달본을유지한다.

## 다음 작업 순서 — 감사499가 우선

1. **A1 수집 정확성:** 실기493 마지막16전이에서 fetch01/04/06 거부8episode와 회복8episode를 확인했다. low/high·주소·PPUMASK 중단/재개·실제픽셀/row commit 경계를 짧게 재현한다. 메뉴 정상/CRC0과capture 건강을 구분한다. V3 이력으로 전체 거부율·손실시간을 계산하지 않는다.
2. **A2 구조 예산:** 반복geometry 전송·RUN SPI 설정·늦은metadata/VRAM DMA의 구조를 비교한다. 관측 비조회wire17.959ms는16.667ms를 넘는다. 삭제할제어·Flash/LE/stack과 모든필수byte를 먼저 확정한다. 작은status/FSM 실험 재개 조건은499 보류표를 따른다.
3. **A3 한 후보 구현:** A1 원인/픽셀을 해결한 뒤 예산이 성립하는 구조 하나를 구현한다.493 기준으로498 차분 채택 여부도 명시한다. 독립검사·STOP·old identity·최종ACK/EA·VBlank 유지.
4. **A4 전체/실기:** 동일 입력·시작위상과 연속일정을 구분한다. 실제 전체시간·부팅 검증 뒤 새번호 전달본과493 원복으로 두 번 비교한다. 사용자가ZIP 설치 후TXT를 반환한다. 현재 새 실기 설치 요청은 없다.

## 근거·보존·재현

- 현실기raw3TXT는로컬 `probes/nes-hardware494/run01`/receipt.json,linked종료termination02·parser01·analysis02.json. DWARF offset읽기실패termination01은통과근거가아니다. [분석기](../../tools/analyze_nes_hardware494.py)·[종료검사](../../tools/check_nes_hardware494_termination.py).
- 현재소스/ELF는 `probes/nes-boot493/ARM01/src`,FPGA assembly01,ZIP trial01/MMC493-BOOT-SPLIT.zip. [493 연결검증](../../analysis/boot493-verification.json)에781함수491동일/71frame2020packet489동일·old489 BI3 byte동일을고정했다.
- [491 개발계약](../../docs/nes-consume491-contract.ko.md)·[검증](../../analysis/consume491-verification.json)의actual M4 71상태/12guard/8burst·CPU71 모델7.25%/108unit/공동첫화면/5124bus 근거는보존한다. 새SNES를보류한493에7.25%를적용하지않는다.
- 이전489 선택은 `probes/nes-output489` candidate03/ARM02/audit01/client04/assembly01/trial02,ASCII board02/loader01/live01/bootbus01. [489 계약](../../docs/nes-output489-contract.ko.md)·[실기490](../../docs/nes-hardware490-results.ko.md).
- 이전485는 `probes/nes-supply485/ARM03/src`,FPGA `probes/nes-mmc482/candidate01/board`;[485 계약](../../docs/nes-supply485-contract.ko.md)·[실기486](../../docs/nes-hardware486-results.ko.md)·[재현 의존성](REPRODUCING.ko.md).raw/영상/ROM/도구가clone에포함된다고가정하지않는다.
- 원본소스·상용ROM·개인save·영상·라이선스·원시로그·패키지바이너리는Git에넣지않는다. 공개JSON에는파일명/크기/hash와파생카운터만둔다. 493/489/485/482/476/164/467 원복·GBC164/G13C44/0.9.0·save를보존한다.
- 독립CRC/coverage·epoch/generation/token·credit와실제DMA소비의구분·STOP/staleDONE/ACK 차단·최종ACK 뒤commit/EA·base/menu를유지한다. 493은exportCOMMIT 뒤다음capture가시작하지만표시중receiver를덮지않는다.498만별도old identity로수신재사용을허용하며아직실기미선택이다.
- 전체NES/MMC4/5·60fps·지속capture무손실·p95·NES실시간속도·fullstack/IRQ·전체reset/CDC/IO는미완료다. Quartus Lite/Questa Starter FLOAT1좌석순차실행을유지하며변경없는정상시험·license smoke는반복하지않는다.
