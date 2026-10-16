# NES200 표시 완료 후 계획 경로 재무장

PR117의 연속프레임 연결 후보다. 배포186이나 실기 패키지는 바꾸지 않았다.199의 타일생성/출력방식을 유지하며 END 뒤 계획 경로를 다시 사용할 수 있게 한다. 실제capture/producer와board mux/runtime까지의 통합은 아직 남아 있다.

## 변경 이유와 순서

193 chunk bridge는 END 처리 뒤 내부in_frame을 해제하고 token을 계속 증가시킬 수 있었다. 반면199 SPI는 END를 session 종료까지 유지했고 C도finish 이후 다시 시작할 수 없었다. 따라서 프레임마다transport/코어를reset하는 우회 대신, **최종SNES표시 ACK 뒤의 명시적retire**를 추가했다.

정상호출 순서는 sink begin →191 planner/200 emit →200 finish(END+모든chunk소비) →기존 sink seal(테이블/VRAM/CGRAM/OAM/HDMA 최종ACK) →200 retire →source lease 반환/다음capture 승인이다. 이번C에는 finish와retire가 구현되어 있지만 이 전체순서를 productionRUN에 호출하는 작업은 미완성이다.

finish는 표시완료가 아니다. `nes_plan200_retire`는 sink가IDLE이고 displayed=true이며 last_generation/current generation이 자신이완료한generation과 같아야 한다. 실제195 sink의 packet ACK status/token/signature 검사와 seal 성공 후상태를 사용한다. 실패·불확실응답·guard 실패·poll 한도는terminal이며 재전송하지 않는다.

## Protocol과 클록 경계

- E8 status version4. flags bit0=write credit, bit1=END latch, bit2=retire 진행중, bit7=fault. E9는199 short/full 혼합형식 그대로다.
- EA는7B: `EA,generationLE16,accepted_batchesBE16,CRC8,A5`. CRC8은앞5B다. END가있고남은chunk가없으며plan host가빈상태, 세대/묶음수/정확한7B/CRC/tail이모두맞아야한다.
- EA를받으면credit을차단하고 기존165의1bit mailbox로host→NES 재무장을요청한다. NES는 END를수락한closed상태이고 WAIT이며 남은plan mailbox가없어야closed를지운다. 그ACK가host까지돌아온뒤에만 END와accepted를0으로바꾸고credit을연다. NES clock이멈추면진행중으로남으며성공을꾸미지않는다.
- END 이후 도착한계획은SPI latch뿐아니라 NES decoder의closed에서도거부한다. 즉host가END통지를보기전에다음묶음을밀어넣는경우도오류다. 중복EA/옛generation/옛묶음수는terminal이다.
- chunk RAM bank, writer/reader, chunk token, source reader는프레임retire때reset하지않는다. token은계속증가하며FFFFFFFF 소진정책은193 그대로다. EA는SNES buffer consume가아니다. SPI가최종PPU상태를직접검사하는것도아니며그확인은C의sink ACK 경계가담당한다.
- common STOP/fault/reset은양쪽endpoint를취소한다. independent endpoint reset은지원하지않는다. STOP뒤새token seed/동기client재시작은caller의기존책임이며이번normal retire와구분한다.

## 검증

SELECT `probes/nes-frame200/test03`, `faults02`, `c01`, `evidence01`.

- 실제SPI2.625MHz→200planRAM→192qualifiedREAD16/70ns메모리fixture→193aperture로3합성장면을각3frame 연속처리했다. 총9frame/1968B가186기준과동일하다. BG,OBJ,변형행,raw장면의normal tile부분을포함한다. raw8bpp최종표시를새로검증한것은아니다.
- 각run에서generation65534→65535→0, token1000부터계속증가, 중간reset/STOP없음. 합성core요청에대한응답도계속검증했다. 이것은실제게임CPU실행증거가아니다. lease/ROM epoch는fixture에서제공했고실제producer snapshot재승인은아직연결하지않았다.
-50경계검사: 기존37 plus 정상retire/멈춘NES clock/STOP, END전EA, generation/accepted/CRC/tail/잘림/추가byte/남은chunk, END이후E9, 중복EA, host END통지전decoder closed거부.
- 실제C200+실제195sink의10검사:3연속frame의begin/emit/finish/seal/retire, 최종ACK누락·오류·wrong displayed generation, 재무장지연한도/잘못된응답/전송실패/guard실패. SPI와SNES ACK exchange는mock이다. 실제C와RTL/실제65816을동시에실행한시험이아니다.195의actualC+65816증거는그대로재사용한다.
- test01은하네스sg/frame200선언충돌, test02는변수치환이task이름까지바꾼오류로실패했다. test03에서수정했다. faults01은END펄스를실제193의1hostclock보다길게준fixture가중복END로거부된것이며, 한clock으로맞춘faults02를선택했다. 생산RTL/C는첫구현그대로통과했다. 실패로그는보존했다.
- 이전199까지15개archive/source hash를확인한다. 전체ARM/FIT/STA/IO/CDC물리승인/새FW/ZIP/실기결과는없다.

## 남은 연결과60fps

이번변경은다중frame의 **END→표시ACK→재무장** 경계를구현했다. 새로운frame의capture generation/content epoch를원자적으로가져와lease를유지하는producer/controller, board SPI/descriptor mux, productionC RUN의위호출순서를다음에결합해야한다. retire완료전source를풀거나다른capture로갈아끼우면안된다. 실제ROM변경/CHR-RAM은기존immutable/snapshot요구를유지한다.

전체ARM/RUN/IRQ 및FIT/IO를거쳐짝패키지로첫레벨스크롤을측정한다. 추가적인작은codec최적화만반복하지않는다.199의17.944ms합성전송결과는여전히60fps승인이아니고이번결과로갱신하지않는다. 새50검사는속도개선측정이아니다.

collected_runs는비어있다. 숫자1+A→첫레벨확인→RIGHT+B유지/Apress-release반복으로실제원본/계획/전송/고유표시간격을측정한다. persistentdelta는basegeneration/bank/slot/contentepoch/row-alt-mask와RAM예산을포함해후속검토한다. 배포186/GBC164/saveSRAM/완료archive유지. AV약60fps→장기play/오류·reset로그→입력유지품질 순서다.
