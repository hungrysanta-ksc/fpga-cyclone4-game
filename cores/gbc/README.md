# GB/GBC 개발 기준선

다른 코어 작업에는 [이식 회고](../../docs/development/GBC-PORTING-LESSONS.ko.md)를 먼저 읽습니다. 실행 코어는 Gameboy_MiSTer 기반이며 SameBoy 유래 CGB 부트 코드를 사용합니다.

- 내부 후보: G13C44. 사용자 실기 성공: 2026-10-04.
- 공개 제품 매핑: [sd2snesHST 0.9.0](https://github.com/hungrysanta-ksc/sd2snesHST/releases/tag/v0.9.0).
- 고정 구현 커밋: 35ef4aef14fc6abef6495a980b7f00f257e5174f.
- FPGA: [src/fpga](../../src/fpga), MCU: [overlay](../../src/firmware-overlay), SNES 출력: [renderer](../../src/renderer).
- [빌드](../../docs/BUILD-C44.ko.md), [호환성](../../docs/COMPATIBILITY.ko.md), [사용 가이드](../../docs/USER-GUIDE.ko.md).
- [소스 해시](../../source-manifest.json), [C44 파일 해시](../../release/c44-artifacts.json), [재현 결과](../../release/c44-rebuild-verification.json).

C44는 load/cap/state SD 진단 기록만 끄며, SRAM·RTC·4슬롯 상태·설정 기록은 유지합니다. FPGA와 renderer는 C43 성공본과 동일합니다.

유지보수는 재현 가능한 사용자 보고와 공통 코드 변경의 회귀를 중심으로 진행합니다. 일본판 크리스탈의 관찰된 성공과 MBC30 확장 주소 범위 구현은 구분합니다. 특수 매퍼·SGB 테두리·치트·통신 기능은 현재 제품 범위에 추가하지 않습니다.
