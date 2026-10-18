# NES240: 송신용 중복 복사를 제거한 인코더

## 작업 의미

60fps 입력 증분 경로의 준비 시간과 FPGA 제어 회로를 함께 줄인다.239는 실제 FIT에서522LE·43LAB이 부족했다.240은 작은 산술식 조정보다 데이터 이동 구조를 바꾼다. 완성된 payload를 송신 RAM으로 다시 복사하지 않고 기존 저장 위치에서 읽는다. 전체 codec과 source ACK 규약은 유지한다.

## 변경과 수명 규약

- 일반 literal은3B header와 L의 payload,행 이동은5B header와 N의 양 끝2B,반복 raster는5B header와 M의8B를 순서대로 읽는다. 저비용 raster record는 C를 직접 읽는다. header/geometry END/raw END는 P에서 읽는다.
- 기존 send_return의7가지 후속 작업이 송신 자료 위치도 구별하므로 별도 mode register는 추가하지 않는다. read 상태에서 주소를 설정한 뒤 기존 synchronous RAM read와 byte handshake를 따른다. CRC16은 실제 송신 byte 순서대로 계산하며 trailer의 마지막2B만 checksum으로 대체한다.
- 공개한 record의 REQUEST/SREAD/SBYTE 동안에는 scratch와 base 쓰기를 하지 않는다. byte backpressure가 길어져도 원본 영역과 송신 byte를 보존한다. geometry와 raw의 L 영역 재사용은 이전 record 송신 완료 후에만 일어난다.
- C에 작은 raster literal을 모으는 복사는 필요하므로 유지한다. 이때만 L에서 C로 순차 복사한다. 기존 범용 copy 주소2개/count/continuation 및 저장된 literal destination을 제거하고 build_i를 재사용한다. cheap_i는 해당 record를 다 보낸 뒤에 증가한다.
- scratch의 O0..65/N128..193/L256..495/C80..91/M96..103/P208..227은 겹치지 않는다. 실제 payload412B,주소 span496B로512×8 true-dual-port RAM에 들어간다. 논리 저장량 감소이지 M9K 회수 주장과 같지 않다. base4096+2048 두 bank는239와 같다.

serial32/epoch32/CRC16,geometry5741B,query235의 독립 offset 검사,raw width,부분 실패 후 base 무효화/common reset 규약은 유지한다. 게임 CPU/APU/mapper와 save SRAM은 바꾸지 않는다. PREPARED는 source base 승인이고 최종 SNES displayACK는 아니다.

## 검증 범위

239와 같은 seed237의24정상 자료와17경계 검사를 사용한다. 모든 송신 위치에서 긴 ready 지연을 추가하고 정지된 byte 불변성,공개 중 RAM write 금지,각 정상 완료 후 base5741B 일치를 검사한다. 큰 serial 시험은 직접 seed한 경계 시험이며 수십억 frame을 실제 재생한 것이 아니다.

같은 SMB3 첫 레벨 관측71프레임905..975를 actual collector201→query235→encoder240→SPI235 실제 핀→actual C234/231로 전달한다.234 record는 oracle이며 FPGA 입력이 아니다. wire/record 경계와 C geometry/raw/metadata/packet/plan355파일을 비교한다. 준비 cycle과 전송·대기는 따로239와 비교한다.

PPU 입력과 PREPARED ACK,C ROM/표시 callback은 fixture다. 전체 게임 CPU/실제 ARM/최종 SNES 표시/실기 FPS 검증이 아니다. 기존235 SPI 경계와232 actual65816 결과는 보존·재사용하며 새로 실행하지 않는다.

최종24정상+17경계 총41검사와7가지 송신 위치의 stall 불변성을 통과했다. 실제71프레임은2229records/350blocks/62967payload bytes와 record 경계가 일치했고,355개 C 결과 파일,4,066,624 reference checks,1459 C fault/restart 검사도 통과했다. 모든71프레임에서 준비 cycle이 감소했고 전체 cycle이 증가한 frame은 없다.

| 동일907..975 창 |239|240|
|---|---:|---:|
| 준비 최대 cycle |39779|37080|
| 준비 합계 cycle |2419742|2326612|
| 입력 시작→PREPARED 최대 cycle |137913|137200|
| 입력 시작→PREPARED 합계 cycle |6365593|6317145|
| record credit 대기 합계 cycle |2226246|2270929|
| ACK 상태 대기 합계 cycle |1605629|1605628|
| record 송신 합계 cycle |113976|113976|

