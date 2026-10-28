# NES388–389: 증분 map 준비와 source 비용의 합산

386의 표시 직전 범위 재해석·64열 순회·job 압축을 실제로 제거했다.907/908의 준비는1.244/6.059ms에서 **0.788/0.786ms**로 줄었다. 하지만 source 처리가 늦어지는 비용까지 연결하면 **첫 capture 누락은 여전히911번**이다. 지속60fps 후보로 채택하지 않는다.375 RTL·377 ARM과 기존 회로 부족2,255comb는 그대로다.

## 삭제·대체한 실행 제어

기존16B PPU job에서 사용하지 않는 token 복사4B를 제거하고12B 형식으로 바꿨다.256job의3KiB와 회수한1KiB의4B map 좌표256개가 기존4KiB record 공간을 나눠 쓴다. source receipt용 token은 저장 ACK까지 immutable한 aperture에서 마지막에 직접 읽는다. typed header는 실제 필요한7B만 복사한다. 최종 ACK의 token 의미는 바꾸지 않는다.

작은 sparse 정책(7범위 이하·128B 이하)은 열 정보가 필요 없다. 한도를 넘는 순간 compact 좌표를 재사용해 bounds를 초기화하고 기존 범위를 한 번 반영한다. 이후 실제 변경 word의 min/max와 변경 열 목록만 갱신한다. 준비가 끝난 뒤 모든 map/64열을 재순회하지 않는다. 초기화와 첫 범위 replay도 source service에 포함한다.

각 job 생성 시 현재 길이로 전체 DMA 예산을 누적하여 표시 직전 job 길이 재순회도 제거했다. 누적은 saturating 방식이다.4개의2048B tile을 WRAM에 저장할 수 있더라도 VBlank 예산을 넘으면 표시 전에 거절한다. 메모리 수용과 표시 수용은 다른 조건이다.

## 실제 CPU·STOP 검증

native07은907..916의10warm+STOP을 통과했다. 모든 source 저장 뒤 실제 PPU port write를 실행하고 전체 map4096B·변경 tile·OAM544B·현재 H2 scroll을 독립 expected와 비교했다. 최종 ACK와 PPU data write는 같은 VBlank여야 한다.

guards05의16case는 기존 STOP·용량·CGRAM·palette·dense·두 screen의 열 사이 빈 셀 검사에 다음을 추가했다.

- bounds 전환/replay 중 STOP과 표시 설정 중 STOP.
- compact map 좌표257번째와 PPU job257번째의 별도 용량 검사.
- 8192B tile 저장 뒤 표시 예산 overflow 거절.
- 상위16bit가0이 아닌32bit token의 실제 두16bit read/write 및 최종 ACK.

표시 suffix의 기존 STOP 경로가 공통 cache 무효화를 우회하는 문제도 새 검사에서 확인했다. guards04의 실패를 보존하고, suffix의 abort를 공통 cache invalidator로 연결했다. 두 bank bit를 지우고 forced blank·HDMA off·최종 ACK 차단으로 종료한다. 수정 전 native06과 수정 후 native07의 정상10프레임 bus event 및 시각 hash는 모두 같다. 회로/시간 절감으로 계산한 수정은 아니다.

prior-bank WRAM/VRAM/OAM·valid bits·HDMA terminator는 명시적 warm fixture다. 실제 cold 초기화·STOP 후 정상 복구·전체 pixels·전체 resident CPU를 증명하지 않는다. palette/dense/columnholes/용량/widetoken은 synthetic 출력 ABI 시험이며 추가 ARM/NES 프레임이 아니다.

## 전체 비용

|항목|386|388|
|---|---:|---:|
|실제65816 ROM fragment|3290B|3274B|
|payload/job/cache SNES WRAM|24705B|24769B|
|추가 DP 예약 상한|30B|37B|
|새 FPGA 절감|0|0|

추가64B는 변경 열 목록이다. 기존16B×256 job 공간을12B×256 job+4B×256 map 좌표로 재사용하여 map 좌표용1KiB를 새로 더하지 않는다. 기존 header/token 복사8B는 fragment에서 사용하지 않지만 fullresident RAM 회수로 계산하지 않는다. 추가 DP37B는 보수적 예약이며 전체 stack·firmware RAM 배치 승인은 아니다.

보드 sink ROM slot은4KiB이고 새 fragment는 그 안에 든다. 전체 dispatcher·ordinary·NMI·음성/입력·복구 프로그램 크기는 여전히 미확정이며4KiB를 하드 목표로 삼지 않는다. 새 ROM을 보드에 설치하지 않았다. 확장 시 ROM decode·M9K도 전체 비용에 넣어야 한다.

## source로 옮긴 비용을 포함한 계측

기존387은 source 종류별 최대 control 비용을 모든 record에 부과했다.388에서는 초기화/replay의 단발 비용과 길이에 따른 차이가 커져, 실제 각 record의 CPU control을 그대로 부과하도록389 service allocation을 바꿨다. 이 모델 변경을 구현 이득에 섞지 않기 위해 **386도 같은 per-record 모델로 다시 실행했다.** 추가 frame 초기화904master clocks,약42.091µs는 한 번 더 부과한다.

source control은 actual native의 첫 status→다음 status 시간에서 payload의8clocks/byte를 뺀 값이다. CPU의 payload 전후 control 합계를 실제 source read 앞에 보수적으로 배치한다. 저장 receipt의 전체 비용을 빠뜨리지는 않지만 instruction 단위 CPU/SPI lockstep은 아니다.325 ordinary WRAM·381 view head·실제 M4 IRQ/공유 SPI/2슬롯/ROM 경쟁을 유지한 혼합 service allocation이며 실기 WCET는 아니다.

