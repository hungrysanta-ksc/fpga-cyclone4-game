# NES 현재 인계 — 147 실제 SMB3 첫 실행 장애 수정 중

[146 실기 결과](../../analysis/SCREEN146-HARDWARE-RESULT.ko.md)

## 다음 작업의 우선순위

사용자가 빠른 A/B 혼합의 추가 판정을 생략하고 실제 Super Mario Bros. 3 (J)의 이동·스크롤·프레임 끊김을 확인하도록 지시했다. 146은 적재·대조·RUN·STOP·표시 존재·실제 메뉴 복귀 PASS, 빠른 전체 화면 정합성 INCONCLUSIVE다. CRT의 빠른 교대 관찰만으로 오류라 단정하지 않는다. 146 영상/로그 재수집이나 같은044 복원 시험을 요구하지 않는다.

[147 결과](../../analysis/GAME147-RESULT.ko.md) · [재현](../../docs/nes-game147-reproduction.ko.md)

PR90에는146 실기 결과만 커밋했다(`eecec90`). 실제 게임 작업은 `codex/nes-game-147`의 새 PR로 분리한다. PR90은 c38bad708988e301df336c227f4ea78cdad77b69로 머지됐으며 master가146 결과 커밋에 도달함을 확인했다. PR91의 기준은 master로 갱신했다.

147은 PRG256KiB/CHR128KiB 물리 주소·캐시 태그와19비트 적재/CHECK/SPI, 식별5F·BEGIN인수2를 구현했다. 기존 MMC3를 재사용한다. unit04의98검사·8실제쓰기·6CHECK읽기·6오류조건과 잘린태그 대조군을 통과했다. 시험 전용 카운터 주입이므로 전체384KiB 적재 검증은 아니다.

현재 막힘은 실제 ROM의 PPU 읽기 deadline이다. core02는 frame24/line193/dot231,주소21e1ff에서 valid0으로 실패한다. 실험적 미리 읽기는 첫 경계의 위상0/3.5ns에서 통과하지만 core03는 frame26/193/237,21e100에서 다시 실패한다. 내부 네임테이블 RAM→CHR 전환을 현 예측이 처리하지 못하는 것으로 추정한다. 다음 수정은 PPU의 다음 논리주소를 실제 MMC3 뱅크로 변환하거나 같은 마감을 만족하는 읽기 경로를 구현하는 것이다. 기존 현재 CHR 상위주소만 재사용하는 가정을 확대하지 않는다. 오류를 숨기거나 코어 시간을 느리게 하지 않는다.

20프레임의 커튼 그림은 RTL 초기 화면일 뿐 실기·독립 픽셀 일치·게임 플레이 통과가 아니다. 두 전체코어 실행은 FAIL을 유지한다. 실행된 모델은 메모리를 미리 채운70ns PSRAM/READ16/168MHz이며 실제 MCU 적재가 아니다. 독립 에뮬레이터 시도는 결과 없음으로 제외했다.

다음 순서: 실제 ROM의 첫 읽기 실패 수정 → MCU384KiB 적재·대조와 로딩 단축 → 게임용 SNES 화면·패드 → 최소 변경 검증/배치 → 유한 실기 패키지. 기존80KiB 적재·대조518.99초의 단순 비례는384KiB 약41.5분이므로 그 경로를 그대로 배포하지 않는다. 고정 팔레트·스크롤0·스프라이트 없는 NCR1 출력은 게임 경로가 아니다. 오디오·다른 맵퍼는 후속이다.

147 원본251파일 manifest는 analysis/game147-verification.json에 고정했다. core01/02/03과unit01/02 실패도 보존했으며 core03 입력26개를 현재 생성기가 같은 해시로 재현했다. 모든 FLOAT 작업은 종료했다. 로컬 probes/nes-game147/progress.json을 확인하고 완료된 증거/작업을 덮어쓰지 않는다.

## 보존할 기준

## 구현과 검증 범위

실제65816/PPU/DMA 모형 정상·혼합·늦음 각30패킷/60,240바이트와395개RGB 통과. 정상 전송18,390~18,406 master clocks,첫225→238줄/이후240→253줄로 같은 블랭크 안에서 켠다. 늦음은13번째 블랭크 판독값0을 주입해 다음 블랭크 대기를 확인한 분기 시험이며 물리 지연 증거는 아니다. 해당 분기를 우회한 테스트전용ROM은 완전30패킷 실행 후대기 조건에서 거부됐다. 길이/헤더오류2/7도 차단했다.

MCU는145에서 이름146만 변경,호스트21사례·ARM186792/NMI15store0call3DSB2ISB·소스일치 통과. 같은142/145 RTL·배치·QSF·SDC·타이밍 보고서를 유지하고 ROM/MIF24576바이트 및ASM만 갱신했다. 실제65536주소대응 통과. 전체코어/새MAPFITSTA는 반복하지 않았다. 기존144NES ROM/CRC·전량 대조·보호·RUN중SD쓰기금지·STOP/base/menu는 그대로다.

선택client01/normal02/mixed01/late01/negative02/bad_length01/bad_header01/host01/arm01/armcheck01/rom01/asm01/bus01/reference01/release01. 첫normal01의225줄검사 실패와negative01의테스트ROM누락은 별도 보존하며 실제RTL/펌웨어 실패로 분류하지 않는다. frozen1464701파일 manifest b533b53f59b667181acd8c243b013fce5dc29a7284df978bae3d4bcd6a42f967. completed freezer나기존archive를 다시 실행·수정하지 않는다.

## 공통 보존

보드는 FXPAK Pro Mk.III Rev.D/2022-05-02, STM32F401RCT6, EP4CE15F17C8N, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 기존 FLOAT wrapper1seat를 재사용하고 새 유료 라이선스/부품/PC연결을 다시 요구하지 않는다. GBC152·원래NES334·모든 과거 public pin 유지. 전체IO/MTBF, ACK16ns 실패, E1/E2·8µs·양 클록 정지CE9µs·source-lock4·124격리 유지. 공개에는ROM/바이너리/사용자영상/라이선스/개인경로 금지. PR한국어4절과 사용자머지 원칙.
새 PR은 사용자가 머지한다. 다음 작업 전에 실제 PR/master와 인계 상태를 갱신한다.
