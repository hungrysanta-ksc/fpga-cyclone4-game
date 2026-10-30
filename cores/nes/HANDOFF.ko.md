# 현재 NES 인계

PR138 merge `7e9699fb5d3ce4617495c204aa04d194cb09798d`와 감사499 head의 master 도달을 확인했다. 현재 `codex/nes-capture-correctness-500` / [PR139](../../docs/progress/pr-139.md)에서 진행한다. 먼저 [502 실기 안내](../../docs/nes-mmc502-trial.ko.md) · [전달본](../../analysis/capture502-package.json) → [502 행 소유권·소비 비용](../../docs/nes-capture502-contract.ko.md) → [검증](../../analysis/capture502-verification.json) → [A1–A4 계획](../../docs/nes-audit499-plan.json)을 읽는다. 감사499의 보류 목록은 유지한다.

## 현재502 — 실기 전달본 준비, 결과 대기

501의 행 복구를 유지하고, visible 전환과 다음 행 fetch 전환의 raw 소유권을 나눴다. 기존27조건 중10조건이3→2행으로 줄었고 필요한4행은 모두 보존한다. 정상33/반례12종,raw15,360픽셀/native241,956이벤트 비교가 통과했다. 주소/DATA/ROM·완전한 행/세대·STOP·조기 query 검사는 유지했다.

같은 한 cold 장면의 실제 source를493 M4 수신·planner·serializer에 넣고493 65816으로 소비했다. 수신SPI330B/E1 1797B 및 ARM 명령 수가 줄었고 최종RGB가 동일했다. 같은 시작 시각을 둔 두 위상에서 최종ACK 단축은0.20347ms/16.82504ms다. 실제공유ARM/IRQ/ROM·연속일정·실기FPS가 아니다. 기존257plan→3bulk 묶음과 VBlank를 포함한 endpoint 모델이다.

Lite board01:15,287LE/14,135comb/8,399FF/264,816bit/51M9K,잔여121LE.501 대비−21LE/+2comb으로 packing 차이이며 제어 삭제가 아니다. 관련setup+.353/hold+.142ns,제약/seed 그대로다. `equivalence01/boundary02/guards01/export501-02/export502-02/arm01/cpu01/cpu02/board01`이 선택 증거다. export501-01의 시험용 선언순서 컴파일 실패는 보존했다.

`MMC502-CAPTURE.zip`은 `probes/nes-capture502/trial01`에 있다. ARM01의781개 함수/주소/크기/명령은493과 같고 파일명만502다. 기존502 fit을 CPF/BI3로 변환하고 실제FatFS/프로그래머로RBF510,856B 일치를 확인했다. GPIO/DONE은 모델이다. installer/로그 이름은502,02-RESTORE493 및이전복구는byte보존했다. [제작검증](../../analysis/capture502-release-verification.json) 참조. programmer01의sandbox DLL 실행실패는02의정상환경시험과구분한다. 새Questa/FIT는없다.

**다음 순서:** 같은 동선의493/502 수집·표시·메뉴 로그를 받고 candidate/profile/ABI부터 확인한다. 단계DWT/SPI와 최종ACK를 비교하되중첩counter를더하지않고 generation차이를전체거부수로세지않는다. 결과로A2전체예산을갱신한다. 변경없는bounded/FIT 재실행이나498/status/FSM 혼합을하지않는다. 실기4939.57fps는유지하며502실기성공/성능/A1전체완료는아직아니다.

## 현재 실기 선택

| 항목 | 고정 기준 |
|---|---|
| 구현 | MMC493,source commit54bdc1fe8521b742944d59bda20294d59716ad90 |
| ARM | probes/nes-boot493/ARM01/src,491 query 변경 유지·493 label;SHA256 6e780cecb815066caeaefcf4294d0f20798d72d1e2d294b9bc552a65a12f1ae9 |
| FPGA | 정상489 board02/SNES byte동일,493 파일명;BI3 SHA256 257b9686fa68ab11712b443728dc24c6ea7b561674a7ad2905ecb36f63349119 |
| ROM/ABI | 원래 SMB3(J),CRC5a04eed7/profile7b/status3/client4891/4credit |
| 실기494 수신 | **60.07초575최종표시/9.57fps**,부팅50ms/실행·메뉴정상;첫레벨차이작음 |
| 단계 | 수신28.97ms/계획·타일33.05ms/SEAL·최종ACK41.33ms,op/quiet 중복합산금지 |
| FPGA 비용 | Lite15272LE/14078comb/8392FF/264800bits/51M9K,136LE·5M9K잔여;관련setup/hold+0.183/+0.168ns |
| ARM 비용 | text202801/data10040/BSS18572B,firmware212844B·Flash148B,RUN31848B/full stack·IRQ미증명 |

이전489는60.08초577회/9.60fps다. 이번과입력·장면이달라소수점차이를개선/회귀율로해석하지않으며지속성능향상은미확인이다. 이전485대기13.55/플레이포함8.22fps,NROM47623.84fps는별도조건이다. 정확한레벨전용FPS/p95/capture무손실/NES실시간속도는미측정이다. 완료수는native최종ACK 진행이며screen_frames는신뢰하지않는다. 실제설치바이너리hash는로그에없어전달본label/profile/ABI로연결한다.

## 종료·부팅 판정

493의마지막sink2/window3은SEAL status transfer의전송후guard에서60초제한이전파되는결합signature다. 실제linked493에서정상ACK commit/후guard제한/진짜IO실패3가지를실행해result0/1/3을구분했고오류뒤추가SPI·표시없음을확인했다. 로그16negative와이전489-label12negative를거부한다. trace576=표시575+미완료1,마지막SEAL pending/ACK미공개·failed_transfers/CRC/abort0을요구하며모든error3을허용하지않는다. 실제물리종료순간재현은아니다.

492의5초ready timeout은493에서회복됐다. 새491/492 FPGA·word DMA/MVN은계속보류한다. 493성공만으로492단일원인을확정하지않는다. [492 실패](../../analysis/boot493-hardware492.json)·[493 제작계약](../../docs/nes-boot493-contract.ko.md).493 package/verification의미확인은제작시점스냅샷이며현재실기는494를따른다.

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
