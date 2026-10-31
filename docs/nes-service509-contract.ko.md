# NES509 — E8 공통 검사와 실제 ROM 허용 기록, MMC509 확인본

실기 기준은 **MMC502/489 SNES,10.59fps**다.509는 개발 후보이며 새 실기 성능은 아직 없다. [검증](../analysis/service509-verification.json),[전달 검증](../analysis/service509-release.json),[패키지](../analysis/service509-package.json),[설치 안내](nes-mmc509-trial.ko.md)를 함께 읽는다. PR140 동일 브랜치다.

## 실행 제어와 검사

508의 bulk 우선/credit·완료 watermark/일반 packet 선행 공급을 유지한다. FLUSH·FINISH·RETIRE·REARM의 중복 E8 전송·header·CRC 검사를 `read509`로 공유한다. 각 호출자의 상태·STOP 검사는 앞에 남기고, FLUSH/FINISH의 reserved-before-CRC와 RETIRE/REARM의 CRC-before-empty 오류 우선순위를 보존했다. 독립 payload 검사·full ACK identity·SEAL drain·최종 ACK→resident commit→EA·VBlank는 변경하지 않았다.

실제 linked M4의 기존34조건과4phase×10응답 변조40조건이 통과했다.508/509의 반환값·첫 오류·30B diagnostic·SPI transcript가 같다. FPGA/SNES 제품 소스는 바꾸지 않았다.

## 시간과 전체 비용

같은 시작3000000masterclocks·ROM phase0·CPI2·503 SPI 평균으로 실제 M4/IRQ·48965816을 실행했다. 두 비교 모두12개 최종 RGB,36144B VRAM DMA,3280회 ROM read 배정이 같고 queue4/bulk2 제한을 유지한다. 미래 ACK를 현재 ARM에 공개하지 않는 기존 교정을 유지한다.

| 비교 | 기준 |509|판정 |
|---|---:|---:|---|
| 기존 stride48 모형,508 대비 첫 표시 뒤11간격 |1147.400098ms|1147.421702ms|+0.021604ms|
| 같은 모형,두 초기 표시 뒤10간격 |931.109780ms|931.080726ms|-0.029054ms|
| 실제 부팅 ROM 기록 재생,506 대비 첫 표시 뒤11간격 |1247.250861ms|1164.043460ms|6.67% 단축|
| 같은 기록,두 초기 표시 뒤10간격 |981.009972ms|931.092366ms|5.09% 단축|

첫 두 행은509 공유 변경만 분리한다. 수십µs 차이를 추가 가속 성과로 주장하지 않고508의 기존 이득 보존으로 해석한다. 뒤 두 행은506→508 선행 공급까지 포함한 비교이며 **부팅 기록의 민감도 시험**이다. 서로 다른 ROM 모형의 절대 시간을 빼서 개선율로 쓰지 않는다. SPI는 기존 모형140055→140015B,부팅 기록146427→141255B다.

FW212992→212956B로 Flash36B를 회복했다. text202913/data10040/BSS18576B, runtime444/sink36/plan300/window40B다.508 대비 BSS 증가는 없지만 실기502 대비 BSS+4B/FW+112B는 남는다. 기존 모형의 SP 최저0x2000f860→0x2000f878,관측 호출 stack24B 감소/workspace 간격2488B다. 부팅 기록에서는 SP0x2000f878/간격2488B다. 전체IRQ stack WCET 증명은 아니다.

507 보드 source·기존 SOF/FIT/STA 보고서 SHA를 대조했다. **15164LE/14172comb/8394FF/264816bits/51M9K**,잔여244LE·5M9K,관련 setup+0.078ns/hold+0.139ns를 재사용한다.502 대비LE−123/comb+37/FF−5/RAM동일이다. 새 합성·FIT를 반복하지 않았고,전달 변환은 같은 SOF의 CPF/BI3 작업이다. 전체 reset/CDC/IO 승인은 여전히 미완료다.

## 실제 ROM 시험의 범위

