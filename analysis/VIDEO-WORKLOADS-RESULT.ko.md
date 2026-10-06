# Mapper4 영상 표본 확장과 packet 승인 검사021

2026-10-05. 후보 **NES-R2-VIDEO-WORKLOADS-021**, NES 구현014 유지.
**기존 정적BG packet의 지원 한계를 실제 표본으로 확인하고, 미지원 장면의 잘못된 승인을 막는 오프라인 검사를 추가했다.**
스크롤/sprite 지원을 구현했다는 뜻은 아니다.

## 실제 실행
자체009 진단에서 파생한 원본 ROM5개를 격리 Mesen NES에서 새로 실행했다.
CPU가직접 PPU/OAM/MMC3를설정하며 관측Lua는상태를바꾸지않는다.
각4프레임,총20프레임/1,228,800화소를수집했다.
기준·fine-X1·8×8sprite1개·IRQ중CHR변경·32KiB CHR네묶음순환의5조건이다.
이번은새NES에뮬레이터참조표본이다. 새RTL/Questa 또는SNES 실행은없다.

| 표본 | 기존 저수준 packet의 결과 | 새 승인 검사 |
| --- | --- | --- |
|기준정적BG|4프레임전체화소일치|4프레임승인|
|가로1픽셀scroll|변환은성공하지만43,993~45,250화소/frame불일치|scroll미지원으로거부|
|sprite1개|변환은성공하지만32~33화소/frame불일치|PPUMASK/sprite미지원으로거부|
|화면중간CHR bank변경|8×8cell안의물리타일이달라변환불가|표현불가로거부|
|CHR32KiB/네묶음순환|고주소tile일부가1024tile표현범위밖|현재16KiB전체atlas한계로모든frame거부|

020의상위build는고정ROM검증과전체golden비교를이미했다.
이번발견은020의통과가잘못됐다는뜻이아니라,저수준변환함수만범용화하면scroll/sprite를놓친다는증거다.
새검사도실시간FPGA/SNES에탑재한것이아니며전체참조화면을요구하는오프라인검증도구다.

sprite차이는CPU가설정한x40..47/y80..87영역에만있었다.
분할표본은실제IRQ handler에서line63의dot30~35에R0, dot87~92에R1을썼다.
입력fetch의물리주소와CHR ROM값,매프레임BG cadence16,388건을검증했다.
세로scroll/8×16sprite/overflow/priority혼합/CHR RAM/강조색을검증했다는주장은하지않는다.

## 관측한 BG 캐시 요구량
모든조건은BG fetch65,552건/4frames를분석했다.
전체CHR reads는각80,976건이며,캐시표에는sprite/dummy fetch를넣지않았다.
각행은캡처첫시점empty LRU,16B물리타일수요적재의frame별payload다.

| 표본·cache | frame6 | frame7 | frame8 | frame9 |
| --- | ---: | ---: | ---: | ---: |
|기준/fine-X/sprite의BG,8KiB|4,096B|4,096B|0B|0B|
|화면중간bank변경,4KiB|8,192B|4,096B|4,096B|4,096B|
|화면중간bank변경,8KiB|8,192B|0B|0B|0B|
|네bank묶음,8KiB|4,096B|4,096B|4,096B|4,096B|
|네bank묶음,16KiB|4,096B|4,096B|4,096B|4,096B|

분할표본은매프레임512tiles=8KiB를실제로참조했다.
네묶음표본의관측union은1024tiles=16KiB이나각묶음을한번씩만보았다.
16KiB cache의warm이후hit율을실측한것은아니다.
어느조건도BG rolling1364NESmasterticks 최대fill512B였지만물리서비스/FIFO크기를입증하지않는다.
미래접근순서나관측union을사전적재선택에사용하지않았다.

## 새 승인 경계
완전한상태정보,불변CHR ROM<=16KiB,고정BG table/nametable,scroll0,PPUMASK0A,
active PPUwrite없음,전체BG cadence/시간순서/물리tile/byte/좌표일치,
완전한240줄packet복원과참조화면일치를모두요구한다.
누락상태·sprite·scroll·가변CHR·active write·참조변조·unused fetch누락·plane누락·
fetch값/tile/tick/frame변조의12종검사를통과했다.
sprite enable만있어도보수적으로거부하며,눈에보이는sprite가없다는추정을하지않는다.
기존020저수준함수/소비자ROM은변경하지않았다.

## 다음 구현 순서
표본확장자체는이번범위에서완료했다. 같은지원한계검사만반복하지않는다.
1. fine-X 가로scroll을표현하는packet/map경계를구현하고021실제화면을SNES에서재생해비교한다.
2. sprite와8×8cell내bank변경에필요한overlay/patch·큰CHR의residency정책을전송예산과함께판단한다.
3. 확정한표현에producer완료시각→packet전달→queue/CDC→소비자기한을연결하고018자원에대입한다.

020의소비자기한18,046clocks/최소여유11,852는정적BG범위의보존결과다.
새장면으로확대하지않는다.240줄동시출력·색상최종정책·DMCtiming·SMB3·fullboard/실기미완료.
[수치](video-workloads-verification.json), [재현 계약](../docs/nes-video-workloads-contract.md).
