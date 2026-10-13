# NES167 원시 자격 캡처 분리 — 실기 시험판 준비

NES167 실기 시험판을 준비했다. 원시 자격 캡처와 명령 판정을 분리하고 적재 카운터 산술 분리를 결합해 내부 setup+0.245ns/hold+0.126ns,14944LE/956LAB/35M9K를 통과했다. 조건부 외부 연결·영상 리셋 검사를 통과해167 MCU와 새 FPGA를 패키징했다. 화면 복구·속도·사운드는 새 실기 결과로 확인해야 한다.

## 구현과 외부 계약

166은 화면 완성 전에 BEGIN/ABORT를 반복했다.167의 정상 사용권·소비자 대기 분리와 세부 취소 이유 처리는 앞서 기능 검증을 통과했으나 FPGA 타이밍 때문에 배포하지 못했다. 이번에는 그 수정과 함께 사용할 SPI 명령 경로의 병목을 해결했다.

기존의 SS 캡처 시 준비 상태→명령 자격을 한 번에 계산하던 경로를 분리했다. **C0 원시 자격 캡처→C1 원인 조합→C2 명령 판정→C3 승인·실행→C4 CHECK 카운터 반영**이다. C0에서 loaded/run/ready/load_ready와 나머지 조건을 저장하고 C1에서는 저장된 값만 사용한다. 같은 edge 등가가 아니며 이전 후보보다 명령 승인에1클록,기존165/166보다 CHECK 카운터까지2클록이 추가된다.

모든 대기 단계에서 hard fault9·잘못된 응답7·SS 겹침1을 계속 live 검사한다. 승인 전에 오류가 오면 실행을 차단하고 reset은 전체 큐를 비운다. C3에 이미 승인된 카운터 효과는 C4 직전 fault로 되돌리지 않지만 비동기 reset으로는 취소된다. STOP의 WRITE/HOLD 배출은 그대로이고, 새 지연만큼 STOP 승인도 늦어진다는 계약을 명시한다.

현재 MCU의2.625MHz mode0, SS high/setup 최소2µs에서 응답 바이트가 동일하므로 SPI ID0x74를 유지한다. 이는 소스·모델 근거이며 실기 버스 측정이 아니다. 적재 수는 앞서 검증한 `loadcount167`의 갱신 허용/산술 분리를 그대로 적용했다. 세이브 SRAM·GBC·164 복원은 변경하지 않았다.

## 검증과 최종 결과

|항목|결과|
|---|---|
|C0 캡처/C1 판정|369,165조건 통과;C0 직후 모든 외부 준비 상태·길이 반전|
|C1/C2/C3 오류·reset|180경계 통과|
|승인 직전/직후 카운터·reset|24경계 통과|
|실제 SPI와 새 로더 결합|219프레임/14,016비트 응답 일치;100읽기·7ACK·19주소 손상·72취소·2겹침|
|잘못된 회로 검출|C1의 live ready 사용, 새 단계 SS 겹침 누락, 승인 시 hard fault 무시3종|
|전체 배치|14,944LE /956LAB /35M9K|
|실제 클록 최악 setup /hold|**+0.245ns /+0.126ns**|
|CHECK /적재 카운터|+0.917ns /+0.718ns|
|원시 캡처 /원인 /오류 판정|+0.613ns /+2.641ns /+1.966ns|
|조건부 외부 연결|PSRAM 여유+3.341ns;SNES76.557ns/모델270ns;SPI167.547ns/반주기190.476ns|
|영상 payload 음수 recovery/removal|0개;기존 release/sync24경로는 별도 한계 유지|

전체 FIT는 한 번 수행했다.61개 입력을 동일하게 재생성했고59개는commitstage167/map01과 동일하다.3개corner/4개 실제 클록을 검사했다. 클록·seed·Standard Fit·SDC·false-path·multicycle 예외를 완화하지 않았다. 엄격한 개발 예산 보고서는 별도로 보존했고 실제 클록 통과와 구분했다. 조건부 IO 판정은 기존70ns 부품 규격·디지털 버스 모델 및 배선 여유 가정에 한정하며 전체 전기적·MTBF 보증이 아니다.

로더의294912조건/1056시퀀스/524288증가·STOP 오류 회로 검출은 정확히 같은 로더 바이트로 재사용했다. 변경된 SPI와 연결한219프레임 시험은 새로 실행했다.167 fill/export·ARM 전체 링크와RUN/IRQ스택 여유1076바이트, MCU/SNES45ACK·61184픽셀 검증도 바이트 확인으로 재사용했다. 전체 ROM 쓰기·게임 부팅을 반복한 것으로 주장하지 않는다.

test01은 테스트 task 이름으로 Verilog 예약어 `edge`를 사용해 컴파일 실패했다. RTL 문제가 아니며 이름만 고친test02가 통과했다. 실패 실행본도 보존했다.

## 패키지와 실기 판정

ASM/CPF 뒤 압축 FPGA를 복호화 대조하고 ZIP 안의 모든 파일을 manifest와 비교했다.166 패키지에서 ROM·메뉴·164 복원 파일을 그대로 보존했으며 바이너리·ROM은 공개 Git에 올리지 않는다.167 firmware는 앞선 전체 ARM 검증본과 동일하다.

- ZIP SHA-256: `99f9cf595766146d8d86c254d607d2f717eea8a4a0b491ae41cc6117584b709b`
- firmware SHA-256: `783a3c831385c4dde009e6fe4b787bc6629f85db6afd317cb144ab2fe8bc86b0`
- FPGA SHA-256: `d1e8278212164ecce5ec1161ca9f469ad710debc4e7ffe2c2c9d0450bd356bf2`

NES167-SMB3-FILL-WAIT.zip의01-GAME167-SD-ROOT 내용을 SD 루트에 적용하고 NES GAME 167.nh1로 SMB3(J) 첫 레벨의 화면·사운드·약60초 메뉴 복귀를 확인한다. nes-progress-167.txt/nes-game-last-167.txt와 화면이 나오면20~30초 영상을 받는다. 검정이면 촬영 불필요. 결과 전에는 새 범용 진단·무변경 FIT/부팅·166/044 반복 시험을 추가하지 않는다. 실패하면 최초 fill 세부 사유와 BEGIN/END/ABORT/COMMIT/native_frames에 따라 실제 경로만 고친다. 이후 연속 AV 품질→장기 플레이/오류·본체 리셋 로그→입력 유지 순서를 지킨다.

이 작업은 **실기 영상 구현을 막던 타이밍 문제를 해결하고 시험 가능한 펌웨어·FPGA 쌍을 만든 작업**이다. 사전 검증과 패키지 준비는 완료됐으나 실기 화면 복구·정상 속도는 미완료다. [설치 안내](nes-game167-ready.ko.md) · [검증·해시](../analysis/rawstage167-verification.json) · [이전 단계](nes-commitstage167-contract.ko.md).

재현: `nes_rawstage167.py --baseline <commitstage167/map01> --out <새 ASCII 경로>` → 새 기능 검사/전체 FIT/실제 클록·조건부 IO 검사 → `check_nes_rawstage167.py` → `release_nes_rawstage167.py`. 완료된 원본·record/audit는 덮어쓰지 않는다.
