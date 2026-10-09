# NES 현재 인계 —127 로더 통합, 다음은168MHz 명령·reset 경로

[127 결과](../../analysis/LOADER127-RESULT.ko.md) · [검증 메타](../../analysis/loader127-verification.json)

## 바로 이어서 할 일

**동결127 fit02를 기준으로 `mem_fault→check_next`와 `checked_data→fault` 경로를 구조적으로 줄인다.** 실제 코어에 로더·검증 후 RUN·가드가 연결됐지만 memory168 setup−2.647ns로 실기 파일을 만들 단계가 아니다. 배치 성공을 타이밍 성공으로 혼동하지 않는다. 명령 판정 단계 분리와 진단 로컬 reset 해제를 먼저 검토한다. 기존124의 common assert/local release 원칙을 새 decoder/loader에 대조한다.

최종 fit02:14,127LE/954LAB/5,296regs/26M9K/PLL1/물리46핀+가상264핀. 남은9LAB은 최종 소비자나 MMC3 여유가 아니다. NES8.963/host2.527/mem−2.647ns, 전체raw−10.383ns. 85°C guard mem_fault→check_next15,0°C checked_data2→fault−2.258ns가 남는다. live.sdc에는 blanket falsepath/multicycle이 없다. 과거126의 데이터372쌍/제어10체인 결과를 새 hierarchy에 그대로 적용하지 않는다. 이후 새 경로의 제약을 다시 확인해야 한다.

## 구현 계약과 재사용할 시험

- 168MHz 쓰기 SETUP22/WRITE64/HOLD22/RELEASE22:5.952ns 모델130.944/380.928/130.944/130.944ns. 최소125/375/125/125ns다. WRITE63은374.976ns라 거부한다. 새 비트스트림의 물리 핀 보증은 별도다.
- RUN은 실제 SPI CHECK/순차 ACK/FINISH/verified 이후 START만 허용한다. 외부ext_arm으로 메모리 RUN 우회 금지. boot의 실제 START 배선은 연결됐다. 영상 arm은 기존대로 별도다.
- 최종 SPI decoder는 CHECK 비교3개만 선행 레지스터에 계산한다. 프레임 offset은8바이트 중 앞쪽에서 고정되고 index는명령 종료 때만 바뀌며CHECK length는불변이다. DATA의 동적인length/ready비교는 즉시 비교를 유지한다. 명령 경계에서 기존 비교와의 동등성을 계속 시험한다.
- unit02:80/96KiB 핀쓰기180,224+오류87바이트, CHECK260/RUN128/쓰기·유지86오류 위치, guard3, 부정 대조3 통과. decoder02:half-SCK60/18ns 각각149검사/18오류/16ACK/96query, 비교 일치와 미검증RUN 우회 거부. unit02와 최종decoder/fit의 loader/boot/reader/guard 해시 일치. 바뀐 decoder만 추가시험했다.
- CPU 전체세션과 SPI 전체전송을 묶은 검증은 아직 없다. RAM70ns·decoder 응답16바이트는 모델이다. 원시 reset으로 취소하는 경우는 프로토콜 오류의 쓰기 drain과 구별한다. 양쪽 클록이 멈추면 guard가검출하지못하는 반례 유지.
- 최종 guard는heartbeat21분주/상대clockage672/startup33603이다. 파이프라인을 바꾸면서 이시간을줄이거나공유오류보호를해제하지않는다. 변경 없는 full80/BASE/ENTRY/전체프레임을 반복하지말고 바뀐경계를시험한다.

## 동결과 재현

127 evidence는1,171파일,manifest c2a31d101697953dcc1d02fc3ef82036ff24d16a134a144b0eb74749aa99a6c8. unit01의부정시험문구불일치,초기LAB제목파서오류,fit01의−2.508ns실패,fit02의미해결경로를모두보존한다. fit01→fit02는959→954LAB이나최악memorysetup개선성공은아니다. 동결notes의140ns-class초안표기는125/375/125/125ns로읽어야한다. 완료finalizer/옛archive수정금지.

`run_nes_loader127.ps1`은기존FLOATwrapper와`-Baseline <probes>`/새ASCII출력을사용한다. `run_nes_loader127_decoder.ps1`은최종decoder경계/빠른SPI검증이다. `nes_loader127_fit.py --baseline <probes> --out <newASCII> --quartus-bin <bin64>`후`review_nes_loader127.py`로클록별실제실패까지확인한다. `verify_nes_loader127.py --evidence <frozen127>`는빌드없이전체해시·시험·배치결과를재검증한다. 새최종제약이나실기패키지는아직없다.

## 유지할 실기 기준과 목표

119에서 동일 ARM116/097 CF86의 전체80KiB 적재·비교·STOP·기본FPGA·메뉴복귀·사용자044복원이 통과했다. 메뉴준비491.34초는 펌웨어 시각이며 독립 화면 시각이 아니다. 해당 시험의 GBC 플레이는 미보고다.113 정지 원인은 미확정이며 로그 추가의 타이밍 영향 가능성을 남긴다. 외부E1/E2·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. 제한 진단6완료/5부분/1미완료는 게임 완성률과 구분한다.

첫 게임 목표: Super Mario Bros 3 (J),mapper4,PRG256KiB+CHR128KiB,393232bytes,SHA `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 현재 진단 크기를384KiB 지원으로 확대 해석하지 않는다. 이후 맵퍼·호환성을 넓힌다.

## 재현과 게시

PR72병합확인. 한국어제목과작업목표/작업내용/작업결과/작업의미4절,사용자가병합한다. GBC152/원래NES334/모든공개핀보존. ROM·바이너리·미디어·라이선스·개인경로는Git제외. 새ARM/ASM/패키지/실기는없다. 다음은위타이밍병목을고친뒤SNES소비자·관측가능한최소RUN+044복원이다.

게시 검사에서 decoder 실행기의 공백만 있는 빈 줄 하나가 발견되어 그 공백만 제거했다. 실행·동결 원본은 보존했고 공개 검증기는 이 정확한 한 줄 차이만 허용한다. RTL과 시험 결과는 변경하지 않았다. 첫 게시 검사 실패 기록도 보존한다.
