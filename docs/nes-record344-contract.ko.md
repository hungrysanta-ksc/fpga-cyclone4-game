# NES344 — 연속 BG 묶음 선행 공급과 연속 source record

**구현과 검증을 완료했지만 결합 후보는 채택하지 않는다.** source record 경로는 whole11comb를 줄였으나, BG 선행 공급은 대기 서비스 수정 후에도 세 일정 모두 느려졌다. 선택은338 RTL·336 ARM, 부족4.022994145ms/1866comb를 유지한다. 근거는 `analysis/record344-verification.json`, 재현 도구는 `tools/analyze_nes_record344.py`다.

## 변경 경계

ARM은 full COMMIT 이후 warm(serial>2)에서 한 번, 현재 batch의 clear 뒤 첫 완성된 연속 BG run을 선행 발행한다. 최소2개 BG slot을 요구하고 각 slot이 resident used인지 확인한다. 낮은 미사용 slot 때문에 기다리지 않는다. 새 packet의 token/sequence/CRC는 기존 refill 경로에서 발행 순서대로 생성한다. 나머지 batch는 memmove로 보존하고 기존15plan/240B 용량을 reserve_bytes/plans에 남긴다. cold 두 bank 초기화는 기존 순서를 유지한다. STOP은 prefix와 예약을 지운다. 이 구현은 미래에 더 긴 run이 생길 때까지 기다리지 않는다. 실제 추가 chunk·credit·wire는 검증 대상으로 남는다.

Source는 기존 MASK·SHIFT 바이트 형식을 유지한다. 512B source phase RAM 중256부터 record를 연속 저장한다. MASK의 값은257+mask_bytes+diff_count, mask는257+row_i/8에 기록한다. 지연 mask 쓰기 뒤 BUILD344에서 header를 기록한다. SHIFT는 BUILD344의4cycle에 header·방향·edge2B를 저장한다. 출력 주소는256+rec_i 하나가 되고 기존 MASK threshold/subtraction과 SHIFT byte mux를 삭제한다. H/GEO/END 저장 위치는 유지하며 CRC trailer는 직렬 출력 뒤 checksum에서 선택한다. mask_pending 단일 포트 중재·base history·SHIFT 비교·CRC·lease·abort는 보존한다. 새 RAM 블록이나128B 별도 배열을 추가하지 않는다.

실제 코드: `tools/nes_record344.py`; 일정 probe: `tools/probe_nes_record344.py`; 전체 합성: `tools/map_nes_record344.py`.

## host 공통 실행기 검토

338 host의 ordinary PUT은 staging put_ready(또는 H2 context_ready)에서 진행하고 EXPAND325는 출력 길이만큼 seed를 반복한다. Metadata MCAP313은 encoded cursor를 진행한 뒤 MISSUE313에서 queue expected RAM을 선택·기록하고 MWAIT313 이후 manifest cursor를 진행한다. canonical_write313은 state와 bounds로 결정되므로 range_ready가 단순 write ACK라고 가정해서는 안 된다. RLE zero 생성과 encoded packet 끝 검사는 MNEXT313에서 수행한다.

공통화할 경계는 checked byte 공급, 목적지별 ISSUE/WAIT, 수락 뒤 cursor/remaining 갱신이다. 목적지 선택·RAM 포트와 staging backpressure를 분리하여 단일 accepted event를 만들되 expected RAM write 시점·stop gate·마지막 byte 완료를 보존해야 한다. Queue parser cursor와 출력 단위 cursor를 하나로 합치면 반복 압축에서 의미가 달라진다. 독립 validator의 read-owned CRC/coverage/private job 및 최종 scan은 유지한다. source는 NES clk, host/validator는 host_clk이므로 전역 하나의 실행기나 CDC 삭제를 가정하지 않는다.

이번에는 host RTL을 변경하지 않는다. 342의 reader/storage 공유만으로는 큰 절감이 없었던 근거를 유지한다. host1015comb 감소 목표를 실측 이득으로 세지 않는다.

## 실행 범위와 한계

ARM336 그대로인 RTL 단독 제한 ROM 연속905→906→907을 먼저 검증하고,338 RTL 위의 ARM 단독 및 결합 후보를 비교한다. 결합 후보는 동일 시작/ROM 위상, 제한 ROM 연속 일정, 일반 ROM 연속 일정을 분리한다. 실제M4 명령·IRQ·SPI·2slot·tile ROM/staging·readCRC·receipt·최종ACK 경로를 실행한다. SNES CPU bus trace는 기존 실행의 replay이고 CPI·exception 비용은 모델 할당이다. 새 full firmware RUN·full65816 CPU·물리 지속60fps 증명이 아니다. 새71프레임 전체 경로를 주장하지 않는다.

