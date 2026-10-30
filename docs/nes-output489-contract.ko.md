# NES489 — loader 허용 경계와 raw 직접 DMA

[검증](../analysis/output489-verification.json) · [전달본 manifest](../analysis/output489-package.json) · [설치/원복](nes-mmc489-trial.ko.md) · [PR137](progress/pr-137.md). **후속 실기 수신490:489 실행·메뉴 복귀 정상,60.08초577회/9.60fps.** [실기 분석490](nes-hardware490-results.ko.md)에서 비용·한계를 확인한다. 아래는 전달 당시의 기능/모델/timing 근거이며 제작 스냅샷은 덮지 않는다. 첫 레벨 가속·60fps는 미입증이다.

## loader setup 경로

488의 `check_failed`→`loader.byte_hold[7]` 경로는 실제 쓰기 허용과 inactive payload 저장이 같은 늦은 제어를 사용해 생겼다.489는 RECEIVE에서 DATA가 있으면 payload/address/chip/lane을 선행 저장한다. 이 값은 SETUP에 들어가기 전까지 PSRAM에 구동되지 않는다. **SETUP 진입·오류·STOP·count·WRITE/HOLD drain·reset은 기존 제어 그대로**다. SETUP/WRITE/HOLD 중에는 선행 저장하지 않아 이미 허용한 write의 data와 pulse를 보존한다.

따라서 무허용 상태의 내부 payload 값과 주소 핀은 이전과 다를 수 있다. chip-select/drive가 활성일 때의 data/address와 모든 상태·허용·오류·counter·pulse 제어는 같아야 한다. 이를 실제482 대비294912상태·1056연속 시퀀스·524288count·131072이전 오류 코드에서 비교했다. blocked STOP 오류, blocked 제어 우회, WRITE/HOLD data 덮어쓰기3종 잘못된 후보는 모두 시험이 잡았다. 원본 loader의 full384KiB 적재·CHECK CRC·readback을 불필요하게 다시 반복하지 않았으며, 외부적으로 달라진 inactive 샘플링을 register 완전 동일성으로 표시하지 않는다.

## 복원과 DMA 일정

paired ABI는 **4891**이다. raw1/2행은 **plane pair→사용 행→32tile→두 byte** 순서로 전송한다. 기존 압축 DATA/RLE·E1 CRC·4credit은 유지한다. 새 순서는64B 단위 반복도 모아 기존 RLE가 처리할 수 있다. raw3..7은 기존2048B fallback, raw0은 기존 scroll-only다. ARM은 expired bg_keys4096..4479를 재사용하고 canonical patch.chr를 보존한다.

65816은 compact bytes를 다시 tile 순서 WRAM으로 만들거나249B configuration tail을 복사하지 않는다. 기존 독립 검증기는 검증된 compact 길이에서 계산한 table pointer를 사용하며, mode/enable/길이/224행 합계/raw 행 수/coverage 검사는 그대로다. 실제 PPU HDMA도 그 table을 읽는다. low6plane은 VMAIN stride32와 native DMA로 비활성 raw VRAM에 쓴다.

- 초기 forced blank에서 양쪽 raw 영역4096B를 ROM header의 immutable zero byte로 지운다. 이는 프레임마다 반복하지 않는다.
- bank별2byte cache는 **암묵 plane/미사용 행의 패턴**만 인증한다. 색상은 캐시하지 않고 매 프레임 모두 보낸다. raw 데이터 영역은 A5000..57FF/B9000..97FF이며 normal BG/OBJ/map DMA 영역과 겹치지 않는다.
- 같은 행 수이면 low-plane384B(count2)만 갱신한다. 초기 zero 인증이면 필요한 plane6 FF만 추가한다. 행 수 변경/legacy 경로는 **수정 전에** 해당 bank 인증을 무효화한다. 부분 clear·DMA 뒤 STOP에서는 무효 상태를 유지한다.
- 새 인증은 성공한 표시 commit에서 기록하고 곧 최종 ACK를 발행한다. 이것은 ACK 공개 **뒤**의 별도 단계가 아니다. 그 구간에 새 service/STOP 지점을 넣지 않았고, 오류·중간 STOP에서 표시 identity와 픽셀은 이전 것으로 남는다. ARM resident commit/EA는 계속 실제 최종 ACK를 기다린다.
- cold clear와6개 low-plane DMA·필요한 high-plane DMA의 data뿐 아니라 각 DMA setup도 기존4192B VBlank 예산에 청구한다. visible DMA의 첫/마지막 write와 최종 reveal/ACK를 실제65816 PPU 상태로 검사했다.

