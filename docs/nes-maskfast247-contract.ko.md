# NES247: 코드 확대를 사용한 실제 수신 시간 개선

2026-10-18, PR128. 목표는 정상 속도의 지속적인60프레임 표시다.4KiB를 유지하기 위해 느린 루프를 고집하지 않고, 수신기 본문을4398→5775B로 확대했다. **같은71프레임에서 map 수신·manifest·coverage의 최악 합은20.05851→13.28558ms, warm69의 합계는24.36% 감소했다.** 아직 전체60fps 후보는 선정하지 않았다.

[공개 검증](../analysis/maskfast247-verification.json) · [71 frame 표](../analysis/maskfast247-frames.csv) · [직전4398B 실행·저장 근거](nes-storage247-contract.ko.md).

## 변경한 완전한 수신 경계

2471 wire 형식은 유지한다.1024B의 불변 조회표가 mask별 payload 길이와 첫 word부터 마지막 word까지의 범위를 제공한다. 전체 record 길이를 먼저 검사한 뒤8개 선택 위치를 전개한 코드로 기록한다. 선택하지 않은 word는 쓰지 않는다. DMA 목록은 word마다 추가하지 않고 group당 한 번 추가한다. 같은 map section의 내부 간격은 최대14B이며 map 전체도4096B 이내이므로 기존 gap96/길이4096 규칙과 같은 목록이 된다. 처음과 마지막 바깥쪽 여백은 추가하지 않는다.

manifest와 pattern coverage는8word씩 비교한다. 모든 word의 내용·유효성 검사는 유지하고 반복 index 계산만 묶는다. cold map의 전체 receipt 검사, 두 manifest의0/240 offset·240/16 길이, 엄격한 group 순서, 초기화 상태, pattern/raw/CGRAM lifetime, STOP 및 최종 display ACK 경계는 유지한다. DB는 바꾸지 않으며 DP80..93의 임시 영역을 사용한다. 새 framebuffer나 save SRAM 할당은 없다.

조회표는 assembler label fixup과 함께 생성하며 각 branch relaxation 때 다시 배치한다. 완성 바이너리의 주소를 사후 패치하지 않는다. 첫 build01은 생성 코드의 DP 변환 후 문자열을 잘못 찾은 도구 오류로 중단됐다. 실패 snapshot을 보존하고 build02를 선택했다.

## 실제 CPU 검증

SELECT `maskfast-build02/test01/fault01/lanes01/masks01/analysis02`, `faststorage-map01/rtl01`. sender는 검증된 `maskrun-host01` 그대로다.

- 실제 C/65816 정상71 display commits,1100 ACK, C reference4,066,624 checks. 독립 Python encoder와 wire/manifest가 일치한다. 목적 map290,816B 및71개 DMA command 목록이 이전 수신기와 정확히 같다.
-426DMA/132,270B,178기존 bulk chunks/12,944B, 최대DMA1312B, 최대목록13개. warm multi-VBlank는952/955 두 개로 변하지 않았다. single-VBlank67 commits는60fps 증명이 아니다.
- 기존12개 오류·STOP 시험과 새24개 검사 위치 시험을 통과했다. 새16개 manifest 반례는 두 packet과 비교 블록의 각 byte 위치를,8개 coverage 반례는 각 전개 word 위치의 미초기화 pattern 요구를 검사한다. 모두 이전 표시 한 개를 유지하고 두 번째 후보를 terminal rejection했다.
- 별도 실제 CPU 시험은 정상 두 frame 표시 후 bank0에255개 nonzero mask를 전부 입력했다.1024선택 word뿐 아니라 선택하지 않은 word까지 map4096B, receipt256B, 정확한4080B command span과 manifest를 확인했다. 합성 그래픽을 화면에 표시하거나 WRAM/ACK를 주입하지 않았다. 이는 모든 가능한 packet 조합이나 formal 증명은 아니다.
- 정상 replay의752개 미초기화 읽기 주소는 독립 oracle이 허용한 미사용 pattern gap에 한정됐다.

## 시간 비교와 남은 비용

동일한 actual instruction 진입/복귀 master clock으로 비교했다. packet read·decode·staging·append와 해당 routine 내부 service가 포함된다. 도구 callback의 wall time은 CPU 시간으로 계산하지 않는다.