|frame|386 source control|388 source control|386 표시 전 준비|388 표시 전 준비|
|---|---:|---:|---:|---:|
|907|3.120798ms|2.603505ms|1.243924ms|0.788185ms|
|908|5.502486ms|5.933268ms|6.059449ms|0.786136ms|
|914|8.850780ms|10.094704ms|10.593838ms|3.614158ms|
|915|11.814016ms|13.856554ms|12.509637ms|3.825172ms|

CPU가 일하는 시간은 줄어도 완료 기한에 유리하다고 바로 판정하지 않는다. 특히908의 source control은 약0.431ms 늘어났다.914/915의 수치는 native 단일 프레임 계측이며 새 연속 실행이 해당 출력까지 완료했다는 뜻이 아니다.

## 같은 시작·ROM 조건의 연속 비교

reference01과 joint01은 같은 generated testbench hash와375 보드 공유RTL31개·377 M4 load image를 사용한다. testbench 차이는 원래387에 대해 per-record control 선택3곳과 추가 초기화 시간 부과1곳뿐이며, 두 실행에 동일하게 적용했다. ROM_WINDOW=1·46,561ps master allocation·위상0·고정907 capture cycle5,371,247 및 후속 capture 기한을 유지한다.

|항목|386 per-record 기준|388 증분 후보|
|---|---:|---:|
|907 ready|278.230315ms|277.776498ms|
|907 source→완료|17.227501ms|17.226057ms|
|908 ready|297.479321ms|297.967444ms|
|908 source→완료|33.542754ms|33.542615ms|
|표시 VBlank|16/18|16/18|
|첫 capture 누락|911|911|

907/908의 완료 차이는1.444/0.139µs 수준으로, polling 위상 차이이며 전체 일정 개선으로 채택하지 않는다. 두 실행 모두905..908 배출4개,908/909/910 capture 승인 뒤911 owned1/release0/fault0 실패다. 원본 source·plan·실제 read→CRC/coverage→receipt 공개의 독립 검사 순서를 대조했다.

908 ready가 기준보다0.488123ms 늦어져 view head 뒤 phase가326,533으로 이동했다. native cutoff246행까지9011clocks, **0.419561ms**만 남는다. 준비0.786136ms는 이보다 **0.366575ms 길다.** 따라서 이전 시각에서 잡았던0.8ms 목표 달성만으로 충분하지 않다.

기존 replay의 tail 예산만 보더라도 준비 후 남은13,951clocks가 예산14,048보다97clocks,약4.52µs 모자랐다. 이 차이를 없애려고 cutoff·512clock reserve·ROM 위상·capture 기한을 완화하지 않는다. 실제 native의 더 보수적인 행 제한도 그대로 유지한다.

연속 실행은 정상 profile이 동일한 native06을 사용했다. 이후 STOP 수정 native07의 모든 정상 event/time hash가 같음을 확인하여 새로운 시간 이득 없이 안전 수정만 연결했다. future389 기본 경로는 native07이다. fullCPU/실기 전체 시험으로 확대 해석하지 않는다.

## 다음 선택

SNES에서 map 계획을 계산하는 현재 후보는 시간 개선안으로 선택하지 않는다. 다음에는 **ARM의 기존 map 범위 정보로 compact 실행 계획을 한 번 생산하고 SNES에는 검사·실행을 맡기는 경계**를 비교한다. 기존 ordinary WRAM 명령을 재사용하되 새65816 소비기에도 ordinary5·메타데이터 경로를 실제로 연결해야 한다. 현재325 trace allocation으로 새 명령의 실행 비용을 무료로 대체하지 않는다.

ARM 생성 시간/임시 RAM·추가 wire/응답·2credit/IRQ·SNES 수신/목적지·coverage 검사·gather·cache 세대·STOP·최종 ACK를 합산한다. ARM의 더 이른 공급으로 ready가 달라지면 cutoff 예산도 다시 산정한다. 현재 시각에서 post-view0.35ms 이하를 예비 목표로 두지만 아직 구현값이나 보장이 아니다. source 임계 구간에서 제어를 실제로 줄이는 것이 우선이다.

동시에 source/host/queue/plan/receipt 본체의 기존 순삭제2410comb 예산을 유지한다. 현재 Lite375는22390LE/17663comb/8985FF/300640bits,부족2255comb이고 새MAP/FIT/STA나 새 절감은 없다. control3582→1172이하는 새 context/mapper/bridge 전의 상한이며 FIT 보장이 아니다. 합법적인 시간과 회로 용량을 함께 확보하지 못하면 ROM 중재·렌더 표현·역할·하드웨어 범위를 재검토한다.

MMC4/5는376 gate 그대로 미구현·여유 미승인이다. source control+준비 시간의 합계 개선을 mapper 여유로 전용하지 않는다.71/heavy7·여러 위상·live core/mapper·전체 resident CPU/IO/audio·cold/STOP 정상회복·WCET·whole FIT/STA·실기60fps는 미완료다. production227/GBC164/saveSRAM을 보존하고 자동merge/구매하지 않는다.

근거는 `analysis/increment389-verification.json`, raw는 `../probes/nes-increment388/`다. 초기ROM title 길이 실패,초기 전체열 추적/예산 재순회 후보와 guards04의 표시 STOP 실패도 보존했다.