독립 oracle를 바꾸거나 expected를 producer 결과로 대체하지 않는다. 해당 기록 workload에서 plan 및 non-E9 output 순서가 유지되는지 엄격 비교하고, 실제 read event로 계산한 unit와 validator job/publish를 별도 대조한다. STOP 및 잘못된 ACK·최종검사·VBlank 검사는 유지한다. source record 저장 중 STOP과 deferred mask 쓰기 중 STOP을 추가한다.

## source 단독·회로 분리 검증

- RTL 단독3프레임 PASS. 실제 record 바이트·E1/DMA 동일, 전체 시간 기준과 동일. cold source prepare11840→11916cycle,906은11838→11854cycle,907은11838→11848cycle지만 기존 대기와 겹쳐 source 전체 cycle은 동일했다.
- 전체Lite MAP:22129LE/17263comb/9020FF/307808bits. 기준 대비−15LE/−11comb/+2FF/0RAM; 회로 부족1855. encoder 자체1348→1324지만 whole 절감은24가 아니라11이다. 다른 계층의 재최적화가 함께 반영된다. FPGA encoder FSM 추출 유지, 새FIT/STA 없음.
- 실제M4 bounded run guards10개 PASS: 낮은 미사용slot, 예약, 한번발행,STOP, gap, 후속run보존, 미소유slot,COMMIT, fault,cold보존. prefill은 단위 검사에서 stub이고 실제SPI는 결합일정으로 확인한다.




## 선행 발행 첫 후보의 회귀와 수정 경계

ARM 단독 제한 ROM907은20.689660812→36.678150766ms(+15.988489954)였다. 첫 요청은시작후8.38ms대→6.974484ms로 빨라졌으나 실제 첫ROM 승인은 동일했다. 82–84가 첫 E9(32B),85–86이 다음 E9(22B)로 나뉘며 E9 합계92→100B였다. 실제 DMA chunk는16개로 같았다. 따라서 이 회귀는 추가 DMA chunk 때문이 아니다.

추적상 첫 `tiles290`의 `bulk289` 대기는265.138467→275.264961ms였다. 기존 `service296`/`pending302`는 BG 완료 뒤 OBJ만 준비하므로 이 동안 남은 BG 계산이 중단됐다. 이후85–86 E9 공급은276.644306ms에야 시작했고 slot86 실제 plan 수락은291.159347ms로 다음 ROM 창으로 밀렸다. clear→첫 BG의 bulk 전환이 후속 planner를 막는 대기 경계가 새로 노출됐다.

수정안 `probe_nes_service344.py`는 prefix가 이미 발행된 경우에만 이 대기 중 기존 bounded `next_step286`을 허용한다. 초기 prefix가 없을 때는 기존 동작이다. work302의 DMA/credit/IRQ·공급 우선 검사는 유지하고 SPI 재귀를 추가하지 않는다. prefix는 이미1이므로 nested step의 advance344는 재발행하지 않는다. 실제M4 단위 검사에서29개 BG step이 foreground와 같은 batch·plan·BG 완료 표식을 만들었고 STOP 뒤 continuation/pending이 취소됐다. cold 입력으로 강제 lifetime을 시험한 최대 step49,869instructions는 작지 않으며 실제 warm 일정과 IRQ 지연은 전체 실행에서 별도로 확인해야 한다.


수정안의 제한 ROM 연속 결과:905 99.245263588ms(+0.499994µs),906 116.712008530ms(−0.272724µs),907 20.790295968ms(+0.100635156ms). 큰 대기 회귀는 제거했지만 기준보다 빠르지 않다.907 E1은15개/584B로 같고 E9는4→5개/92→100B, E2는22→24개/308→336B다. 추가36B wire는0.109714ms이며 실제 최종 시간 증가는겹침을 반영한0.100635ms다. M4 .text30638(+528),.data0,.bss47412(+8),관측stack1288동일. 기존 probe 전체 크기이며 full firmware RAM 예산의 대체물은 아니다.


## 최종 전체 비용 비교

| warm907 일정 |338 RTL·336 ARM|344 source+수정 ARM|차이|
|---|---:|---:|---:|
|동일 시작·ROM 위상|25.051199382ms|25.152879980ms|+0.101680598ms|
|제한 ROM 연속905→906→907|20.689660812ms|20.790295968ms|+0.100635156ms|
|일반 ROM 연속905→906→907|13.410066350ms|13.572655308ms|+0.162588958ms|

