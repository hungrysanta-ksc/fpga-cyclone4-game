# NES289 native 출력 생산기 연결

NES289: 기록된 ordinary/manifest 명령을 실제 M4 native 생산기로 대체했다. 71프레임 1039명령/73260B 일치·fixture read0, producer6+오류8 검사와 실제 IRQ/ROM 정상·제한3씩 PASS. 일반907 15.314998ms(+0.793718), 제한907 17.999648ms(-0.727400); ARM text+4236B/BSS+768B/관측stack1296B. FPGA RTL287 동일/새MAP 없음/절감0/2263comb 부족 유지. native 생산 첫 연결이며 시간·회로 공동 최적화 완료가 아니다.

## 실제 변경

NES287의 실제 row planner를 유지했다. `frame259`는 기록된 명령 blob을 파싱하지 않고 native video/resident/dirty 상태에서 BEGIN, tile DMA descriptor, 일반 명령, map/manifest, SEAL을 생산해 기존 checked dispatcher로 보낸다. E9 encoded plan을 순회해 실제 tile producer와 같은 연속 slot·2048B 범위를 만든다. offline71은 bulk token만 0으로 정규화해서 원본 명령과 비교하며 live3은 실제 token을 포함한 E1/E9 전송 바이트가287과 완전히 같다. 테스트는 명령 fixture 메모리를0xA5로 채운다.

map_word185의 실제 변경에서 두 bank의512B dirty mask를 갱신한다. 옛 native fixture의4KiB map 복제는 가져오지 않았다. 이는287 대비4KiB 절감이 아니다. 새512B mask·206B seal·sink 상태는 추가 비용이다. manifest는 RLE 길이 계산 후 직접 packet을 구성해512B 임시 배열을 없앴다. 첫 live test01의stack1768B는 최종test02에서1296B가 됐다.

생산 완료와 commit을 분리했다. 실패한 생산/STOP/미생산 상태는 commit285를 거부한다. 실제 worker는 기존finish267의 checked EA/display retirement 성공 뒤에만commit285를 호출해 resident/dirty와 대상bank mask를 commit한다. 이 순서는 호출자 계약이다. offline dispatch interception의commit은 ACK를 가정한 시험이며 실제 ACK 검증으로 세지 않는다. 기존FPGA bounds/CRC/receipt/orderedACK/STOP/최종12B ACK 제어는 그대로다.

## 측정

ARM 일정은 기존과 같은 84MHz·CPI1 가정이다. 실제 M4 명령을 실행했지만 하드웨어 실행 시간을 측정한 것은 아니다. 905·906은 cold bank 준비를 포함하며, 907 한 프레임의 warm 결과를 전체 장면에 일반화하지 않는다.

| 항목 | NES287 | NES289 | 차이 |
|---|---:|---:|---:|
| 일반907 진단 전체 일정 | 14.521280ms | 15.314998ms | +0.793718ms |
| 제한ROM907 | 18.727048ms | 17.999648ms | -0.727400ms |
| ARM text | 22214B | 26450B | +4236B |
| ARM BSS | 46292B | 47060B | +768B |
| 관측stack | 472B | 1296B | +824B |
| whole Lite comb | 17671 | 17671 | 0 |

제한ROM907의60Hz 예산 초과는1.332981ms다. 일반907 한 프레임이 예산 안이어도 전체71의60fps를 입증하지 않는다. 이번 새전체일정은정상3+제한3뿐이고287의warm 최대954=26.375411ms를289 결과로 전용하지 않는다. 일반/제한 상세값은 `analysis/joint289-normal.csv`, `joint289-restricted.csv`다. 생산 명령71은86806..256654 M4 instructions이며 dispatch를intercept한 비용이므로 full transport 시간과 중복합산하지 않는다.

제한907의slot wait는110230→77732cycles, E2는23→21, IRQ wait는9→8로줄었다. 생산비용이늘면서ROM위상도바뀌었으므로-0.727400ms를순수생산기개선이나최악시간보장으로해석하지않는다. 일반907은+0.793718ms로반대결과다. 독립build03과live ELF의파일해시는달랐지만모든PT_LOAD 코드·데이터·주소·BSS범위는정확히같다. 이차이로중단된analysis01은보존하고로드이미지일치를확인한analysis02를선택했다.

## 회로와 미완료 경계

RTL 해시가287과 같아 기존Lite whole MAP22569LE/17671comb/9025FF/307808bits를 참조했다. 새합성은 하지 않았다. 기존FPGA host2361+validator1090, queue129+plan568+SPI658+glue47을 아직 제거하지 않았다. 범위4853comb와예산2590, 부족2263은 그대로다. ARM에서 실제명령을 생산하도록 바꾼 사실을 FPGA제어 통합으로 부르지 않는다.

기존E9 진단8192B와 raw/BG-key union은 유지한다. 모든planner 완료 후출력 생산하므로 earlyDMA가 아니다. source 비용은280 replay, SNES 일반실행은279 bus trace 재사용이며 tile/map/display는bus model이다. 전체firmware RUN/NVIC, 실물CPI, 새live65816/VBlank, 전체program ROM, FIT/STA/physical60fps는 미검증이다. production227/GBC164/saveSRAM은 변경하지 않았다.

## 검증과 보존

SELECT native01(71+6), guards01(8), test02(3), window01(3), analysis02. ELF/RTL/TB/변환입력/생성소스 해시를분석에고정했다. build01의잘못된빌드진입실패, build02/test01의이전stack/commit구현은개별보존했다. test01을최종코드검증으로합산하지 않는다. offline71 최종ACK는가정, live3는실제checkedfinish후commit이다. 회로동일하므로287 RTL오류검사를새289실행으로세지 않는다.

## 다음 작업

NES289 native 생산기를 기능 기준으로 보존하되 성능 비교 기준287도 유지한다. 다음은 완료된 E9 batch와 BG DMA cursor의 단계별 연결 및 원본 descriptor dispatch/host 전송 제어를 실제 제거하는 공동 교체다. raw/BG-key union, COMMITTED, H2, 양 bank dirty 수명을 지키고 OBJ/OAM/map/manifest/SEAL의 독립 coverage·CRC·receipt·STOP·최종ACK를 유지한다. queue/plan/SPI/glue1402comb를 유지하면 host+validator3451comb는1188 이하(128여유1060)가 필요하다. ARM 생산 추가비용·stack1296·공유SPI·IRQ·제한ROM을 모두 포함해4853→2590 경계를 검증한다. 새로운 전체71 일정과 matched whole Lite 전까지 조기DMA 이득/회로 절감/60fps를 주장하지 않는다.
