# NES 현재 인계 — 148 실제 마리오 초기 읽기 장애 해결

[148 결과](../../analysis/GAME148-RESULT.ko.md) · [147 기준](../../analysis/GAME147-RESULT.ko.md) · [146 실기 결과](../../analysis/SCREEN146-HARDWARE-RESULT.ko.md)

## 현재 결정과 다음 작업

모든 코어에서 최소한의 필수 구현 확인 후 실제 목표 ROM의 실기를 우선한다. 사용자는 추가 A/B 판정을 종료했고 마리오 이동·스크롤로 프레임 문제를 확인하도록 했다. 같은146·044 복원과 변경 없는 전체 검증을 반복하지 않는다. 공통 기준은 docs/development/MILESTONE-WORKFLOW.ko.md다.

PR90은 c38bad708988e301df336c227f4ea78cdad77b69로 머지됐으며146 결과eecec90에 도달한다. 게임 작업 PR91은 master 기준 초안이며147/148을 함께 담는다. 인증은 현재 개인 GitHub 계정으로 고정했고 선택 창 없이 fetch·push와 실제 인증 주체 확인을 통과했다. 퇴사 계정으로 대체하지 않는다. 커밋 작성자도 이 저장소의 개인 계정 설정을 사용한다.

148 core03은 실제 SMB3(J)30프레임을 통과했다. CPU ROM 샘플1,425,678·PPU384,638·맵퍼 쓰기 관측468,오류0이다.147의24/26프레임 PPU deadline 실패를 해결했다. 다음 배경 패턴 주소와 현재PPU버스 데이터를 같은MMC3뱅크 레지스터로 변환해 미리 읽는다. 실제 요청 우선·물리태그·마감·클록은 유지했다. 기존1/2/10/20프레임 출력은 모두 같다.

현재 증거는 미리 적재한 ROM/70ns PSRAM 모형의 약0.498초 실행이다. 실제 게임 표시·조작이나 모든PPU경계 통과가 아니다. 초기 미정값 경고40개,core01선언순서 컴파일 실패/core02생성기문자열 실패를 보존했다. 현재 서비스/reader/loader/CHECK/SPI는147과 동일하므로 이전 경계 시험을 재사용한다.147의실패를 과거 기록에서 지우지 않는다.

다음은 MCU384KiB 적재·검증과 로딩 단축, 게임 SNES 출력·패드 연결이다. 기존80KiB 적재·대조518.99초를 그대로 늘리면 약41.5분 추정이므로 같은 바이트 전송을 그대로 배포하지 않는다. 고정팔레트·스크롤0·스프라이트 없는 NCR1을 실제 게임 출력으로 간주하지 않는다. 필요한 자원·타이밍과 종료 경계만 확인하고 실기 ROM 패키지로 간다. 새 진단 체계·추가 패턴 시험·변경 없는30프레임 반복을 끼워 넣지 않는다.

147 PRG256KiB/CHR128KiB 전체태그·19비트계수·5F/BEGIN2는 아직MCU/top 미연결이다. 오디오·다른 맵퍼도 후속이다. 기존146패키지와147 frozen은 불변이며 새148증거124파일 manifest는 analysis/game148-verification.json에 고정했다. 모든 FLOAT 작업은 종료했다. 설치 가능한 새SD패키지는 없다.

## 보존할 기준

## 구현과 검증 범위

실제65816/PPU/DMA 모형 정상·혼합·늦음 각30패킷/60,240바이트와395개RGB 통과. 정상 전송18,390~18,406 master clocks,첫225→238줄/이후240→253줄로 같은 블랭크 안에서 켠다. 늦음은13번째 블랭크 판독값0을 주입해 다음 블랭크 대기를 확인한 분기 시험이며 물리 지연 증거는 아니다. 해당 분기를 우회한 테스트전용ROM은 완전30패킷 실행 후대기 조건에서 거부됐다. 길이/헤더오류2/7도 차단했다.

MCU는145에서 이름146만 변경,호스트21사례·ARM186792/NMI15store0call3DSB2ISB·소스일치 통과. 같은142/145 RTL·배치·QSF·SDC·타이밍 보고서를 유지하고 ROM/MIF24576바이트 및ASM만 갱신했다. 실제65536주소대응 통과. 전체코어/새MAPFITSTA는 반복하지 않았다. 기존144NES ROM/CRC·전량 대조·보호·RUN중SD쓰기금지·STOP/base/menu는 그대로다.

선택client01/normal02/mixed01/late01/negative02/bad_length01/bad_header01/host01/arm01/armcheck01/rom01/asm01/bus01/reference01/release01. 첫normal01의225줄검사 실패와negative01의테스트ROM누락은 별도 보존하며 실제RTL/펌웨어 실패로 분류하지 않는다. frozen1464701파일 manifest b533b53f59b667181acd8c243b013fce5dc29a7284df978bae3d4bcd6a42f967. completed freezer나기존archive를 다시 실행·수정하지 않는다.

## 공통 보존

보드는 FXPAK Pro Mk.III Rev.D/2022-05-02, STM32F401RCT6, EP4CE15F17C8N, PSRAM IS66WVE4M16EBLL-70BLI 두 개다. 기존 FLOAT wrapper1seat를 재사용하고 새 유료 라이선스/부품/PC연결을 다시 요구하지 않는다. GBC152·원래NES334·모든 과거 public pin 유지. 전체IO/MTBF, ACK16ns 실패, E1/E2·8µs·양 클록 정지CE9µs·source-lock4·124격리 유지. 공개에는ROM/바이너리/사용자영상/라이선스/개인경로 금지. PR한국어4절과 사용자머지 원칙.
새 PR은 사용자가 머지한다. 다음 작업 전에 실제 PR/master와 인계 상태를 갱신한다.