수정안의 제한 ROM 60Hz 부족은4.123629301ms다. 고정 위상도 회귀하므로 연속 일정의 차이를 앞 프레임 위상 효과로 설명할 수 없다. 일반 ROM도 이득이 없었다. 일반 cold905/906은각각+0.020863386/+0.020727024ms였다. 초기 후보 ARM-only와source결합의 제한 일정은완전히 같은 결과였으며 source-only는기준과동일했다. 시간 이득과 회로 여유를 함께 확보하지 못했다.

Host는 변경하지 않았으며 공통 실행기의 절감은0으로 계상한다. whole15253comb 상한까지는후보에서도2010개 감소가 더 필요하다. MAP의1855comb 초과는FIT/LAB/STA 해결을 뜻하지 않는다. source encoder1324에서목표701까지도623개가 남는다. 출력 주소 mux만 없애는 구조로647개 절감 예산을 채울 수 있다는 근거는 얻지 못했다.

## 검증 범위와 재현 증거

SELECT는 `rtl01/arm01/joint01/service01/servicefixed01/servicenormal01/map01/guards01/source01/armguards02/serviceguards02/continuation02`다. 기록 프레임은 905–907 세 개이며 6일정의 18관측이다. 새 71프레임 전체 실행이 아니다.

- 기록된 3프레임에는 SHIFT record가 없었다. 따라서 동일 encoder RTL에 별도 인공 입력 4개(cold MASK→left SHIFT→right SHIFT→unchanged)를 넣었다. 전체 N5 record와 CRC가 독립 Python encode280과 일치했고 SHIFT 수는 0/1/1/0이었다. 출력 stall에서도 byte가 안정적이었고, SHIFT BUILD 도중 STOP에서 RAM 동결·ACK 차단을 확인했다. 이는 source 단위 검사이며 실제 scroll이나 전체 일정 측정은 아니다. 단위 TB의 27 warnings는 미사용 output 26개와 connection count 1개이며 입력 누락은 없다.
- 10개 통합 fault 검사를 통과했다: source/E9/ROM STOP, 조기 표시 ACK, expected/receipt 손상, wrong token, raw CRC STOP, 최종 검사 조기 요청, BUILD344 STOP, deferred MASK STOP. fault 이후 RAM 동결과 완료 공개 차단도 확인했다. 별도 aperture 및 raw0/final 8 cases도 통과했다.
- M4 prefix 10종을 첫 후보와 수정안 각각의 실제 ELF에 검사했다. BG continuation 3종은 29 step에서 foreground와 같은 batch·plan·BG 완료 표식, 미발행 시 계산 억제, STOP 취소를 검증했다. 초기 별도 build ELF와 통합 ELF는 PT_LOAD 이미지가 같지만 파일 hash가 달라, 최종 단위 검사는 통합 ELF에 다시 묶었다.
- 입력·변환된 C/RTL·ELF·TB·로그·합성 입력을 해시로 묶었다. 전체 Lite MAP 입력 중 338 대비 변경은 nes_core257.sv 하나이며 기능 검증 RTL과 같다. 기존 expected/실제 read CRC·coverage·token 공개·2credit·VBlank 검사를 약화하지 않았다. 기존 SNES bus trace replay이며 새 full65816 실행은 아니다.

첫 후보의 fixed01은 ARM-only와 joint01에서 같은 큰 회귀를 확인한 뒤 의도적으로 중단했다. `v1-cancel.json`과 원래 로그를 보존하고 PASS에 포함하지 않는다. 수정안으로 고정·연속·일반 일정을 모두 실행했다. 초기 sandbox 호스트 확인/ARM build DLL 제한은 허용된 호스트 wrapper/build로 해결했으며 새 라이선스 문제가 아니다. 라이선스·서버 로그는 Git에 넣지 않는다.

## 다음 교체 경계

추가 E9나 prefix 길이 조절을 다음 최적화로 선택하지 않는다. MASK·SHIFT와 nonmap 압축을 하나의 record 생성 경로에서 유지하며 입력 완료를 실제로 앞당길 수 있는지, host의 두 목적지 진행 경로를 실제로 삭제할 수 있는지 합쳐 예산을 다시 검증한다. 입력 wire가 같은 record layout 변경만으로는 이전 ROM 창을 잡지 못한다. 340의 독립 encoder 추가나 343의 MASK 제거로 돌아가지 않는다.

실제 삭제 목록·RAM 포트 수명·응답 wire·ARM 계산·cold 비용을 먼저 확정하고, 정당화된 후보만 전체 일정과 whole Lite로 평가한다. 미구현 host 절감이나 새 제어를 무료로 세지 않으며 독립 검사·저장 credit/소비 분리·STOP·최종 ACK·VBlank를 유지한다. production227/GBC164/saveSRAM 변경 및 자동 merge는 없다.
