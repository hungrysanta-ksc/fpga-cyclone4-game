# 694–696: 장시간 통합 검증과 두 설치본

**MMC695 60초 비교판과 MMC696 장시간판을 준비했다.** MMC695는 MMC690의 실행 코드와 보드를 유지하고 이름만 바꿨다. MMC696은694 arm01·client01·board01을 고유 이름으로 전체 링크한 기능 시험판이다. 실기 성능 기준은 여전히 MMC690이고 MMC666 대조군을 보존한다. [설치·종료·로그 안내](nes-mmc695-696-trial.ko.md) · [694 검증](../analysis/longrun694-verification.json) · [695/696 패키지](../analysis/trial695-package.json) · [보존 근거](../analysis/longrun694-archive.json)

## 수정한 실제 비용

693의 압축 ROM은512B 직접 복사 prefix가128B로 줄어 부팅 복원·검사가 MMC690보다19.940521ms 길어졌다. 같은 시작 시각의 첫 위상에서 cold905가 한 VBlank 늦었고957 마지막 ACK까지16.654350ms가 전파됐다. warm 간격만 보면 빠지는 문제였으므로 절대 마지막 ACK와 reset 부팅을 함께 비교했다.

694는 **기존 decoder 형식 안에서 최저 저장 바이트의 literal/reference 분할**을 빌드 시 계산한다. 새 target opcode나 표·CRC 생략은 없다. 동일6020B 본문을512B prefix+4230B 압축 스트림으로 저장하며5,120B 물리 영역의 여유는26B다. 실제 native65816 reset loader에서 본문 전 바이트 일치와 손상 거부를 확인했다. 부팅 증가는4.703204ms로 줄었고 같은 시작 시각에서 잃었던 한 VBlank를 회복했다. 부팅 시간 절감을 warm FPS 개선으로 계산하지 않는다.

ARM은 정지 tick 감시의 갱신을 매 내부 guard에서 실제 `step` 경계로 옮겼다. step만 해당 카운터를 증가시키므로 중복 tick 읽기를 줄일 수 있다. 전송별 service·클록·소유권 검사와4,194,304-step 정지 tick 차단은 유지한다. 전체 Flash212940B/여유52B,data10040B,BSS19552B로693과 같다. MMC690보다BSS8B 증가이며60초판은 변경하지 않았다.

## 같은 작업량·시작 시각의 결과

실제 링크 M4와native65816을 기존 SPI/IRQ·2슬롯·ROM 허용 달력 모델에 연결했다. 905–957 총53화면씩 두 위상, 시작 masterclock7288416/7467100을 유지했다. map·tile·OAM·palette의 독립 결과와 작업량을 맞췄다. 전체 배치된 FPGA를 CPU와 한 시뮬레이터에서 실행한 결과는 아니다.

| 항목 | 위상1 | 위상2 |
|---|---:|---:|
| 밀집 평균 변화, MMC690 대비 | **+0.010728ms** | −0.048889ms |
| 957 마지막 ACK 변화, MMC690 대비 | 0ms | −0.006612ms |
| 밀집 평균 변화, MMC666 대비 | −0.041178ms | −0.050137ms |
| 957 마지막 ACK 변화, MMC666 대비 | −0.188944ms | −0.392508ms |
| 956 입력7블록 반환→955 최종 ACK 여유 | 1.593781ms | 1.509076ms |
| 911 마감·951 공개246선·952 표시3회·957 최종대기0회 | 통과 | 통과 |

두 위상 모두 화면 간 VBlank 수 증가가 없다. 다만 첫 위상906에는 최종대기1회가 추가됐고 밀집 평균도10.728µs 늘었다. 따라서 **모든 시간의 무회귀 게이트는 실패**다. 이를 새 성능 개선으로 채택하지 않고, 원래60초 구현을 그대로 유지한 별도 장시간 기능판으로 제공한다. 사용자 요청의 장시간 안정성 시험을 위한 비용이며 성능 후보와 분리해 기록한다. 첫 위상의 수 µs를 맞추려 고정 지연·ROM 위상·seed 탐색을 하지 않았다.

## 독립 검사·취소·세대 전환