507의 실제 CPU·PPU·MMC3·cache·arbiter·READ16과70ns PSRAM 모형을 연결했다. NES21.477MHz/mem168MHz,위상3.5ns에서20frame 무선행/포화선행을 단일 Starter FLOAT 좌석으로 순차 실행했다. CPU read942526/PPU read182196/mapper write228,bank 관측과 저장한1·2·10·20화면이 같다.1..20 모든 pixel을 저장·비교한 시험은 아니다. 기존 STOP/drain/reset/잘못된 주소/응답·clock 소실 guard도 통과했다.

frame12..19의2386회 선행 read는 프레임당298~299회,반환5NES클록,같은 허용 구간 내 grant 간격12~1092클록(중앙12)이다. 실제 slot은 CPU divider·read주소·cache 수요·DMA·freeze/pause와 scanline242..259를 함께 본다. 일정한48클록 간격과 같지 않다.

이8개 부팅 window를 같은 시작 위상으로 반복 재생해 M4/65816의 ROM 배정에 연결했다. **905..916 첫 레벨의 실제 NES 부하와 일치한 폐루프 실행은 아니다.** tile/source의 바이트별 상태와 나머지 peripheral/CPI·SPI 평균에는 모형이 남는다. 전체 입력 중 live ROM 경쟁,실기 capture 거부율·IRQ최대지연·60fps를 입증하지 않는다. 추가 장시간 모형을 실기 결과 대신 쌓지 않고 제한 전달본에서 실제 플레이를 확인한다.

## 전달과 다음 순서

MMC509 전달용 ARM03은 검증 ARM01의784개 함수가 주소·크기·명령까지 동일하고 메뉴/ROM/FPGA/로그/버전 문자열만502→509다. STM3 CRC/길이와 실제227 FatFS·프로그래머의BI3→RBF 전체 바이트를 검증했다. GPIO/DONE은 모형이며 실기 설치 성공은 아직 아니다. 기존502 base/menu를 byte 그대로 넣고 ROM/save/RESTORE는 제외했다. 새 파일은 `MMC509-OVERLAP.zip`,게임명은`mmc509.nes`,로그는`*-mmc509.txt`다.

1. MMC502와MMC509를 같은 첫 레벨·비슷한 동선으로 확인한다. 사용자 설치·플레이·약60초 메뉴 복귀 후3개 로그를 받는다. 새 실기 성공 전에는502를 기준으로 유지한다.
2. 수신/계획/SEAL·최종 표시와전송량,STOP·capture 오류를 비교한다. 초기frame과연속구간을 나누고중첩counter를 합산하지 않는다.
3. 실제로 남는 본문·framing·DMA 병목을 기준으로 A2 예산을 갱신한다. 이득이 없는505 prefix DMA와509 E8 미세조정/ROM 위상·seed 반복은 새 근거 전까지 동결한다.60fps와MMC4/5 여유는미승인이다.

## 재현과 보존

Entry: `nes_service509.py`,`test_nes_service509_arm.py`,`trace_nes_service509_rom.py`,`test_nes_service509_schedule.py`,`analyze_nes_service509.py`,`release_nes_service509.py`,`package_nes_service509.py`. 기존508의34guard runner,ARM builder와 실제489 client를 재사용한다. 빌더에는 반드시 절대 경로를 전달한다.

선택: `probes/nes-service509/ARM01`(시험)/`ARM03`(label만509),`arm-test01`,`parity02`,`analysis01`,`trial01`;Temp `nes-service509-rom03`,`joint01`,`calendar01`(506)/`calendar02`(509),`assembly01`,`programmer02`. ROM01/02는 harness forward-reference/library 누락,ARM02는 상대 경로,programmer01은sandbox DLL loading 실패다. 제품/라이선스 오류로 오인하지 않는다. 최초parity01의 diagnostic32B 읽기는 실제30B크기에 맞춘parity02로 대체했다.

Temp 원본은 `probes/nes-service509/archive01/evidence.zip`과 SHA inventory로 보존한다. 기존 MMC502/489 SNES/GBC/save/백업은 불변이다. 상용 ROM·raw·firmware·license는 Git에 넣지 않는다. 다른 PC의 완전 재빌드에는 기존 private 입력이 필요하다는 이식성 부채도 유지한다.