새 SNES 문맥은1258..125F의8B: bank 인증2B와 프레임 문맥6B다. 새 framebuffer나 ARM global RAM은 없다. program body4311B를5KiB ROM에 배치하고, header는 별도 주소 remap으로 읽는다. ROM의FF/zero source와 전체code/header5124읽기·23위상을 실제 보드 RTL에서 확인했다.

## 같은 시작 시각의 시간

실제 linked ARM이 만든 패킷과 실제65816/PPU를 사용했다. 전송은4credit·2.625Mbps·20B 상태 가시성 모델이며, 다음 BEGIN은 앞 표시 최종 ACK 뒤다. 모든 비교는 baseline과489에 같은 시작 시각을 준다.

| 조건 | 기존 경로 | 489 | 감소 |
|---|---:|---:|---:|
| 12개,masterclock3000000 | 823.806ms | 757.253ms | **66.553ms /8.08%** |
| 같은12개,시작+4ms | 819.806ms | 753.253ms | **66.553ms** |
| 71개 연속 | 4234.845ms | 3903.397ms | **331.448ms /7.83%** |
| reset부터12개,시작0·초기 VRAM/cache 오염 | 863.647ms | 813.733ms | **49.915ms /5.78%** |

초기화도 무료로 빼지 않았다. 첫 packet poll은 baseline1038746→4891202060masterclocks로 약7.60ms 늦다. 늘어난 program copy/검사와 forced-blank 초기 DMA를 포함한다. reset부터의 비교에서도 최종 이득은 남았다.12개 총 VRAM DMA는51888→36144B(초기4096B 포함)다. 복원 준비는수십µs로 줄었고 실제 raw 복원은 위 DMA 일정에 포함한다.

이는 **물리 ARM·IRQ·공유 SPI·ROM 경쟁의 공통 시간 증명이 아니다.** actual C→source/ROM/SPI RTL→실제65816→STOP/base는 별도로 통과했으나 첫 raw0 프레임이다. 이 결과와 raw71개/다른 시작 위상에서 가장 좋은 숫자를 합쳐 물리 FPS를 만들지 않는다. 실제485의494플레이 프레임을 재생한 것도 아니다.

## 전체 비용

| 항목 | 488 →489 | 실제485/482 대비 |
|---|---|---|
| whole Lite LE/comb/FF | 15287/14081/8392→**15272/14078/8392** | +18LE/+29comb/FF 동일; **136LE 잔여** |
| logical memory bits | 289376→**264800** | +8192bits |
| physical M9K | **51→51**,5개 잔여 | +4M9K;5KiB ROM이3블록을 회수한 것은 아님 |
| 관련 setup/hold 구현 조건 | −0.101/+0.151→**+0.183/+0.168ns** | 이전 물리 기준+0.133/+0.132ns |
| nominal setup/hold | −0.101/+0.151→**+0.224/+0.168ns** | 같은 이전 SDC·corner 사용 |
| ARM Flash | +16B, **124B 잔여** | firmware212868B,+108B |
| ARM text/data/BSS | 202825/10040/18572 | 새 global RAM0B; SEAL static304B/RUN31848B 유지 |
| SNES | program8→5KiB,body4311B,문맥+8B | 기존3936B 배치 초과; 플랫폼 ROM 한도가 아님 |