source45.454ns/host11.904ns/SPI2.625MHz 모델에서 준비 최대는1.808115→1.685434ms(-6.785%),준비 합계는-3.849%다. 전체 입력 경로 최대는6.268698→6.236289ms,합계는-0.761%다. 빨리 준비해도 record credit 대기가 늘어나 일부 이득이 상쇄된다. ACK 상태 대기에는 마지막 block 전송도 들어 있으므로 이 값을 순수 ACK 왕복 지연으로 보지 않는다. 실제 ARM 계산·다른 SPI 명령·SNES DMA/표시는 제외돼 있으며 전체60fps 증명이나236의 공유 SPI 예산을 대체하는 수치가 아니다.

## 보드 승인 조건과 보존

기능 검증 후 같은224 전체 보드에서 MAP/FIT를 각각 한 번 실행한다. 옛 source 교체 범위와216개 retired SDC 행 정리는239와 같다. 새 false path,clock 완화,timeout 확대,seed 반복은 없다. 실패한 FIT 요구량을 배치·timing 성공으로 사용하지 않는다.

최종 source lease/displayACK/retire 연결,host/NES fault 영역과 최초 오류 보존,새 입력 전체 ARM RUN/IRQ,CDC/IO/STA,232의5개 VBlank 초과 burst는 남아 있다. mapper 여유까지 확보해야 하며 단순히 현 FPGA 한도에 맞추는 것만으로 완료하지 않는다. 생산227/GBC164/save SRAM과 기존 봉인 자료를 보존하며 미승인 실기판은 배포하지 않는다.

선택은 test01/guards01/board01/source01이다. MAP/FIT는 각각 한 번 실행했고 결과는 다음과 같다.

| 항목 |239|240|
|---|---:|---:|
| encoder 조합/FF |1395/443|1399/409|
| source 계층 조합/FF |2091/1008|2092/974|
| 전체 조합/FF |14977/8611|14966/8577|
| MAP 추정LE |19821|19809|
| 실패한 FIT의 LE 요구량 |15930|15898|
| 실패한 FIT의 LAB 요구량 |1006|1003|
| M9K 요구량 |54|54|
| 논리 메모리 bit |316000|311904|

FIT는 Error170012로 실패했으며 **490LE·40LAB이 아직 부족**하다. mapper·timing 여유는 별도다. scratch512×8도1M9K를 사용하므로 용량 절반이 실제 블록 회수로 이어지지는 않았다. base4+2,scratch1,SPI1의 구성이며 RAM 위치는Unassigned다. 배치·타이밍 성공으로 사용하지 않는다. 기존 loader state 관련332174/332049와 IO 경고도 원본 로그에 보존했다. 이번은 STA/전기적 승인 단계가 아니다.

범용 복사 포인터를 없애 FF34개가 줄었으나 직접 송신의 주소 선택이 필요해 encoder 조합 수는4개 늘었다. 전체 LE 요구량은32개만 줄었다. LUT-only7321/register-only932/LUT+register7645이며239는7319/953/7658이었다. **복사 제거만으로 큰 면적 절감이 된다는 가정은 기각한다.** 준비 시간 이득과 자원 개선이 모두 있지만 부족량 해결과는 구별한다.

## 다음 구조 변경의 조건

전체 제어 분기와 공유 데이터 경로를 함께 재설계하는 후보를 먼저 평가한다. 단순히 같은 카운터의 increment/reset 식을 다시 쓰거나 작은 가산기,주소식,FIT seed를 반복하지 않는다. MAP의 multiplexer restructuring 표에서 lit_len/lit_used15:1,row_i19:1,build_i25:1이 보이지만 해당 행의 Area if Restructured는 이미0이다. 이 표의 Baseline Area나 가상 Saving을 남아 있는 셀 수로 합산해서는 안 된다. 특정 CE/reset 때문에490LE가 낭비됐다고도 확정할 수 없다.

가능한 다음 후보는 M9K 내 compact control과 명시적인 register write/hold 구조다. 실제 남는1~2M9K 안의 word 폭·read latency·분기 비용을 설계하고,각 값의 최초 write→read 수명과 reset/abort/ACK 우선순위를 보존해야 한다. 기존 RAM을 단순히 넓히는 메모리 산술이나 좁힌 protocol 필드는 허용하지 않는다. 현재 직접 송신·codec·query 독립 위치 검사는 유지하며 준비 cycle과 전체 source 시간을 같이 비교한 뒤 한 번의 전체 보드 gate로 평가한다. 아직 이 후보의 효과를 입증하거나 mapper 여유로 승인한 것은 아니다.
