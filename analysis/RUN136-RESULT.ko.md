# 136 최초 최소 RUN 실기 패키지

## 작업 목표

135 공정 점검의 A: 검증 문서 단계를 늘리지 않고 실제 CPU를 잠깐 실행할 SD 패키지를 제공한다. PR81 병합 `a8b4450a6f81cf0f6997a681fa6e5ec41439e692` 기준이다.

## 작업 내용

선택135fit03의 RTL·QSF·라우팅을 그대로 재사용했다. MCU는 실제119에서 적재/비교/메뉴복구에 성공한116 기반이다. 식별은 로더59·관측D4만 허용하고 새 선택 파일 `NES RUN 136.nh1`을 사용한다. 80KiB 합성 JMP8000 이미지를 전체 적재·비교한 뒤 START,1ms 대기와 관측16회,STOP,기본FPGA/메뉴 복원을 수행한다. RUN 중 SD 쓰기는 없다. bit별 shared-fault/RDY 및 CSS/NMI 보호를 유지했다.

실제 MCU 명령열과 RTL 대조에서 **RUN 뒤 STOP은 READY 상태·이미지를 유지**한다는 차이를 발견했다. 기존의 idle/0 기대는 실기 복구를 막을 수 있었다. RUN 전용 STOP은 flags2/count81920을 정확히 요구하도록 수정했고 구형 sd_command의 승인 범위는 넓히지 않았다. 선행CF86 short 식별 함수는 이 후보에서 미사용이어서 제거했다.

새 진행 파일은 `nes-progress-136.txt`, 최종 파일은 `nes-run-last-136.txt`다. 전자는 RUN_NEXT/RUN_STOPPED와 기존 복구 단계를 남긴다. 후자는 후보·적재·CPU 읽기 카운터·오류·STOP·복구 결과를 남긴다. 공통 고장 뒤에는 SD 기록을 강행하지 않는다.

## 작업 결과

- **A 패키지 준비 완료, B 실기 결과 대기.** [실기 안내](../docs/nes-run136-instructions.ko.md). 게임/화면/입력/오디오는 이번 범위가 아니다.
- 실제 FatFs/MCU/bit GPIO/보호/복구 코드8사례 통과: 정상,잘못된D4,진행없음,ROM오류,실행중RDY낮음,STOP실패,STOP후카운터변화,잘못된59. 정상 및 논리적 활동 실패는STOP/메뉴까지,통신·공통 고장은RESET/USB보호 유지. 외부 SD/FPGA는 모델이며 실물 성공으로 세지 않는다.
- 실제 MCU 생성22프레임을135 RTL에 재생한 두 위상0/3.5ns 통과. 각 위상 first3430→last73722→stopped75636,STOP뒤불변. 초기80KiB와검증상태는 주입했고 전체RTL 쓰기를 반복하지 않았다. 이상적PLL/70ns RAM 모델이다.
- ARM185780bytes,호스트와제품 소스 일치 및 실제 NMI 벡터/15stores/0calls/보호 호출 확인. 새 ASM/압축만 수행했고 MAP/FIT은0회다. ZIP12항목 전체 바이트·압축해제·정상044 쌍 확인.
- 현재2400 crossing rows/505pairs 중 held-data270pairs/810cornerchecks 통과(address+1.999ns/data+38.685ns). 실제12chains(4control+8release) firstfanout1,setup+4.762/hold+.194ns. reset3642rows 중80음수는 releasechain 비동기 입력에 한정,나머지하류최소+.561ns. 이를 MTBF·모든reset조건 승인으로 해석하지 않는다.
- 실제 패드 경로2280rows: reader출력최대12.078ns/입력7.219ns.95.232ns 읽기창에서70ns부품규격·setup/uncertainty2ns·**미측정 PCB왕복2ns 가정**을 빼면 조건부1.935ns다. 이는 측정 여유나 전체IO signoff가 아니다. write-data/ownership 경로는 읽기마다변하지않는계약으로구분한다. 기존readonly/guard/reset서비스5파일은131과해시가같아기능근거재사용했다.

선택결과 host05/RTL02/ARM03/ARM-check03/STA01/IO03/ASM01/release01. 초기실패도동결했다. MCU STOP차이는실제수정이며 IO경로분류·미사용함수·sandbox DLL오류는원인을구분했다. 원시numeric/connection경고보존,실기미실행.

패키지SHA `973bd739d98a51a8d05c27d19b36b74208ad882f9ed958c03247e6cc290ea04b`. 펌웨어SHA `e5b7591fec88ec28aaea97ea31ddb0cc9c2fcc295c10bc47a4b392b8a451a215`. FPGA압축SHA `60c67adbb2662dbb9b8f2bc9adc352ab31b2b77241ccff06e28ceedafdba7566`. 이진파일은Git제외,로컬개인시험묶음이다.

## 작업 의미

**실기 코어 실행을 위한 MCU↔FPGA 연결과 시험물 전달**을 완성했다. 다음 판단을 보드의 CPU활동·종료로그로 할 수 있다. 카운터증가는명령정확성·프레임·SMB3성공이아니다. 정상한번의실기시험을위한조건부준비이며 전체제품승인은아니다.

사용자136 실기에서 두 TXT·메뉴 복귀·044 메뉴/GBC 복원 결과를 확인한다. 실패 시 마지막 성공 단계~첫 실패 경계만 수정한다. 정상 CPU 활동 확인 뒤 기존H1 소비자와 실제 NES 화면·입력을 연결한다. 새 실패 없이 같은 오프라인 시험·배치·로그 확장을 반복하지 않는다.

E1/E2·MTBF·전체전기조건·8µs·양클록정지 lockedHIGH CE9µs 반례는 미해결이다. source-lock 보류4건은 그대로이며 selected135는 regs_savestates/bus_savestates를 사용하고 dpram/MMC3 원본은 포함하지 않는다. 새 upstream 원본 반입·공개 바이너리 배포·보류 해제는 없다.119/044/GBC/SMB3 첫 목표와 기존6/5/1의 제한 범위를 보존한다.

재현: `prepare_nes_run136.py`, `build_nes_run136_arm.ps1`, `test_nes_run136.py`, `test_nes_run136_rtl.py`(기존FLOAT RunOnly), `check_nes_run136_arm.py`, `nes_run136_inventory.py`/`nes_run136_sta.py`/`nes_run136_io.py`, `nes_run136_assemble.py`, `release_nes_run136.py` 순으로새출력폴더에서실행한다. 불변135DB와116소스·pair109는개인동결입력이다. 완료검증은 `verify_nes_run136.py --evidence <frozen136>`이며 동결증거는수정하지않는다. [검증메타](run136-verification.json).