- 실제 reset 복원4조건: 기존/신규 정상 복원과 손상 거부. 모델 ROM 버스이며 실물 부팅 성공 증명은 아니다.
- 실제 host ROM 버스:84MHz·23 상대 위상에서5,125회 읽기, reset/inactive release 및 STOP status 확인. 전체 보드 STOP 전파를 이 시험 하나로 증명하지 않는다.
- 실제2bank plan RTL: 두 상대 위상,65534→65535→0,stale identity 거부, NES clock 정지 중 STOP,늦은 tile DONE 차단, 재개 통과. 승인된 Starter FLOAT1좌석으로 순차 실행했다.
- 실제 M4/65816 세 화면 재생: 입력·plan·출력·ACK wire generation65534/65535/0,최종commit3회. fixture 장면 번호만905/906/907로 유지하고 ACK identity 바이트는 검사했다. source/SPI/ROM endpoint는 모델이다.
- 기존 native65816 DMA·STOP23조건을693본문으로 통과했고694본문이 바이트 동일함을 확인했다. 새 packed 부팅은 별도 재검증했다. 실행 중 packet/DMA 두 지점에서 종료 조합을 넣어stage7E→park 이후1,000회 반복 동안 ACK/DMA가 추가되지 않음을 확인했다. 요청→park는각각1.965/0.893ms였다.
- 최종694 ARM16조건·메뉴5/marker4·base복구5조건 통과. 새 이름으로 링크한695/696도 각각메뉴·marker·base5를 검사했고,695의5–40/40–55 집계와696의16장시간 guard/statistics를 확인했다. 각 경계가 통과한 것이며 실제보드 장시간 종료·전원/입력 전기적 동작은 사용자 시험이 남았다.

초기 wrap fixture의 네 번째 장면 진입 실패, 종료 fixture의 joypad callback 중복, sandbox의 구형 GCC DLL 실패를 보존했다. 이들은 실패 후 fixture/실행 환경을 수정해 재실행했다. 잘못된 단계의 성공 로그로 대체하지 않았다. 라이선스·서버 원문은 보존 ZIP/Git에서 제외했다.

## 전체 보드와 전달

689D의82개 입력을 고정하고 `sink-program.hex`만 바꿨다. 같은 seed1·핀·클록·SDC로 전체 Quartus Lite compile을 실행했다.

| 항목 | 694/장시간판 | MMC690의689D 대비 |
|---|---:|---:|
| LE |15,295/15,408|동일|
| LAB / M9K |963/963 ·56/56|동일, 여유0|
| setup / hold |+0.104 / +0.137ns|동일|
| recovery / removal |+1.460 / +0.488ns|동일|
| minimum pulse width |+2.626ns|동일|

PSRAM reader·word 경로·ROM IO 보고도 양의 slack이다. 기존 unconstrained input54/output56–57 및 경로 수는 그대로다. 외부IO 전체 sign-off로 확대하지 않는다. 실제227 programmer/FatFS에서 새BI3를 풀어RBF 전 바이트와 일치하는지 검사했다. GPIO/DONE은 모델이며 물리 재설정은 아직 아니다.

전달 ZIP은 `WORKSPACE/probes/nes-trial695/trial01/MMC695-60SEC-MMC696-LONG.zip`이다. SHA256 `66ed0fbc3b4ff74a1a08e0dc49567b35ce1d5b0a609ce0b4e364ecb9631adb76`. 게임·RESTORE·세이브를 넣지 않았고 base/menu는 정상 복귀에 필요하여 포함했다. 각각 이름을 갱신한 ARM의 함수 주소·크기·명령 바이트가 원래 선택본과 일치하고 firmware CRC·Flash 한도·marker·로그·ROM경로와ZIP 재읽기를 검증했다. 로그696은schema693의 유한 epoch 통계이며 첫55초 집계는 보존한다.

## 재현과 다음 순서

`tools/prepare_nes_longrun694.py`는693client02와635client04에서 새client01을 만들고, `prepare_nes_longrun694_arm.py`는693arm03/src에서patch01을 만든다. `build_nes_mmc479_arm.ps1` Base=693arm03/Patch=patch01로694arm01 전체 링크. `prepare_nes_longrun694_board.py`는689D 입력에서board01을 만든다. private archive에는 선택·기각 재생 스크립트와 원시 결과가 있으며 공개 도구는입력hash를 고정한다. ASCII Temp 경로와 해당 PC의 정당한 Questa FLOAT 환경이 필요하다.

1. MMC695를 같은 첫 레벨 동선의60초 대조로,MMC696을 장시간·종료 조합 확인에 사용한다. 실기 결과 전까지MMC690을 제품/성능 기준으로 유지한다.
2. 자연 발생한 시작 실패·장시간 오류·메뉴 복귀를 각각 분리한다. 기존 stage0 실패를 이번 부팅 복원 지연과 동일 원인이라고 단정하지 않는다.
3. 692에서 분리한951 마지막tile ACK→SEAL12.448/11.849ms를 준비·credit·수락으로 나눠 최소 성능 후보를 검증한다. 장시간 기능의 작은 비용을 고정 지연으로 맞추는 탐색은 보류한다.