|warm69 routine|이전 최대ms|현재 최대ms|69개 합계 감소|
|---|---:|---:|---:|
|mask 수신|16.73239|11.32351|16.88%|
|manifest|1.81820|0.91343|49.72%|
|coverage|1.51202|1.04864|30.59%|
|frame별 세 항목 합|20.05851|13.28558|24.36%|

현재 합은3.57904..13.28558ms다. 모든 개별 mask 경로가 빨라진 것은 아니다.908/911/927/929/933/934/935/936/951/952/953/956/959/961의14개 frame에서는 mask routine만 더 오래 걸렸다. 고정8위치 검사와 group 준비 비용을 포함한 결과이며, 개별 원인의 시간 비중은 별도 계측 전까지 확정하지 않는다. 전체 합계와 최악 시간 개선으로 이 회귀를 숨기지 않는다.963은99word/50record에 세 항목13.28558ms를 사용한다.

ready4 wire 모델과 측정한 mark/mask/manifest/coverage를 직렬로 합한 조건부 비용은12.58500..27.32937ms다.16.67ms 초과는58→45/69로 줄었으나 source·ARM·나머지 dispatch/copy·대기·DMA/display까지 포함한 실제 일정은 아니다. 이 결과를FPS 또는 모든 겹침 일정의 불가능 증명으로 사용하지 않는다.

## ROM 자원은 전체 보드에서 여전히 해결 필요

같은5775B 본문을6KiB(4096+2048)와 직접8KiB ROM으로 standalone MAP했다.6KiB는249LE/97조합/158FF/49,152bits이며 두 M9K ROM 배열이 추론됐다. 직접8KiB는248LE/96조합/157FF/65,536bits다.6KiB 본문 수용량5984B에209B가 남는다.6KiB/209B를 새 절대 한도로 삼지는 않는다.

실제 bus RTL의 LoROM·packet·control 읽기33,029개와 raw read/reset/inactive/write 배제4조건이8KiB와 같았다. read latency, vector/footer alias, 빈 구간의FF를 포함한다. ROM write 관련 기본0 경고6개를 보존했다. 새 whole-board FIT/STA는 하지 않았다.

기존240은54/56M9K이며 LE/LAB 부족으로 미배치다. 프로그램4→6M9K를 대입하면56/56이 되는 **용량 산술**이며, 배치나 mapper 여유 승인도 아니고 새 source를 수용했다는 뜻도 아니다. FPGA source449B/rowshift와 함께 M9K·LE·LAB를 다시 배분해야 한다. 생산227의 다른 자원 수치를 섞지 않는다. 외부 PSRAM 적재는 loader/CHECK/RUN 소유권·부트·영역 예약·무결성 연결이 필요한 별도 후보다.

## 다음 경계

공간 확대가 실제 시간을 줄인 근거는 확보했다. 다음은 남은 mask 비용을 record 준비·값 복사·목록 추가·입력/STOP service로 분해하고, sparse/dense record 분포 및 packet 경계와 함께 비교한다. service를 무조건 생략하거나 검사·소유권을 삭제하지 않는다. 묶음 처리의 CPU 시간과 wire·메모리·최대 service 간격을 함께 평가한다. 단독 opcode/seed/코드 크기 미세 조정 반복은 하지 않는다.

동시에952 순서 비용,955의최소4198>4192 DMA charge, source 전체 면적·mapper 여유, 새입력 ARM RUN/IRQ, host/NES firstfault·CDC/IO·최종 display lease/retire가 열려 있다. 이 경계가 해결되기 전에 P2/새설치물/실기60fps를 승인하지 않는다. 생산227,240 미배치 기준,기각241/246,GBC164,save SRAM과 기존 실패·검증 자료는 보존한다.

재현 도구는 `nes_maskfast247.py`, 기존 `test_nes_maskrun247.py`·`test_nes_maskfault247.py`, 새 `test_nes_fastlanes247.py`·`test_nes_fastmasks247.py`, `nes_faststorage247.py`·`test_nes_faststorage247.py`, `analyze_nes_maskfast247.py`다. 실제 도구 snapshot·원본 로그·해시와 private ROM은 분리 보관한다. 공개 자료에는 게임 ROM·그래픽·license를 포함하지 않는다.