선택 board02는 **whole Quartus Lite compile1회**와 동일한 두 timing view로 판정했다. 새 false-path/waiver/seed 반복은 없다. 이제 worst setup은 loader phase→loaded_bytes이며, 이전 check_failed→payload 늦은 허용 경계는 분리됐다. 전체 reset/CDC/IO 및 full ARM stack/IRQ 승인은 여전히 미완료다.

고정71개 ordinary/SEAL E1은364761→**222596B(38.97%)**,프레임당1797..2135B/평균2002.32B 절감이다.488보다14578B 더 작다. ARM serializer는487의13767406→8002870명령(41.87% 감소)이지만 **488의6392237명령보다 늘었다.** DMA 친화적 생산의 추가 계산/Flash 비용을 포함한 수치이며 명령 수를 물리 cycle로 간주하지 않는다. BEGIN/tile/plan/source/poll을 제외한 E1 비율이다.

## 검증·전달 경계

실제 M471개 canonical 상태·598개 계획 일치, sender0..7 경계8개, window CRC/credit 표본과 소유권12개를 통과했다. 이름만 바꾼 최종 ARM02는 시험 ARM01과781개 linked 함수의 주소·크기·명령 byte가 모두 같다. 변경은 같은 길이의 version/경로/로그 문자열이며 최종 ARM도 소유권 guard를 실행했다.

실제65816 raw71개 전체239행 RGB·raw VRAM이 baseline과 같다. 별도20개씩 두 synthetic suite는1↔2/0/3..7 양 bank와 오염된 초기 VRAM/cache를 검사했다. 실제 게임 의미를 가진 새 NES 입력이라고 주장하지 않는다. 기존 버전/count/길이/mode5거부, 복원/low DMA/최종 표시 STOP3종, 행 변경 후 partial clear/low DMA/최종 표시 STOP3종도 통과했다. 이전 표시 identity/픽셀과 무효 cache를 확인했다.

같은 source closure의 C/RTL/65816 START·34ACK·STOP/base,5KiB ROM bus, 선택 BI3/RBF의 실제227 FatFS/프로그래머 코드도 통과했다. GPIO/DONE은 모델이다. 한 Starter FLOAT 좌석으로 순차 실행했고 새 유료 라이선스는 필요하지 않았다. 현재 공개 정책에 따라 ROM·raw 로그·개인 tool/license·실행 binary는 Git에 넣지 않는다.

전달은 **MMC489-RAWDMA.zip**,marker `NES MMC3 489.nh1`,ROM `mmc489.nes`,로그3종 `*-mmc489.txt`다. 기존485/482/476/164/467 원복 파일은 byte/hash 동일하게 포함했다. 검증된 GBC/save는 보존하며 새 실기 메뉴 복귀/FPS는 아직 미확인이다.

## 다음 순서와 재현

다음은 사용자가489를 설치해 같은 대기/플레이 장면의 로그를 돌려주는 단계다. 실제 수신/계획·tile 공급/SEAL·ACK·capture/종료 비용을 이전485와 분리해 보고, 그 결과로 다음 병목을 정한다. 모델 이득만으로 추가 SPI 속도·source IRQ·새 매퍼를 동시에 바꾸지 않는다.60fps·전체 MMC4/5·지속 capture/p95는 남은 목표다.

공개 레시피는 `nes_output489.py`·`prepare_nes_output489_board.py`·관련test/audit/analyze/assemble/package tool이다. 로컬 선택은 `probes/nes-output489`의 candidate03/ARM02/audit01/client04(시험client03과동일)/assembly01/trial02다. board02/loader01/live01/bootbus01/programmer02/snes04..07/cold01/transition suite는 ASCII 실행 경로에 원시 근거를 보존했다. 원본487 ARM/482 board·고정 입력/reference·정당한 동일 ROM·도구가 필요한 기존 재현 부채는 [재현 범위](../cores/nes/REPRODUCING.ko.md)에 따른다. 없는 로컬 원본을 다른 fixture로 대체하지 않는다.
