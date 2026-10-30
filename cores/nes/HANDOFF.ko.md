# 현재 NES 인계

PR137 merge29815faa3887a035091e3169ffa0f751dda3de44의 master 도달 확인 뒤 `codex/nes-consume-schedule-491` / [PR138](../../docs/progress/pr-138.md)에서 진행한다. 먼저 [495 후보 판정](../../docs/nes-status495-contract.ko.md)·[검증](../../analysis/status495-verification.json)·[실기494 분석](../../docs/nes-hardware494-results.ko.md)·[측정](../../analysis/hardware494-mmc493.json)·[현재 계획](../../docs/nes-output487-plan.json)을 읽는다. 현재 정상 동작 기준은493이다.

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

## 실험495: 기능·관련 timing 통과, 전달 보류

EB8B 진행 응답은 기존 snapshot/CRC를 재사용하고 마지막 E0 전체ACK를 유지한다. ROM 요청의 중복 gate를 제거하되 기존 owner/range/START 오류·STOP 취소·유효 CE/OE edge는 유지했다. M4 기존12/추가6반례, RTL queue3조건 각3949검사, ROM2위상·4096fault, 실제 C/RTL/기존65816 첫표시34ACK·STOP를 통과했다. loaded ROM 상태를 seed한 기능 연결이며 전체384KiB 재적재·공통 물리 시계 증명은 아니다.

Whole Lite15121LE/14097comb/8394FF/51M9K, 관련 setup+0.046/hold+0.164ns다. LE151개 감소는 packing 결과이며 comb는19개 늘어 제어151개 순삭제로 해석하지 않는다. Flash96B 잔여, BSS/RUN/SNES body는 그대로다. **실기493 비용표를 이 후보 값으로 교체하지 않는다.**

동일12프레임 최종표시는0.002794ms 단축,시작4ms 이동은0.013316ms 증가로 유의미한 전체 개선이 없다. 현재 CPU/wire 모델은 실제 M4 busy-poll·IRQ/sourceROM과 실제 연속tile 묶음을 포함하지 않는다. 따라서 후보를 실기 선택하거나 물리 성능이 나빠졌다고 단정하지 않는다. 새BI3/programmer/ZIP 없이493을 유지한다. [상세 판정](../../docs/nes-status495-contract.ko.md).

## 다음 작업 순서

1. **493을 정상 실기 기준으로 유지한다.** [설치/원복](../../docs/nes-mmc493-trial.ko.md)·[manifest](../../analysis/boot493-package.json). 사용자가ZIP을설치하고TXT를반환하는방식이다.
2. 실제 M4의 E0/EB busy-poll·128us quiet/IRQ와 실제tile_bulk206의 같은kind·연속slot·2048B 묶음을 기존65816 소비의 같은event ledger에 연결한다. plan당 하나의bulk를 만드는 현재fixture를 실제chunk로 대체한다. source/ROM 공급·저장credit·실제DMA소비·SEAL/최종ACK·VBlank를 구분하고493/495를 동일 입력·시작위상으로 비교한다. MCU_RDY는external_memory_ready다.
3. 표시대기 중 다음입력 수신 후보는 receiver/video의 실제수명을 확인한다. 현재receiver는 별도workspace이고 consumed()는 COMMITTED→IDLE지만 generation·retire·종료통계는 마지막ACK 뒤에도 참조한다. 이전표시identity를고정하고SPI guard 재진입·STOP·수신중오류를막는범위부터 정한다. 안전성이 입증되기 전receiver를 덮거나 다음계획을 실행하지 않는다.
4. actual ARM·SPI·IRQ·ROM·65816 전체시간 개선과 부팅경계 확인 뒤에만 다음번호paired 실기를 전달한다. 실기493은Flash148B/136LE, 실험495는Flash96B/287LE 예산이다. 전체 reset/CDC/IO 승인은 별도다. 새word 경로는 부팅문제를 좁히기 전 재도입하지 않는다.

## 근거·보존·재현

- 현실기raw3TXT는로컬 `probes/nes-hardware494/run01`/receipt.json,linked종료termination02·parser01·analysis02.json. DWARF offset읽기실패termination01은통과근거가아니다. [분석기](../../tools/analyze_nes_hardware494.py)·[종료검사](../../tools/check_nes_hardware494_termination.py).
- 현재소스/ELF는 `probes/nes-boot493/ARM01/src`,FPGA assembly01,ZIP trial01/MMC493-BOOT-SPLIT.zip. [493 연결검증](../../analysis/boot493-verification.json)에781함수491동일/71frame2020packet489동일·old489 BI3 byte동일을고정했다.
- [491 개발계약](../../docs/nes-consume491-contract.ko.md)·[검증](../../analysis/consume491-verification.json)의actual M4 71상태/12guard/8burst·CPU71 모델7.25%/108unit/공동첫화면/5124bus 근거는보존한다. 새SNES를보류한493에7.25%를적용하지않는다.
- 이전489 선택은 `probes/nes-output489` candidate03/ARM02/audit01/client04/assembly01/trial02,ASCII board02/loader01/live01/bootbus01. [489 계약](../../docs/nes-output489-contract.ko.md)·[실기490](../../docs/nes-hardware490-results.ko.md).
- 이전485는 `probes/nes-supply485/ARM03/src`,FPGA `probes/nes-mmc482/candidate01/board`;[485 계약](../../docs/nes-supply485-contract.ko.md)·[실기486](../../docs/nes-hardware486-results.ko.md)·[재현 의존성](REPRODUCING.ko.md).raw/영상/ROM/도구가clone에포함된다고가정하지않는다.
- 원본소스·상용ROM·개인save·영상·라이선스·원시로그·패키지바이너리는Git에넣지않는다. 공개JSON에는파일명/크기/hash와파생카운터만둔다. 493/489/485/482/476/164/467 원복·GBC164/G13C44/0.9.0·save를보존한다.
- 독립CRC/coverage·epoch/generation/token·credit와실제DMA소비의구분·STOP/staleDONE/ACK 차단·최종ACK 뒤commit/EA·base/menu를유지한다. exportCOMMIT 뒤다음capture는이미시작하며표시중receiver를덮지않는다.
- 전체NES/MMC4/5·60fps·지속capture무손실·p95·NES실시간속도·fullstack/IRQ·전체reset/CDC/IO는미완료다. Quartus Lite/Questa Starter FLOAT1좌석순차실행을유지하며변경없는정상시험·license smoke는반복하지않는다.
