# NROM458: 457 진단 산출물 identity

457의 같은 Lite routed DB에서 assembler와 CPF로 SOF·RBF를 만들고, 검증된 bounded-run encoder로 227용 BI3를 생성했다. 독립 decoder는 RBF 510,856B를 길이와 내용까지 일치시켰다. 실제 227 FPGA programmer와 FatFS host C가 BI3를 읽어 모델 GPIO에 출력한 510,856B도 같은 RBF다. GPIO/DONE 및 FPGA 설정 자체는 모델이다.

457 FIT 소스와 live 표시 회귀 소스의 QSF 지정 입력 66개가 일치한다. 동일 routed DB의 별도 복사본에서 생성한 Lite 기본 EDA netlist 한 개에서 65816 ROM atom 4,096B를 추출해 227 `sink-program.hex`와 일치시켰다. 이것은 RBF에서 메모리 bit를 직접 추출하거나 물리 FPGA에서 읽은 결과가 아니다. ARM firmware는 기존 418 링크 산출물의 해시를 확인하고, 시각 ROM은 457 공동 실행에 사용한 428 자체 fixture의 해시를 고정했다. ARM 기계어, 현재 SD의 파일 또는 실제 입력장치 실행은 확인하지 않았다.

진단용 identity: SOF `1fbdfe56adf6c17c93903538eda3323e6f5b1228dd8b8c1105c575694aecceb4`, RBF `18e52a167c8b02b7337feb40165eeb51819ffe0fdcf1a0a55db58b5454dafc45`, BI3 `7e22887eea4ed12908766862b7fca425cf6481b33ca81c2c8766c58e2b6bd670`, 418 firmware `596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c`, fixture ROM `61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c`. 전체 입력 해시·시험 결과는 `analysis/nrom458-artifacts.json`, 보존 산출물 및 원시 자료는 `probes/nes-nrom458`에 있다.

**설치 승인 아님.** 457 raw reset/CDC·미제약 IO 및 실제 FPGA 재설정/DONE, 보존 base와 현재 SD 동일성, base token·menu 복구가 남아 있다. 현 환경에서 SD 볼륨이 확인되지 않았으며 원본 227·GBC 및 사용자 저장 자료는 수정하지 않았다. 이 시험은 지속 캡처, 실기 또는 60fps를 증명하지 않는다.
